import os
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, Any

# --- Constants for Configuration and Model Parameters ---
# INCREASED: Make form more impactful
RELATIVE_FORM_WEIGHT: float = 0.25 # Was 0.15. Now 10% form diff -> 2.5% xG impact

# INCREASED: Make injuries more impactful
KEY_INJURY_IMPACT: float = 0.10    # Was 0.08. Now 10% xG reduction per key player
OTHER_INJURY_IMPACT: float = 0.04  # Was 0.03. Now 4% xG reduction per other player

# INCREASED: Make home advantage more impactful
HOME_ADVANTAGE_FACTOR: float = 0.15 # Was 0.1. Now PPG diff has 50% more impact on xG boost

# REDUCED: Control how much Elo blends with Poisson (NEW CONSTANT)
# 1.0 = Purely Poisson Win/Loss Probs, 0.0 = Purely Elo Win/Loss Probs
# Let's make Poisson account for 80% of the Win/Loss outcome, Elo 20%
ELO_BLENDING_ALPHA: float = 0.80  # NEW - Weight for Poisson vs Elo blending

# Elo K_FACTOR remains the same for calculating Elo expectation
ELO_K_FACTOR: float = 400
STRENGTH_INDEX_BLENDING_ALPHA: float = 0.80 # Keep emphasis on simulation (80%)
EXCEL_FILE_PATH: str = "match_analysis_log.xlsx" # Ensure this is defined
N_SIMULATIONS: int = 10000 # Ensure this is defined
DEFAULT_LEAGUE_AVG_HOME_GOALS: float = 1.5 # Ensure defined
DEFAULT_LEAGUE_AVG_AWAY_GOALS: float = 1.2 # Ensure defined
WEATHER_RAIN_WIND_FACTOR: float = 0.95 # Ensure defined
WEATHER_EXTREME_FACTOR: float = 0.90  # Ensure defined
# --- Helper Functions ---

def get_float_input(prompt: str, default: Optional[float] = None) -> float:
    """Gets float input from the user with validation and optional default."""
    while True:
        try:
            default_str = f" (default={default})" if default is not None else ""
            value_str = input(f"{prompt}{default_str}: ")
            if not value_str and default is not None:
                return default
            return float(value_str)
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_int_input(prompt: str, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """Gets integer input from the user with validation and range checks."""
    while True:
        try:
            value_str = input(f"{prompt}: ")
            value = int(value_str)
            if min_val is not None and value < min_val:
                print(f"Value must be at least {min_val}.")
            elif max_val is not None and value > max_val:
                print(f"Value must be no more than {max_val}.")
            else:
                return value
        except ValueError:
            print("Invalid input. Please enter a whole number.")


def help_user() -> None:
    """Prints a guide explaining the required inputs."""
    print("\n=== Help: Input Guide ===")
    print("1.  Team Statistics: Average goals scored/conceded specifically at home/away.")
    print("2.  League Averages: League-wide average goals scored by home/away teams.")
    print("3.  Relative Form: % difference between recent PPG (last 8) and season PPG (e.g., 10 for 10% better, "
          "-5 for 5% worse).")
    # print("   (Alternative) Team Form: % change (e.g., 10 for 10% better, -5 for 5% worse).") # Keep if preferred
    print("4.  Injuries/Suspensions: Count of KEY players (stars, crucial roles) and OTHER important players missing.")
    print("5.  Weather Conditions: Impact scale (1: Clear, 2: Rain/Wind, 3: Extreme).")
    print("6.  Home Advantage Modifier: Difference in Points Per Game (Home PPG - Away PPG) for the home team.")
    print("7.  Team Strength (PPI): Points Performance Index (Team PPG * Avg Opponent PPG). Reflects performance vs schedule difficulty.")
    print("8.  Match Importance (Optional): Scale 1-3 (Low, Medium, High) - Might affect motivation/tactics.")
    print("9.  Rest Days (Optional): Days since last match for each team.")
    print("=" * 25)


# --- Core Calculation Functions ---

def calculate_base_xg(home_stats: Dict[str, float], away_stats: Dict[str, float], league_avgs: Dict[str, float]) -> \
Tuple[float, float]:
    """
    Calculates the base Expected Goals (xG) using the Maher model principle.
    xG_home = (Home Attack Strength) * (Away Defense Strength) * (League Avg Home Goals)
    xG_away = (Away Attack Strength) * (Home Defense Strength) * (League Avg Away Goals)
    """
    home_attack_strength = home_stats['home_avg_goals_scored'] / league_avgs['home']
    away_defense_strength = away_stats['away_avg_goals_conceded'] / league_avgs[
        'home']  # Conceded by away team relative to home goals avg
    home_defense_strength = home_stats['home_avg_goals_conceded'] / league_avgs[
        'away']  # Conceded by home team relative to away goals avg
    away_attack_strength = away_stats['away_avg_goals_scored'] / league_avgs['away']

    # Base xG calculation using the Maher method principle
    base_xg_home = home_attack_strength * away_defense_strength * league_avgs['home']
    base_xg_away = away_attack_strength * home_defense_strength * league_avgs['away']

    # Basic sanity check - prevent negative xG if inputs are strange
    base_xg_home = max(0.1, base_xg_home)  # Ensure a minimum base xG
    base_xg_away = max(0.1, base_xg_away)

    print(f"\n🔍 Base xG Calculated — Home: {base_xg_home:.2f}, Away: {base_xg_away:.2f}")
    return base_xg_home, base_xg_away


def adjust_xg(base_xg_home: float, base_xg_away: float, adjustments: Dict) -> Tuple[float, float]:
    """Applies various adjustments to the base xG values."""
    adj_xg_home = base_xg_home
    adj_xg_away = base_xg_away

    # 1. Form Adjustment (Using points from last 5 as a proxy)
    # Scale points (0-15) to a multiplier (e.g., 0.8 to 1.2)
    home_form_multiplier = 1 + (adjustments['home_relative_form_pct'] / 100.0) * RELATIVE_FORM_WEIGHT
    away_form_multiplier = 1 + (adjustments['away_relative_form_pct'] / 100.0) * RELATIVE_FORM_WEIGHT
    home_form_multiplier = max(0.5, min(1.5, home_form_multiplier))
    away_form_multiplier = max(0.5, min(1.5, away_form_multiplier))  # Cap multiplier between 0.5 and 1.5
    adj_xg_home *= home_form_multiplier
    adj_xg_away *= away_form_multiplier
    print(f"  -> Form Adjustment (H Rel Form: {adjustments['home_relative_form_pct']:.1f}%, A Rel Form: {adjustments['away_relative_form_pct']:.1f}%): xGH={adj_xg_home:.2f}, xGA={adj_xg_away:.2f}")
    # 2. Injury Adjustment (Weighted)
    home_injury_deduction = (adjustments['home_key_injuries'] * KEY_INJURY_IMPACT +
                             adjustments['home_other_injuries'] * OTHER_INJURY_IMPACT)
    away_injury_deduction = (adjustments['away_key_injuries'] * KEY_INJURY_IMPACT +
                             adjustments['away_other_injuries'] * OTHER_INJURY_IMPACT)
    adj_xg_home *= (1 - home_injury_deduction)
    adj_xg_away *= (1 - away_injury_deduction)
    print(
        f"  -> Injury Adjustment (H Key/Oth: {adjustments['home_key_injuries']}/{adjustments['home_other_injuries']}, "
        f"A Key/Oth: {adjustments['away_key_injuries']}/{adjustments['away_other_injuries']}): xGH={adj_xg_home:.2f}, xGA={adj_xg_away:.2f}")

    # 3. Home Advantage Adjustment (Based on PPG difference)
    # Apply a small boost based on the home team's historical PPG difference
    home_adv_boost = adjustments['home_adv_ppg_diff'] * HOME_ADVANTAGE_FACTOR
    adj_xg_home *= (1 + home_adv_boost)
    # Optional: Slightly decrease away xG as well
    # adj_xg_away *= (1 - home_adv_boost * 0.5)
    print(
        f"  -> Home Advantage Adjustment (PPG Diff: {adjustments['home_adv_ppg_diff']:.2f}): xGH={adj_xg_home:.2f}, xGA={adj_xg_away:.2f}")

    # 4. Weather Adjustment
    weather = adjustments['weather']
    weather_factor = 1.0
    if weather == 2:
        weather_factor = WEATHER_RAIN_WIND_FACTOR
    elif weather == 3:
        weather_factor = WEATHER_EXTREME_FACTOR
    adj_xg_home *= weather_factor
    adj_xg_away *= weather_factor
    if weather != 1:
        print(f"  -> Weather Adjustment (Level {weather}): xGH={adj_xg_home:.2f}, xGA={adj_xg_away:.2f}")

    # --- Add Optional Adjustments Here ---
    # Example: Match Importance (Slight boost for higher importance?)
    # Example: Rest Days (Penalty for very short rest?)

    # Final Sanity Check - Prevent negative or excessively low xG
    adj_xg_home = max(0.05, adj_xg_home)
    adj_xg_away = max(0.05, adj_xg_away)

    return adj_xg_home, adj_xg_away


def simulate_match_poisson(home_goals_exp: float, away_goals_exp: float, n_simulations: int = N_SIMULATIONS) -> Dict:
    """
    Simulates match outcomes using Poisson distribution.
    Returns probabilities AND the raw simulated goal arrays.
    """
    home_goals = np.random.poisson(home_goals_exp, n_simulations)
    away_goals = np.random.poisson(away_goals_exp, n_simulations)

    home_wins = np.sum(home_goals > away_goals)
    draws = np.sum(home_goals == away_goals)
    away_wins = np.sum(home_goals < away_goals)

    total_sims = home_wins + draws + away_wins  # Should equal n_simulations

    if total_sims == 0:
        probs = {'home_win': 0.0, 'draw': 0.0, 'away_win': 0.0}
    else:
        probs = {
            'home_win': home_wins / total_sims,
            'draw': draws / total_sims,
            'away_win': away_wins / total_sims
        }

    # Return probabilities AND the raw simulation results
    return {
        'probabilities': probs,
        'simulated_home_goals': home_goals,
        'simulated_away_goals': away_goals
    }


def analyze_goal_outcomes(home_goals: np.ndarray, away_goals: np.ndarray) -> Dict:
    """
    Analyzes simulated goal arrays to predict scorelines, O/U, and BTTS.
    """
    n_simulations = len(home_goals)
    if n_simulations == 0:
        return {
            'most_likely_score': "N/A",
            'over_2_5_prob': 0.0,
            'under_2_5_prob': 0.0,
            'btts_yes_prob': 0.0,
            'btts_no_prob': 0.0
        }

    # --- Most Likely Score ---
    # Combine home and away goals into pairs and find the most frequent one
    score_pairs = list(zip(home_goals, away_goals))
    # Use pandas for efficient counting, but could use collections.Counter too
    score_counts = pd.Series(score_pairs).value_counts()
    if not score_counts.empty:
        most_likely_score_tuple = score_counts.index[0]
        most_likely_score_str = f"{most_likely_score_tuple[0]}-{most_likely_score_tuple[1]}"
        # Optional: Get probability of that exact score
        # most_likely_score_prob = score_counts.iloc[0] / n_simulations
    else:
        most_likely_score_str = "N/A"

    # --- Over/Under 2.5 Goals ---
    total_goals = home_goals + away_goals
    over_2_5_count = np.sum(total_goals > 2.5)  # Technically >2, but 2.5 is standard
    over_2_5_prob = over_2_5_count / n_simulations
    under_2_5_prob = 1.0 - over_2_5_prob

    # --- Both Teams To Score (BTTS) ---
    btts_yes_count = np.sum((home_goals > 0) & (away_goals > 0))
    btts_yes_prob = btts_yes_count / n_simulations
    btts_no_prob = 1.0 - btts_yes_prob

    return {
        'most_likely_score': most_likely_score_str,
        # 'most_likely_score_prob': most_likely_score_prob, # Optional
        'over_2_5_prob': over_2_5_prob,
        'under_2_5_prob': under_2_5_prob,
        'btts_yes_prob': btts_yes_prob,
        'btts_no_prob': btts_no_prob
    }


def adjust_probabilities_with_ppi(poisson_probs: Dict[str, float], home_ppi: float, away_ppi: float) -> Dict[str, float]:
    """
    Adjusts initial probabilities by blending Poisson results with Points Performance Index (PPI).
    Uses STRENGTH_INDEX_BLENDING_ALPHA to control the weight.
    PPI = Team_PPG * Opponent_PPG
    """
    # 1. Calculate "Expected" win probability based purely on PPI ratio
    # This assumes higher PPI means stronger team. Ratio gives value 0-1.
    total_ppi = home_ppi + away_ppi
    if total_ppi > 1e-9: # Avoid division by zero
        ppi_exp_home = home_ppi / total_ppi
    else: # If both PPIs are zero (unlikely but possible), assume equal strength
        ppi_exp_home = 0.5
    ppi_exp_away = 1.0 - ppi_exp_home

    # 2. Get probabilities from Poisson simulation
    p_hw = poisson_probs['home_win']
    p_draw = poisson_probs['draw']
    p_aw = poisson_probs['away_win']

    # 3. Calculate the total win probability predicted by Poisson
    p_win_total = p_hw + p_aw

    # 4. Blend the Win probabilities (if there's any win probability to blend)
    if p_win_total > 1e-9:
        # Calculate Poisson's share of wins
        p_hw_share = p_hw / p_win_total
        p_aw_share = p_aw / p_win_total

        # Blend the shares using the alpha weight (using RENAMED constant)
        blended_hw_share = STRENGTH_INDEX_BLENDING_ALPHA * p_hw_share + (1.0 - STRENGTH_INDEX_BLENDING_ALPHA) * ppi_exp_home
        blended_aw_share = STRENGTH_INDEX_BLENDING_ALPHA * p_aw_share + (1.0 - STRENGTH_INDEX_BLENDING_ALPHA) * ppi_exp_away

        # Apply the blended shares back to the original total win probability
        final_hw = blended_hw_share * p_win_total
        final_aw = blended_aw_share * p_win_total
        # Keep the original draw probability calculated by Poisson
        final_draw = p_draw

    else: # If Poisson predicted ~100% draw, blending doesn't apply to wins
        final_hw = p_hw
        final_draw = p_draw
        final_aw = p_aw

    # 5. Normalize the final probabilities to ensure they sum to 1
    total_prob = final_hw + final_draw + final_aw
    if total_prob == 0: # Fallback for safety
        return {'home_win': 0.333, 'draw': 0.334, 'away_win': 0.333}

    final_probs = {
        'home_win': final_hw / total_prob,
        'draw': final_draw / total_prob,
        'away_win': final_aw / total_prob
    }

    # Updated print statement
    print(f"  -> PPI Adjustment (Blend Alpha={STRENGTH_INDEX_BLENDING_ALPHA:.2f}, H PPI: {home_ppi:.2f}, A PPI: {away_ppi:.2f}): "
          f"HW={final_probs['home_win']:.2%}, D={final_probs['draw']:.2%}, AW={final_probs['away_win']:.2%}")

    return final_probs

# --- Data Storage ---


def store_match_analysis_to_excel(analysis_data: Dict[str, Any]) -> None:
    """Saves the detailed match analysis data to an Excel file."""

    # Add calculated percentages directly to analysis_data or handle them when building flat_data
    # It's slightly cleaner to calculate them when building flat_data

    # MODIFIED DATAFRAME COLUMNS (Changed Elo to PPI)
    df_columns = [
        "Home Team", "Away Team", "Home PPI", "Away PPI",
        "Base xG Home", "Base xG Away", "Adj xG Home", "Adj xG Away",
        "Home Rel Form %", "Away Rel Form %",
        "Home Key Inj", "Home Other Inj", "Away Key Inj", "Away Other Inj",
        "Weather", "Home Adv PPG Diff",
        "Home Win %", "Draw %", "Away Win %",
        "Most Likely Score", "Over 2.5 Prob %", "Under 2.5 Prob %",
        "BTTS Yes Prob %", "BTTS No Prob %"
    ]

    # --- FIX STARTS HERE ---
    # Build the complete flat_data dictionary corresponding to df_columns
    try:
        flat_data = {
            "Home Team": analysis_data["home_team"],
            "Away Team": analysis_data["away_team"],

            # PPI / Elo
            "Home PPI": analysis_data.get("adjustments", {}).get("home_ppi"), # Use .get for safety
            "Away PPI": analysis_data.get("adjustments", {}).get("away_ppi"),

            # Base xG
            "Base xG Home": analysis_data.get("base_xg", {}).get("home"),
            "Base xG Away": analysis_data.get("base_xg", {}).get("away"), # <-- WAS MISSING

            # Adjusted xG
            "Adj xG Home": analysis_data.get("adjusted_xg", {}).get("home"),
            "Adj xG Away": analysis_data.get("adjusted_xg", {}).get("away"),

            # Relative Form
            "Home Rel Form %": analysis_data.get("adjustments", {}).get("home_relative_form_pct"),
            "Away Rel Form %": analysis_data.get("adjustments", {}).get("away_relative_form_pct"),

            # Injuries
            "Home Key Inj": analysis_data.get("adjustments", {}).get("home_key_injuries"),
            "Home Other Inj": analysis_data.get("adjustments", {}).get("home_other_injuries"), # <-- WAS MISSING
            "Away Key Inj": analysis_data.get("adjustments", {}).get("away_key_injuries"), # <-- WAS MISSING
            "Away Other Inj": analysis_data.get("adjustments", {}).get("away_other_injuries"), # <-- WAS MISSING

            # Other Adjustments
            "Weather": analysis_data.get("adjustments", {}).get("weather_factor"), # <-- WAS MISSING (Assuming key name)
            "Home Adv PPG Diff": analysis_data.get("adjustments", {}).get("home_advantage_diff"), # <-- WAS MISSING (Assuming key name)

            # Final Win/Draw/Loss Probabilities
            "Home Win %": analysis_data.get("final_probs", {}).get("home_win", 0) * 100, # Calculate here
            "Draw %": analysis_data.get("final_probs", {}).get("draw", 0) * 100,         # Calculate here
            "Away Win %": analysis_data.get("final_probs", {}).get("away_win", 0) * 100, # Calculate here

            # Goal Predictions
            "Most Likely Score": analysis_data.get("goal_predictions", {}).get("most_likely_score"), # <-- WAS MISSING
            "Over 2.5 Prob %": analysis_data.get("goal_predictions", {}).get("over_25_prob", 0) * 100, # <-- WAS MISSING
            "Under 2.5 Prob %": analysis_data.get("goal_predictions", {}).get("under_25_prob", 0) * 100,# <-- WAS MISSING
            "BTTS Yes Prob %": analysis_data.get("goal_predictions", {}).get("btts_yes_prob", 0) * 100, # <-- WAS MISSING
            "BTTS No Prob %": analysis_data.get("goal_predictions", {}).get("btts_no_prob", 0) * 100,
        }
    except KeyError as e:
        print(f"\n❌ Error: Missing expected key in 'analysis_data' dictionary: {e}")
        print("Please ensure the analysis process generates all required data points.")
        return # Stop processing if essential data is missing

    # --- FIX ENDS HERE ---

    # Ensure correct ordering based on df_columns
    # Create DataFrame from the single row of data
    df_new = pd.DataFrame([flat_data])

    # Select and reorder columns - This should now work
    try:
        df_new = df_new[df_columns]
    except KeyError as e:
        # This secondary check is unlikely to fail now but good for debugging
        print(f"\n❌ Internal Error: Mismatch between df_columns and generated flat_data keys: {e}")
        print(f"Expected columns: {df_columns}")
        print(f"Actual columns in DataFrame: {list(df_new.columns)}")
        return


    # --- Rest of the saving logic ---
    try:
        if os.path.exists(EXCEL_FILE_PATH):
            df_existing = pd.read_excel(EXCEL_FILE_PATH)
            # Check columns before concat
            if set(df_columns) == set(df_existing.columns):
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                # Ensure final combined df also has the desired column order
                df_combined = df_combined[df_columns]
            else:
                print(
                    f"\n⚠️ Warning: Excel columns in '{EXCEL_FILE_PATH}' differ from current structure.")
                print("Expected:", df_columns)
                print("Found in Excel:", list(df_existing.columns))
                print("Appending might cause issues. Suggest backing up/renaming the old file first.")
                # Decide how to handle - here we stop to be safe
                print("Saving stopped to prevent data mismatch. Please check the Excel file.")
                return # Stop execution
        else:
            df_combined = df_new # Already has the correct columns and order

        df_combined.to_excel(EXCEL_FILE_PATH, index=False)
        print(f"\n📊 Match analysis saved to '{EXCEL_FILE_PATH}'.")

    except PermissionError:
        print(
            f"\n❌ Error saving to Excel: Permission denied. Make sure '{EXCEL_FILE_PATH}' is not open or write-protected.")
    except Exception as e:
        print(f"\n❌ Error saving to Excel: {e}")

# --- Main Execution ---

def run_match_prediction():
    """Guides user through input, runs calculations, and displays results."""
    print("=== Advanced Soccer Match Outcome Predictor ===")
    help_user()

    # 1. Get Basic Info
    home_team = input("Enter Home Team Name: ")
    away_team = input("Enter Away Team Name: ")

    print("\n--- Enter Team Statistics (Home/Away Specific) ---")
    home_stats = {
        'home_avg_goals_scored': get_float_input(f"{home_team} - Avg goals scored AT HOME"),
        'home_avg_goals_conceded': get_float_input(f"{home_team} - Avg goals conceded AT HOME"),
    }
    away_stats = {
        'away_avg_goals_scored': get_float_input(f"{away_team} - Avg goals scored AWAY"),
        'away_avg_goals_conceded': get_float_input(f"{away_team} - Avg goals conceded AWAY"),
    }

    print("\n--- Enter League Averages ---")
    league_avgs = {
        'home': get_float_input("League avg HOME goals per game", default=DEFAULT_LEAGUE_AVG_HOME_GOALS),
        'away': get_float_input("League avg AWAY goals per game", default=DEFAULT_LEAGUE_AVG_AWAY_GOALS),
    }

    # 2. Calculate Base xG
    base_xg_home, base_xg_away = calculate_base_xg(home_stats, away_stats, league_avgs)

    # 3. Get Adjustment Factors
    print("\n--- Enter Adjustment Factors ---")
    adjustments = {}
    # Form - Using Points in Last 5
    adjustments['home_relative_form_pct'] = get_float_input(f"{home_team} - Relative Form % (Recent PPG vs Season PPG)")
    adjustments['away_relative_form_pct'] = get_float_input(f"{away_team} - Relative Form % (Recent PPG vs Season PPG)")
    # Form - Alternative: Percentage Change (Uncomment if you prefer)
    # adjustments['home_form_pct'] = get_float_input(f"{home_team} - Form (% change, e.g., 10 for 10% up)") / 100
    # adjustments['away_form_pct'] = get_float_input(f"{away_team} - Form (% change, e.g., -5 for 5% down)") / 100

    # Injuries - More Granular
    adjustments['home_key_injuries'] = get_int_input(f"{home_team} - KEY players missing (0-5)", 0, 5)
    adjustments['home_other_injuries'] = get_int_input(f"{home_team} - OTHER important players missing (0-5)", 0, 5)
    adjustments['away_key_injuries'] = get_int_input(f"{away_team} - KEY players missing (0-5)", 0, 5)
    adjustments['away_other_injuries'] = get_int_input(f"{away_team} - OTHER important players missing (0-5)", 0, 5)

    adjustments['weather'] = get_int_input("Weather Conditions (1=Clear, 2=Rain/Wind, 3=Extreme)", 1, 3)
    adjustments['home_adv_ppg_diff'] = get_float_input(f"{home_team} - Home Advantage (Home PPG - Away PPG)")
    # MODIFIED: Get PPI instead of Elo
    adjustments['home_ppi'] = get_float_input(f"{home_team} - Points Performance Index (PPI)")
    adjustments['away_ppi'] = get_float_input(f"{away_team} - Points Performance Index (PPI)")
    # Optional Inputs (Add more as needed)
    # adjustments['match_importance'] = get_int_input("Match Importance (1=Low, 2=Medium, 3=High)", 1, 3)
    # adjustments['home_rest_days'] = get_int_input(f"{home_team} - Days since last match", 0)
    # adjustments['away_rest_days'] = get_int_input(f"{away_team} - Days since last match", 0)

    # 4. Adjust xG
    print("\n--- Applying Adjustments ---")
    adj_xg_home, adj_xg_away = adjust_xg(base_xg_home, base_xg_away, adjustments)
    print(f"🔢 Final Adjusted xG — Home: {adj_xg_home:.2f}, Away: {adj_xg_away:.2f}")

    # 5. Simulate Match Outcomes (Poisson)
    simulation_results = simulate_match_poisson(adj_xg_home, adj_xg_away) # Get dict with probs and arrays
    poisson_probs = simulation_results['probabilities'] # Extract probabilities
    print(f"\n🎲 Poisson Simulation Results (before Elo): "
          f"HW={poisson_probs['home_win']:.2%}, D={poisson_probs['draw']:.2%}, AW={poisson_probs['away_win']:.2%}")

    # 5b. Analyze Goal Outcomes from Simulation
    goal_predictions = analyze_goal_outcomes(
        simulation_results['simulated_home_goals'],
        simulation_results['simulated_away_goals']
    )
    print("\n--- Goal Predictions (Based on Simulation) ---")
    print(f"🥅 Most Likely Score: {goal_predictions['most_likely_score']}")
    print(f"📈 Over 2.5 Goals Prob: {goal_predictions['over_2_5_prob']:.2%}")
    print(f"📉 Under 2.5 Goals Prob: {goal_predictions['under_2_5_prob']:.2%}")
    print(f"⚽ BTTS (Yes) Prob: {goal_predictions['btts_yes_prob']:.2%}")
    print(f"🚫 BTTS (No) Prob: {goal_predictions['btts_no_prob']:.2%}")


    # 6. Adjust Probabilities with Elo
    final_probs = adjust_probabilities_with_ppi(poisson_probs, adjustments['home_ppi'], adjustments['away_ppi'])
    # 7. Display Final Probabilities (1X2)
    print("\n--- Final Predicted Probabilities (1X2) ---")
    print(f"🏠 Home Win: {final_probs['home_win']:.2%}")
    print(f"⚖️ Draw:     {final_probs['draw']:.2%}")
    print(f"✈️ Away Win: {final_probs['away_win']:.2%}")

    # 8. Store Results
    analysis_summary = {
        "home_team": home_team,
        "away_team": away_team,
        "base_xg": {"home": base_xg_home, "away": base_xg_away},
        "adjusted_xg": {"home": adj_xg_home, "away": adj_xg_away},
        "adjustments": adjustments, # Contains 'home_ppi', 'away_ppi' now
        "poisson_probs": poisson_probs,
        "final_probs": final_probs,
        "goal_predictions": goal_predictions
    }
    store_match_analysis_to_excel(analysis_summary) # Pass the updated summary

# --- Run the predictor ---
if __name__ == "__main__":
    run_match_prediction()


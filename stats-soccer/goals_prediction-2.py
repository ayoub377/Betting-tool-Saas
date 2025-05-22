import numpy as np

def help_user():
    print("\n=== Help: Input Guide ===")
    print("1. Team Statistics: Avg goals scored/conceded at home/away.")
    print("2. League Averages: Defaults are 1.5 (home) and 1.2 (away).")
    print("3. Team Form: % change in performance over the last 5 matches.")
    print("4. Injuries/Suspensions: Number of key players missing.")
    print("5. Weather Conditions: Rain, Wind, Extreme Heat (1-3 scale).")
    print("6. Home Advantage: PPG difference for home team.")
    print("7. Team Strength: Elo rating or SPI (Soccer Power Index).\n")

def estimate_xg_from_user():
    print("\n--- Enter Team Statistics ---")
    home_attack = float(input("Home Team - Avg goals scored at home: "))
    home_defense = float(input("Home Team - Avg goals conceded at home: "))
    away_attack = float(input("Away Team - Avg goals scored away: "))
    away_defense = float(input("Away Team - Avg goals conceded away: "))

    league_avg_home_goals = input("League avg home goals per game (default=1.5): ")
    league_avg_away_goals = input("League avg away goals per game (default=1.2): ")

    league_avg_home_goals = float(league_avg_home_goals) if league_avg_home_goals else 1.5
    league_avg_away_goals = float(league_avg_away_goals) if league_avg_away_goals else 1.2

    # Calculate xG
    xG_home = (home_attack / league_avg_home_goals) * (away_defense / league_avg_away_goals)
    xG_away = (away_attack / league_avg_away_goals) * (home_defense / league_avg_home_goals)
    return xG_home, xG_away

def simulate_match_poisson(home_goals_exp, away_goals_exp, n_simulations=10000):
    home_goals = np.random.poisson(home_goals_exp, n_simulations)
    away_goals = np.random.poisson(away_goals_exp, n_simulations)

    home_wins = np.sum(home_goals > away_goals) / n_simulations
    draws = np.sum(home_goals == away_goals) / n_simulations
    away_wins = np.sum(home_goals < away_goals) / n_simulations

    return {'home_win': home_wins, 'draw': draws, 'away_win': away_wins}

def adjust_with_team_strength(probabilities, home_elo, away_elo):
    elo_diff = home_elo - away_elo
    elo_adj_factor = 1 / (1 + 10 ** (-elo_diff / 400))  # Logistic function for Elo adjustment

    probabilities['home_win'] *= elo_adj_factor
    probabilities['away_win'] *= (1 - elo_adj_factor)

    # Normalize to ensure total = 1
    total = sum(probabilities.values())
    for key in probabilities:
        probabilities[key] /= total

    return probabilities

def run_match_prediction():
    print("=== Soccer Match Outcome Predictor ===")
    help_user()

    # xG estimation
    xG_home, xG_away = estimate_xg_from_user()

    # Additional inputs
    home_form_pct = float(input("Home Team Form (% change, e.g., 10 for 10% improvement): ")) / 100
    away_form_pct = float(input("Away Team Form (% change, e.g., -5 for 5% decline): ")) / 100
    home_injuries = int(input("Home Team - Key players missing (0-5): "))
    away_injuries = int(input("Away Team - Key players missing (0-5): "))
    weather = int(input("Weather Conditions (1=Normal, 2=Rain/Wind, 3=Extreme Heat): "))
    home_adv_ppg_diff = float(input("Home Advantage (PPG difference, e.g., 0.5): "))
    home_elo = float(input("Home Team Elo Rating (e.g., 1800): "))
    away_elo = float(input("Away Team Elo Rating (e.g., 1700): "))

    # Adjust xG based on additional inputs
    xG_home *= (1 + home_form_pct - 0.1 * home_injuries + 0.05 * home_adv_ppg_diff)
    xG_away *= (1 + away_form_pct - 0.1 * away_injuries)

    # Weather adjustment (reduce xG in adverse conditions)
    if weather == 2:
        xG_home *= 0.9
        xG_away *= 0.9
    elif weather == 3:
        xG_home *= 0.8
        xG_away *= 0.8

    print(f"\n🔢 Adjusted xG — Home: {xG_home:.2f}, Away: {xG_away:.2f}")

    # Simulate match outcomes
    result_probs = simulate_match_poisson(xG_home, xG_away)

    # Adjust for team strength (Elo ratings)
    final_probs = adjust_with_team_strength(result_probs, home_elo, away_elo)

    # Output
    print("\n--- Final Match Outcome Probabilities ---")
    print(f"🏠 Home Win Probability: {final_probs['home_win']:.2%}")
    print(f"🤝 Draw Probability:     {final_probs['draw']:.2%}")
    print(f"🛫 Away Win Probability: {final_probs['away_win']:.2%}")

# Run the prediction
run_match_prediction()

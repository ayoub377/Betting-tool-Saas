import pickle
import pandas as pd
import numpy as np
import math
from scipy.special import loggamma
from scipy.optimize import minimize
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional
import datetime

from scipy.stats import poisson

# --- Configuration ---
DATA_FOLDER_BASE = Path("./data")  # Base folder containing league subfolders (e.g., ./data/SerieA, ./data/EPL)
CSV_PATTERN = "*.csv"  # Assumes all CSVs in the league's subfolder are relevant match data
REQUIRED_COLS = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
FIXED_XI = 0.0076

MAX_GOALS_PREDICT = 7  # For prediction function later
MODEL_DIR = Path("./models")  # Directory to store saved model files
MODEL_DIR.mkdir(parents=True, exist_ok=True)  # Ensure model directory exists
DEFAULT_MODEL_FILENAME_TEMPLATE = 'dixon_coles_{league}_model.pkl'  # Template for saved parameters
FORCE_REFIT_GLOBAL = False  # Global setting, can be overridden per league during training


# --- Helper Function for Model File Path ---
def get_model_file_path(league_name: str, template: str = DEFAULT_MODEL_FILENAME_TEMPLATE) -> Path:
    """Constructs the model file path for a given league."""
    # Sanitize league_name for filename (lowercase, replace spaces with underscores)
    sanitized_league_name = league_name.lower().replace(" ", "_").replace("/", "_")
    filename = template.format(league=sanitized_league_name)
    return MODEL_DIR / filename


# --- 1. Data Loading and Combination (League Specific) ---
def load_and_combine_data(league_name: str, data_folder_base: Path, pattern: str,
                          required_cols: List[str]) -> pd.DataFrame:
    """Loads all CSVs matching pattern in the league's data_folder and combines them."""
    league_data_folder = data_folder_base / league_name
    if not league_data_folder.exists() or not league_data_folder.is_dir():
        raise FileNotFoundError(f"Data folder for league '{league_name}' not found at {league_data_folder}")

    all_files = list(league_data_folder.glob(pattern))
    if not all_files:
        raise FileNotFoundError(f"No CSV files found matching '{pattern}' in {league_data_folder}")

    df_list = []
    print(f"Loading data for league: {league_name} from {league_data_folder}")
    print(f"Found {len(all_files)} files to load...")
    potential_date_formats = ["%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"]  # Add more if needed

    for f in all_files:
        try:
            # Read first, then parse dates robustly
            df_temp = pd.read_csv(f, usecols=required_cols)

            # --- Robust Date Parsing ---
            original_date_col = df_temp['Date'].copy()  # Keep original for reference if needed
            parsed_dates = pd.to_datetime(df_temp['Date'], errors='coerce',
                                          dayfirst=True)  # Try pandas intelligent guessing first (with dayfirst hint)

            # If guessing failed for some, try specific formats
            if parsed_dates.isnull().any():
                print(f"  Info: Initial date parsing failed for some rows in {f.name}. Trying specific formats...")
                for fmt in potential_date_formats:
                    # Only try parsing the ones that are still NaT
                    mask_to_parse = parsed_dates.isnull()
                    if not mask_to_parse.any(): break  # Stop if all parsed
                    parsed_subset = pd.to_datetime(df_temp.loc[mask_to_parse, 'Date'], format=fmt, errors='coerce')
                    parsed_dates.loc[mask_to_parse] = parsed_subset
                    # print(f"    Tried format '{fmt}', NaNs remaining: {parsed_dates.isnull().sum()}") # Optional debug line

            df_temp['Date'] = parsed_dates  # Assign the parsed dates back

            # Check for unparsed dates
            if df_temp['Date'].isnull().any():
                num_failed = df_temp['Date'].isnull().sum()
                print(f"  Warning: Could not parse {num_failed} date(s) in {f.name}. They will be NaT.")
                # Optional: Show failed dates
                # print(f"    Failed original dates: {original_date_col[df_temp['Date'].isnull()].unique()[:5]}...")

            df_list.append(df_temp)
            print(f"  Loaded and parsed dates for {f.name}")

        except KeyError as e:
            print(f"Warning: Missing required column in {f.name}. Error: {e}. Skipping file.")
        except Exception as e:
            print(f"Warning: Could not load or process {f.name}. Error: {e}")

    if not df_list:
        raise ValueError(f"No dataframes were successfully loaded for league {league_name}.")

    full_df = pd.concat(df_list, ignore_index=True)

    # Final check on the combined dataframe's Date column type
    if not pd.api.types.is_datetime64_any_dtype(full_df['Date']):
        # This case should be less likely now with the robust parsing, but as a fallback:
        print("Warning: Combined 'Date' column is not datetime. This might indicate widespread parsing issues.")
        # Optionally, try one last conversion attempt here, though it's better to fix it file-by-file above
        # full_df['Date'] = pd.to_datetime(full_df['Date'], errors='coerce')

    print(f"Combined data shape for {league_name}: {full_df.shape}")
    print(f"Date column dtype after loading: {full_df['Date'].dtype}")  # Verify dtype
    return full_df


# --- 2. Data Cleaning and Preprocessing (Reusable Logic) ---
def preprocess_data(df: pd.DataFrame, league_name: str) -> Tuple[pd.DataFrame, Dict[str, int], int]:
    """Cleans data, creates team IDs, and calculates time differences for a given league's data."""
    print(f"\n--- Preprocessing data for league: {league_name} ---")

    # --- Essential Data Type Checks and Initial Cleaning ---
    # Ensure 'Date' column exists and attempt conversion if not already datetime
    if 'Date' not in df.columns:
        raise ValueError(f"'Date' column missing from the combined dataframe for {league_name}.")
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        print(f"Warning: 'Date' column dtype is {df['Date'].dtype} before preprocessing. Attempting conversion.")
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        if not pd.api.types.is_datetime64_any_dtype(df['Date']):
            raise TypeError(f"Failed to convert 'Date' column to datetime for {league_name}.")

    # Drop rows with missing essential info (including dates that failed parsing)
    initial_rows = len(df)
    required_subset = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
    df.dropna(subset=required_subset, inplace=True)
    if len(df) < initial_rows:
        print(f"Dropped {initial_rows - len(df)} rows with missing essential data (including NaT dates).")

    if df.empty:
        raise ValueError(f"No valid rows remaining for {league_name} after dropping missing essential data.")

    # Ensure goals are integers
    try:
        df['FTHG'] = df['FTHG'].astype(int)
        df['FTAG'] = df['FTAG'].astype(int)
    except ValueError as e:
        print(
            f"Error converting goal columns to integers for {league_name}. Check data for non-numeric goal values. Error: {e}")
        # Optional: Find problematic rows
        # print(df[pd.to_numeric(df['FTHG'], errors='coerce').isna() | pd.to_numeric(df['FTAG'], errors='coerce').isna()])
        raise  # Re-raise the error after printing info

    # --- Team Name Consistency Check ---
    # (Keep this section as is)
    all_teams = pd.concat([df['HomeTeam'], df['AwayTeam']]).unique()
    all_teams.sort()
    print(f"\nFound {len(all_teams)} unique team names in {league_name}. Review carefully for inconsistencies:")
    if len(all_teams) > 50:
        print(all_teams[:25], "\n...\n", all_teams[-25:])
    else:
        print(all_teams)
    # --- Add league-specific cleaning here if needed ---

    unique_teams_cleaned = pd.concat([df['HomeTeam'], df['AwayTeam']]).unique()
    unique_teams_cleaned.sort()
    team_map = {team_name: i for i, team_name in enumerate(unique_teams_cleaned)}
    num_teams = len(team_map)
    print(f"\nCreated IDs for {num_teams} teams in {league_name}.")

    df['HomeTeamID'] = df['HomeTeam'].map(team_map)
    df['AwayTeamID'] = df['AwayTeam'].map(team_map)

    if df['HomeTeamID'].isnull().any() or df['AwayTeamID'].isnull().any():
        print(f"Warning: Some teams in {league_name} failed to map to IDs. Check cleaning steps!")

    # Sort by date (important for time weighting reference)
    df.sort_values(by='Date', inplace=True)
    df.reset_index(drop=True, inplace=True)

    # --- Calculate Time Difference ---
    # This check should now always pass if the initial checks/drops worked
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        raise TypeError(f"Internal Error: 'Date' column is not datetime before TimeDiff calculation for {league_name}.")

    reference_date = df['Date'].max()  # Should be a valid Timestamp now
    # No need to check tzinfo if we ensure dates are naive UTC or consistent
    # Assuming naive datetime objects after parsing
    df['TimeDiff'] = (reference_date - df['Date']).dt.days  # Simpler if both are naive
    df['TimeDiff'] = df['TimeDiff'].clip(lower=0)

    print(f"Preprocessing complete for {league_name}. Final data shape: {df.shape}")
    if not df.empty:
        print(f"Date range for {league_name}: {df['Date'].min().date()} to {df['Date'].max().date()}")
    else:
        print(f"No data remaining for {league_name} after preprocessing.")

    return df, team_map, num_teams


# --- 3. Model Functions (Reusable Core Logic) ---
def dixon_coles_tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    lam = max(lam, 1e-9)
    mu = max(mu, 1e-9)
    if x == 0 and y == 0:
        tau = 1.0 - rho * lam * mu
    elif x == 0 and y == 1:
        tau = 1.0 + rho * mu
    elif x == 1 and y == 0:
        tau = 1.0 + rho * lam
    elif x == 1 and y == 1:
        tau = 1.0 - rho
    else:
        tau = 1.0
    return max(0.0, tau)


def calculate_dixon_coles_probs(lambda_home: float, lambda_away: float, rho: float,
                                max_goals: int = MAX_GOALS_PREDICT) -> Dict[str, Any]:
    if lambda_home <= 0 or lambda_away <= 0:
        # print(f"Warning: Lambda values must be positive. Got lambda_home={lambda_home}, lambda_away={lambda_away}. Returning default.")
        default_prob = 1 / ((max_goals + 1) ** 2)
        prob_matrix = np.full((max_goals + 1, max_goals + 1), default_prob)
        # Return structure consistent with successful calculation
        return {
            'probabilities_1x2': {'home_win': 1 / 3, 'draw': 1 / 3, 'away_win': 1 / 3},
            'goal_predictions': {'most_likely_score': 'N/A', 'most_likely_score_prob': 0.0,
                                 'over_2_5_prob': 0.0, 'under_2_5_prob': 1.0,
                                 'btts_yes_prob': 0.0, 'btts_no_prob': 1.0},
            'prob_matrix': prob_matrix
        }

    prob_matrix = np.zeros((max_goals + 1, max_goals + 1))
    home_poisson_pmf = poisson.pmf(np.arange(max_goals + 1), lambda_home)
    away_poisson_pmf = poisson.pmf(np.arange(max_goals + 1), lambda_away)

    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            tau = dixon_coles_tau(hg, ag, lambda_home, lambda_away, rho)
            prob = tau * home_poisson_pmf[hg] * away_poisson_pmf[ag]
            prob_matrix[hg, ag] = max(0.0, prob)

    total_prob = np.sum(prob_matrix)
    if total_prob > 1e-9:
        prob_matrix /= total_prob
    else:
        # print(f"Warning: Total probability near zero. Using uniform fallback. Lambdas: H={lambda_home:.2f}, A={lambda_away:.2f}, Rho={rho:.2f}")
        default_prob = 1 / ((max_goals + 1) ** 2)
        prob_matrix = np.full((max_goals + 1, max_goals + 1), default_prob)

    p_home_win = np.sum(np.tril(prob_matrix, k=-1))
    p_draw = np.sum(np.diag(prob_matrix))
    p_away_win = np.sum(np.triu(prob_matrix, k=1))
    norm_factor = p_home_win + p_draw + p_away_win
    if norm_factor > 1e-9:
        p_home_win /= norm_factor
        p_draw /= norm_factor
        p_away_win /= norm_factor

    probabilities_1x2 = {'home_win': p_home_win, 'draw': p_draw, 'away_win': p_away_win}

    max_prob_idx = np.unravel_index(np.argmax(prob_matrix, axis=None), prob_matrix.shape)
    most_likely_score_str = f"{max_prob_idx[0]}-{max_prob_idx[1]}"
    most_likely_score_prob = prob_matrix[max_prob_idx]

    goals_home, goals_away = np.meshgrid(np.arange(max_goals + 1), np.arange(max_goals + 1), indexing='ij')
    total_goals_matrix = goals_home + goals_away
    over_2_5_prob = np.sum(prob_matrix[total_goals_matrix > 2.5])
    under_2_5_prob = 1.0 - over_2_5_prob

    btts_yes_mask = (goals_home > 0) & (goals_away > 0)
    btts_yes_prob = np.sum(prob_matrix[btts_yes_mask])
    btts_no_prob = 1.0 - btts_yes_prob

    goal_predictions = {
        'most_likely_score': most_likely_score_str,
        'most_likely_score_prob': most_likely_score_prob,
        'over_2_5_prob': over_2_5_prob, 'under_2_5_prob': under_2_5_prob,
        'btts_yes_prob': btts_yes_prob, 'btts_no_prob': btts_no_prob
    }
    return {'probabilities_1x2': probabilities_1x2, 'goal_predictions': goal_predictions, 'prob_matrix': prob_matrix}


def predict_match(home_team_name: str, away_team_name: str,
                  estimated_params: Dict[str, Any], team_map: Dict[str, int],
                  league_name_for_log: str = "Unknown League") -> Optional[Dict[str, Any]]:
    if home_team_name not in team_map or away_team_name not in team_map:
        missing = [t for t in [home_team_name, away_team_name] if t not in team_map]
        print(f"Error: Team(s) not found in {league_name_for_log} model's team map: {', '.join(missing)}")
        return None
    if home_team_name == away_team_name:
        print(f"Error: Home and away team cannot be the same for {league_name_for_log} prediction.")
        return None

    required_keys = ['home_adv', 'rho', 'attack', 'defence']
    if not all(key in estimated_params for key in required_keys):
        missing_keys = [key for key in required_keys if key not in estimated_params]
        print(f"Error: Missing required keys in estimated_params for {league_name_for_log}: {missing_keys}")
        return None

    home_adv = estimated_params['home_adv']
    rho = estimated_params['rho']
    att_ratings = estimated_params['attack']
    def_ratings = estimated_params['defence']

    if not all(t in att_ratings and t in def_ratings for t in [home_team_name, away_team_name]):
        print(f"Error: Ratings for one or both teams not found in estimated_params for {league_name_for_log}.")
        return None

    att_home = att_ratings[home_team_name]
    def_home = def_ratings[home_team_name]
    att_away = att_ratings[away_team_name]
    def_away = def_ratings[away_team_name]

    try:
        log_lam_home = home_adv + att_home + def_away
        log_lam_away = att_away + def_home
        lambda_home = math.exp(log_lam_home)
        lambda_away = math.exp(log_lam_away)
    except OverflowError:
        print(f"Error: Overflow calculating lambdas for {league_name_for_log}. Check parameter magnitudes.")
        return None

    min_lambda = 0.01
    lambda_home = max(min_lambda, lambda_home)
    lambda_away = max(min_lambda, lambda_away)

    print(f"\n--- Predicting Match ({league_name_for_log}): {home_team_name} vs {away_team_name} ---")
    print(f"  Calculated Lambdas -> Home (λ): {lambda_home:.3f}, Away (μ): {lambda_away:.3f}")
    # print(f"  Using Parameters -> Home Adv: {home_adv:.3f}, Rho: {rho:.3f}")
    # print(f"  Team Params -> H Att: {att_home:.3f}, H Def: {def_home:.3f}; A Att: {att_away:.3f}, A Def: {def_away:.3f}")

    prediction_results = calculate_dixon_coles_probs(lambda_home, lambda_away, rho)
    prediction_results['lambda_home'] = lambda_home
    prediction_results['lambda_away'] = lambda_away
    return prediction_results


def neg_log_likelihood(params: np.ndarray, data: pd.DataFrame, team_map: Dict[str, int], num_teams: int) -> float:
    if len(params) != (1 + num_teams + num_teams + 1):
        raise ValueError(f"Incorrect number of parameters. Expected {1 + 2 * num_teams + 1}, got {len(params)}")

    home_adv = params[0]
    att = params[1: num_teams + 1]
    defs = params[num_teams + 1: 2 * num_teams + 1]
    rho = params[2 * num_teams + 1]
    xi = FIXED_XI

    att = att - np.mean(att)  # Sum-to-zero constraint

    total_log_lik = 0.0
    tiny_val = 1e-12

    for _, row in data.iterrows():
        home_id, away_id = row['HomeTeamID'], row['AwayTeamID']
        home_goals, away_goals = row['FTHG'], row['FTAG']
        time_diff = row['TimeDiff']

        log_lam = home_adv + att[home_id] + defs[away_id]
        log_mu = att[away_id] + defs[home_id]
        lam_for_tau = math.exp(log_lam)
        mu_for_tau = math.exp(log_mu)

        weight = math.exp(-xi * time_diff)
        tau = dixon_coles_tau(home_goals, away_goals, lam_for_tau, mu_for_tau, rho)

        log_lik_pois_home = home_goals * log_lam - lam_for_tau - loggamma(home_goals + 1)
        log_lik_pois_away = away_goals * log_mu - mu_for_tau - loggamma(away_goals + 1)
        log_lik_match = log_lik_pois_home + log_lik_pois_away

        if tau > tiny_val:
            log_lik_match += math.log(tau)
        else:
            return 1e10  # Penalize impossible scorelines

        total_log_lik += weight * log_lik_match

    if np.isnan(total_log_lik) or np.isinf(total_log_lik):
        # print("Warning: Log-likelihood is NaN or Inf. Check parameters/data.")
        return 1e10
    return -total_log_lik


# --- 4. Optimization Setup (Reusable Logic) ---
def fit_dixon_coles_model(data: pd.DataFrame, team_map: Dict[str, int], num_teams: int, league_name: str) -> Tuple[
    Any, Optional[Dict[str, Any]]]:
    print(f"\n--- Setting up Optimization for {league_name} ---")
    num_params = 1 + num_teams + num_teams + 1
    initial_params = np.concatenate([np.array([0.1]), np.zeros(num_teams), np.zeros(num_teams), np.array([-0.1])])
    param_bound_val = 5.0
    bounds = [(None, None)] + [(-param_bound_val, param_bound_val)] * (2 * num_teams) + [(-0.9, 0.9)]

    print(f"--- Starting Optimization for {league_name} (this may take several minutes...) ---")
    optimization_result = minimize(
        neg_log_likelihood, initial_params, args=(data, team_map, num_teams),
        method='L-BFGS-B', bounds=bounds, options={'disp': True, 'maxiter': 500}
    )

    param_results = None
    if optimization_result.success:
        print(f"\nOptimization Successful for {league_name}!")
        optimized_params = optimization_result.x
        param_results = {
            'home_adv': optimized_params[0],
            'attack': dict(zip(team_map.keys(), optimized_params[1: num_teams + 1])),
            'defence': dict(zip(team_map.keys(), optimized_params[num_teams + 1: 2 * num_teams + 1])),
            'rho': optimized_params[2 * num_teams + 1],
            'xi': FIXED_XI,
            'final_log_likelihood': -optimization_result.fun
        }
        att_mean = np.mean(list(param_results['attack'].values()))
        param_results['attack'] = {k: v - att_mean for k, v in param_results['attack'].items()}
        # Note: Defence ratings are not typically sum-to-zero constrained in the same way attack ratings are,
        # but sometimes their mean is shifted for interpretability (e.g., to make average defense 0).
        # For consistency with original code, only attack is adjusted here.

        print(f"  Home Advantage: {param_results['home_adv']:.4f}")
        print(f"  Rho (Dependency): {param_results['rho']:.4f}")
        print(f"  Xi (Time Decay): {param_results['xi']:.6f} (Fixed)")
        print(f"  Final Log-Likelihood: {param_results['final_log_likelihood']:.2f}")

        try:
            num_display = 5
            attack_series = pd.Series(param_results['attack']).sort_values(ascending=False)
            print(f"\n--- Top {num_display} Attack Ratings ({league_name}) ---")
            print(attack_series.head(num_display).round(4))
            defence_series = pd.Series(param_results['defence']).sort_values(ascending=True)
            print(f"\n--- Top {num_display} Defence Ratings (Lower is Better) ({league_name}) ---")
            print(defence_series.head(num_display).round(4))
            print("-------------------------------------")
        except Exception as e:
            print(f"\nWarning: Could not display team ratings for {league_name}. Error: {e}")
    else:
        print(f"\nOptimization Failed for {league_name}!")
        print(f"Status: {optimization_result.status}")
        print(f"Message: {optimization_result.message}")

    return optimization_result, param_results


# --- 5. League-Specific Training and Prediction Wrappers ---

def train_model_for_league(league_name: str, force_refit_league: bool = False):
    print(f"\n--- Attempting to Train Model for League: {league_name} ---")
    model_file_path = get_model_file_path(league_name)

    if model_file_path.exists() and not force_refit_league:
        print(f"Model for {league_name} already exists at {model_file_path}. Training skipped.")
        print("To retrain, enable force refit or delete the existing model file.")
        return

    if force_refit_league:
        print(f"Force refit enabled for {league_name}.")

    try:
        raw_data = load_and_combine_data(league_name, DATA_FOLDER_BASE, CSV_PATTERN, REQUIRED_COLS)
        processed_data, team_mapping, n_teams = preprocess_data(raw_data, league_name)

        print(f"\nFiltering matches before training for {league_name}. Original rows: {len(processed_data)}")
        today_date = datetime.date.today()
        # print(f"Filtering out matches on or after: {today_date}")
        if pd.api.types.is_datetime64_any_dtype(processed_data['Date']):
            processed_data = processed_data[processed_data['Date'].dt.date < today_date].copy()
            initial_rows_after_date_filter = len(processed_data)
            processed_data.dropna(subset=['FTHG', 'FTAG'], inplace=True)  # Ensure scores are present
            # if len(processed_data) < initial_rows_after_date_filter:
            #     print(f"Dropped {initial_rows_after_date_filter - len(processed_data)} rows with missing scores after date filtering for {league_name}.")
            print(
                f"Rows after filtering for completed matches (before {today_date}) for {league_name}: {len(processed_data)}")
        else:
            print(f"Warning: 'Date' column is not datetime type for {league_name}. Skipping date filtering.")

        if processed_data.empty:
            raise ValueError(f"No completed matches found in the data for {league_name} after filtering.")

        _, estimated_params_fit = fit_dixon_coles_model(processed_data, team_mapping, n_teams, league_name)

        if estimated_params_fit:
            print(f"\nModel fitting complete for {league_name}.")
            model_data_to_save = {
                'params': estimated_params_fit, 'team_map': team_mapping, 'num_teams': n_teams
            }
            with open(model_file_path, 'wb') as f:
                pickle.dump(model_data_to_save, f)
            print(f"--- Model parameters for {league_name} saved successfully to {model_file_path}! ---")
        else:
            print(f"\nModel fitting failed for {league_name}. No model saved.")

    except FileNotFoundError as e:
        print(f"Error during training for {league_name}: {e}")
    except ValueError as e:
        print(f"Error during training for {league_name}: {e}")
    except TypeError as e:
        print(f"Error during training for {league_name}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during training for {league_name}: {e}")


def load_model_for_league(league_name: str) -> Optional[Tuple[Dict[str, Any], Dict[str, int], int]]:
    model_file_path = get_model_file_path(league_name)
    if not model_file_path.exists():
        print(f"No pre-trained model found for league '{league_name}' at {model_file_path}.")
        print(f"Please train the model for '{league_name}' first or check the league name/data path.")
        return None, None, None

    print(f"--- Loading existing model for {league_name} from {model_file_path} ---")
    try:
        with open(model_file_path, 'rb') as f:
            saved_data = pickle.load(f)
        params, team_map, num_teams = saved_data.get('params'), saved_data.get('team_map'), saved_data.get('num_teams')
        if params and team_map and num_teams is not None:
            print(f"Model for {league_name} loaded successfully. Contains {num_teams} teams.")
            return params, team_map, num_teams
        else:
            print(f"Warning: Loaded model file for {league_name} ({model_file_path}) seems incomplete.")
            return None, None, None
    except Exception as e:
        print(f"Warning: Could not load model file for {league_name} ({model_file_path}). Error: {e}")
        return None, None, None


def predict_for_league(league_name: str):
    print(f"\n--- Attempting to Predict for League: {league_name} ---")
    estimated_params, team_mapping, _ = load_model_for_league(league_name)
    if not estimated_params or not team_mapping:
        print(f"Cannot proceed with prediction for {league_name} as model data is missing/incomplete.")
        return

    print(f"\n--- Enter teams for {league_name} Prediction ---")
    available_teams = sorted(list(team_mapping.keys()))
    if not available_teams:
        print(f"No teams found in the model for {league_name}. Cannot make predictions.")
        return

    print("Available teams in this league model:")
    # Simple column display for many teams
    max_cols = 4
    col_width = max(len(t) for t in available_teams) + 2
    for i in range(0, len(available_teams), max_cols):
        print("".join(team.ljust(col_width) for team in available_teams[i:i + max_cols]))

    home_team_input = input(f"Enter Home Team name (from {league_name}): ").strip()
    away_team_input = input(f"Enter Away Team name (from {league_name}): ").strip()

    match_prediction = predict_match(
        home_team_input, away_team_input, estimated_params, team_mapping, league_name
    )

    if match_prediction:
        print(f"\n---> Prediction Results for {home_team_input} vs {away_team_input} ({league_name}):")
        probs1x2 = match_prediction['probabilities_1x2']
        print(
            f"  Outcome Probs: HW={probs1x2['home_win']:.2%}, D={probs1x2['draw']:.2%}, AW={probs1x2['away_win']:.2%}")
        goal_preds = match_prediction['goal_predictions']
        print(
            f"  Goal Preds:    Score={goal_preds['most_likely_score']} (P={goal_preds['most_likely_score_prob']:.2%}), "
            f"O2.5={goal_preds['over_2_5_prob']:.2%}, BTTS(Y)={goal_preds['btts_yes_prob']:.2%}")
        # print(f"  Expected Goals: H={match_prediction['lambda_home']:.3f}, A={match_prediction['lambda_away']:.3f}")


# --- Main Execution ---
if __name__ == "__main__":
    while True:
        print("\n--- Dixon-Coles Football Model ---")
        print("Available actions: 'train', 'predict', 'list_data', 'list_models', 'exit'")
        league_name_input = input(
            "Enter the league identifier (e.g., SerieA, EPL). This should match a subfolder in './data/': ").strip()

        if not league_name_input:
            print("League identifier cannot be empty.")
            continue
        if league_name_input.lower() == 'exit':
            print("Exiting.")
            break

        action = input(
            f"Action for '{league_name_input}'? (train/predict/list_data/list_models/back): ").strip().lower()

        if action == "train":
            force_refit_current = FORCE_REFIT_GLOBAL
            if not force_refit_current:
                force_refit_input = input(
                    f"Force refit for {league_name_input} if model exists? (yes/no, default no): ").strip().lower()
                force_refit_current = (force_refit_input == 'yes')
            train_model_for_league(league_name_input, force_refit_current)
        elif action == "predict":
            predict_for_league(league_name_input)
        elif action == "list_data":
            try:
                league_data_path = DATA_FOLDER_BASE / league_name_input
                if league_data_path.is_dir():
                    print(f"Data files found for '{league_name_input}' in {league_data_path}:")
                    files = list(league_data_path.glob(CSV_PATTERN))
                    if files:
                        for f_path in files: print(f"  - {f_path.name}")
                    else:
                        print(f"  No CSV files matching '{CSV_PATTERN}' found.")
                else:
                    print(f"Data directory {league_data_path} does not exist for league '{league_name_input}'.")
            except Exception as e:
                print(f"Error listing data for {league_name_input}: {e}")
        elif action == "list_models":
            model_file = get_model_file_path(league_name_input)
            if model_file.exists():
                print(f"Model file for '{league_name_input}' exists: {model_file}")
            else:
                print(f"No model file found for '{league_name_input}' at expected location: {model_file}")
        elif action == "back":
            continue
        elif action == "exit":  # Allow exiting from action prompt too
            print("Exiting.")
            break
        else:
            print("Invalid action. Please enter 'train', 'predict', 'list_data', 'list_models', or 'back'.")

import pickle
import pandas as pd
import numpy as np
import math
import logging
from scipy.special import loggamma
from scipy.optimize import minimize
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional
import datetime
import re
from scipy.stats import poisson

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# !!! IMPORTANT: Update these paths to match your new structure !!!
DATA_FOLDER_BASE = Path("./app/data/leagues")
MODEL_DIR = Path("./trained_models")
# !!! -------------------------------------------------------- !!!

CSV_PATTERN = "*.csv"
REQUIRED_COLS = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
FIXED_XI = 0.0076
MAX_GOALS_PREDICT = 7
MODEL_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_MODEL_FILENAME_TEMPLATE = 'dixon_coles_{league}_model.pkl'

# --- In-Memory Model Cache ---
# This dictionary will store loaded models to avoid disk I/O on every prediction
_model_cache: Dict[str, Tuple[Dict, Dict, int]] = {}


# --- Helper Function for Model File Path ---
def get_model_file_path(league_name: str, template: str = DEFAULT_MODEL_FILENAME_TEMPLATE) -> Path:
    """Constructs the model file path for a given league."""
    sanitized_league_name = league_name.lower().replace(" ", "_").replace("/", "_")
    filename = template.format(league=sanitized_league_name)
    return MODEL_DIR / filename


# --- Custom Exceptions for API Error Handling ---
class ModelNotFoundError(Exception):
    pass


class TeamNotFoundError(Exception):
    pass


class DataNotFoundError(Exception):
    pass


# --- 1. Data Loading and Combination (League Specific) ---
def load_and_combine_data(league_name: str, data_folder_base: Path, pattern: str,
                          required_cols: List[str]) -> pd.DataFrame:
    """Loads all CSVs matching pattern in the league's data_folder and combines them."""
    league_data_folder = data_folder_base / league_name
    if not league_data_folder.exists() or not league_data_folder.is_dir():
        raise DataNotFoundError(f"Data folder for league '{league_name}' not found at {league_data_folder}")

    all_files = list(league_data_folder.glob(pattern))
    if not all_files:
        raise DataNotFoundError(f"No CSV files found matching '{pattern}' in {league_data_folder}")

    df_list = []
    logging.info(f"Loading data for league: {league_name} from {league_data_folder}")
    potential_date_formats = ["%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"]

    for f in all_files:
        try:
            df_temp = pd.read_csv(f, usecols=required_cols)
            parsed_dates = pd.to_datetime(df_temp['Date'], errors='coerce', dayfirst=True)
            if parsed_dates.isnull().any():
                for fmt in potential_date_formats:
                    mask_to_parse = parsed_dates.isnull()
                    if not mask_to_parse.any(): break
                    parsed_subset = pd.to_datetime(df_temp.loc[mask_to_parse, 'Date'], format=fmt, errors='coerce')
                    parsed_dates.loc[mask_to_parse] = parsed_subset
            df_temp['Date'] = parsed_dates
            if df_temp['Date'].isnull().any():
                logging.warning(f"Could not parse {df_temp['Date'].isnull().sum()} date(s) in {f.name}.")
            df_list.append(df_temp)
        except Exception as e:
            logging.warning(f"Could not load or process {f.name}. Error: {e}")

    if not df_list:
        raise ValueError(f"No dataframes were successfully loaded for league {league_name}.")

    full_df = pd.concat(df_list, ignore_index=True)
    return full_df


# --- 2. Data Cleaning and Preprocessing (Reusable Logic) ---
def preprocess_data(df: pd.DataFrame, league_name: str) -> Tuple[pd.DataFrame, Dict[str, int], int]:
    """Cleans data, creates team IDs, and calculates time differences for a given league's data."""
    logging.info(f"Preprocessing data for league: {league_name}")
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    initial_rows = len(df)
    df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'], inplace=True)
    if len(df) < initial_rows:
        logging.info(f"Dropped {initial_rows - len(df)} rows with missing essential data.")
    if df.empty:
        raise ValueError(f"No valid rows remaining for {league_name}.")
    df['FTHG'] = df['FTHG'].astype(int)
    df['FTAG'] = df['FTAG'].astype(int)
    unique_teams_cleaned = pd.concat([df['HomeTeam'], df['AwayTeam']]).unique()
    unique_teams_cleaned.sort()
    team_map = {team_name: i for i, team_name in enumerate(unique_teams_cleaned)}
    num_teams = len(team_map)
    df['HomeTeamID'] = df['HomeTeam'].map(team_map)
    df['AwayTeamID'] = df['AwayTeam'].map(team_map)
    df.sort_values(by='Date', inplace=True)
    df.reset_index(drop=True, inplace=True)
    reference_date = df['Date'].max()
    df['TimeDiff'] = (reference_date - df['Date']).dt.days
    df['TimeDiff'] = df['TimeDiff'].clip(lower=0)
    return df, team_map, num_teams


# --- 3. Model Functions (Core Logic - mostly unchanged) ---
def dixon_coles_tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    lam = max(lam, 1e-9);
    mu = max(mu, 1e-9)
    if x == 0 and y == 0: return 1.0 - rho * lam * mu
    if x == 0 and y == 1: return 1.0 + rho * mu
    if x == 1 and y == 0: return 1.0 + rho * lam
    if x == 1 and y == 1: return 1.0 - rho
    return 1.0


def calculate_dixon_coles_probs(lambda_home: float, lambda_away: float, rho: float,
                                max_goals: int = MAX_GOALS_PREDICT) -> Dict[str, Any]:
    prob_matrix = np.zeros((max_goals + 1, max_goals + 1))
    home_poisson_pmf = poisson.pmf(np.arange(max_goals + 1), lambda_home)
    away_poisson_pmf = poisson.pmf(np.arange(max_goals + 1), lambda_away)
    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            tau = dixon_coles_tau(hg, ag, lambda_home, lambda_away, rho)
            prob_matrix[hg, ag] = max(0.0, tau * home_poisson_pmf[hg] * away_poisson_pmf[ag])
    prob_matrix /= np.sum(prob_matrix)
    p_home_win = np.sum(np.tril(prob_matrix, k=-1))
    p_draw = np.sum(np.diag(prob_matrix))
    p_away_win = np.sum(np.triu(prob_matrix, k=1))
    max_prob_idx = np.unravel_index(np.argmax(prob_matrix, axis=None), prob_matrix.shape)
    goals_home, goals_away = np.meshgrid(np.arange(max_goals + 1), np.arange(max_goals + 1), indexing='ij')
    total_goals_matrix = goals_home + goals_away
    over_2_5_prob = np.sum(prob_matrix[total_goals_matrix > 2.5])
    btts_yes_prob = np.sum(prob_matrix[(goals_home > 0) & (goals_away > 0)])
    return {
        'probabilities_1x2': {'home_win': p_home_win, 'draw': p_draw, 'away_win': p_away_win},
        'goal_predictions': {
            'most_likely_score': f"{max_prob_idx[0]}-{max_prob_idx[1]}",
            'most_likely_score_prob': prob_matrix[max_prob_idx],
            'over_2_5_prob': over_2_5_prob, 'under_2_5_prob': 1.0 - over_2_5_prob,
            'btts_yes_prob': btts_yes_prob, 'btts_no_prob': 1.0 - btts_yes_prob
        },
        'prob_matrix': prob_matrix.tolist()  # Convert to list for JSON serialization
    }


def predict_match(home_team_name: str, away_team_name: str, estimated_params: Dict[str, Any],
                  team_map: Dict[str, int]) -> Optional[Dict[str, Any]]:
    if home_team_name not in team_map or away_team_name not in team_map:
        missing = [t for t in [home_team_name, away_team_name] if t not in team_map]
        raise TeamNotFoundError(f"Team(s) not found in model's team map: {', '.join(missing)}")
    if home_team_name == away_team_name:
        raise ValueError("Home and away team cannot be the same.")

    home_adv, rho = estimated_params['home_adv'], estimated_params['rho']
    att_ratings, def_ratings = estimated_params['attack'], estimated_params['defence']

    log_lam_home = home_adv + att_ratings[home_team_name] + def_ratings[away_team_name]
    log_lam_away = att_ratings[away_team_name] + def_ratings[home_team_name]
    lambda_home = max(0.01, math.exp(log_lam_home))
    lambda_away = max(0.01, math.exp(log_lam_away))

    prediction_results = calculate_dixon_coles_probs(lambda_home, lambda_away, rho)
    prediction_results['lambda_home'] = lambda_home
    prediction_results['lambda_away'] = lambda_away
    return prediction_results


def neg_log_likelihood(params: np.ndarray, data: pd.DataFrame, team_map: Dict[str, int], num_teams: int) -> float:
    home_adv, att, defs, rho, xi = params[0], params[1:num_teams + 1], params[num_teams + 1:2 * num_teams + 1], params[
        2 * num_teams + 1], FIXED_XI
    att = att - np.mean(att)
    total_log_lik = 0.0
    for _, row in data.iterrows():
        h_id, a_id, hg, ag, t_diff = row['HomeTeamID'], row['AwayTeamID'], row['FTHG'], row['FTAG'], row['TimeDiff']
        log_lam = home_adv + att[h_id] + defs[a_id]
        log_mu = att[a_id] + defs[h_id]
        lam, mu = math.exp(log_lam), math.exp(log_mu)
        weight = math.exp(-xi * t_diff)
        tau = dixon_coles_tau(hg, ag, lam, mu, rho)
        log_lik_match = (hg * log_lam - lam - loggamma(hg + 1)) + (ag * log_mu - mu - loggamma(ag + 1))
        if tau > 1e-12:
            log_lik_match += math.log(tau)
        else:
            return 1e10
        total_log_lik += weight * log_lik_match
    return -total_log_lik


# --- 4. Optimization Setup (Reusable Logic) ---
def fit_dixon_coles_model(data: pd.DataFrame, team_map: Dict[str, int], num_teams: int, league_name: str) -> Optional[
    Dict[str, Any]]:
    logging.info(f"Starting Optimization for {league_name}...")
    num_params = 1 + 2 * num_teams + 1
    initial_params = np.concatenate([np.array([0.1]), np.zeros(num_teams * 2), np.array([-0.1])])
    bounds = [(None, None)] + [(-5.0, 5.0)] * (2 * num_teams) + [(-0.9, 0.9)]

    # Set optimization options with higher limits for large datasets
    # Scale limits based on dataset size for better convergence
    scale_factor = max(1, (num_teams * len(data)) // 1000)  # Scale based on complexity
    options = {
        'maxiter': min(50000, 15000 * scale_factor),  # Scale iterations based on complexity
        'maxfun': min(100000, 25000 * scale_factor),  # Scale function evaluations based on complexity
        'ftol': 1e-9,  # Function tolerance
        'gtol': 1e-5  # Gradient tolerance
    }

    logging.info(f"Optimization parameters: {num_teams} teams, {len(data)} matches, {num_params} parameters")
    logging.info(
        f"Optimization limits: maxiter={options['maxiter']}, maxfun={options['maxfun']}, scale_factor={scale_factor}")

    res = minimize(neg_log_likelihood, initial_params, args=(data, team_map, num_teams),
                   method='L-BFGS-B', bounds=bounds, options=options)

    if res.success:
        logging.info(f"Optimization Successful for {league_name}!")
        params = res.x
        att_mean = np.mean(params[1:num_teams + 1])
        return {
            'home_adv': params[0],
            'attack': {k: v - att_mean for k, v in zip(team_map.keys(), params[1:num_teams + 1])},
            'defence': dict(zip(team_map.keys(), params[num_teams + 1:2 * num_teams + 1])),
            'rho': params[2 * num_teams + 1],
            'xi': FIXED_XI,
            'final_log_likelihood': -res.fun
        }
    else:
        logging.error(f"Optimization Failed for {league_name}: {res.message}")
        return None


# --- 5. API-Facing Service Functions ---

def train_model_for_league(league_name: str, force_refit: bool = False):
    """Main training orchestrator function."""
    model_file_path = get_model_file_path(league_name)

    if model_file_path.exists() and not force_refit:
        msg = f"Model for {league_name} already exists. Training skipped."
        logging.info(msg)
        return {"status": "skipped", "message": msg, "model_path": str(model_file_path)}

    try:
        raw_data = load_and_combine_data(league_name, DATA_FOLDER_BASE, CSV_PATTERN, REQUIRED_COLS)
        processed_data, team_mapping, n_teams = preprocess_data(raw_data, league_name)

        # Filter for completed matches before today
        today_date = datetime.date.today()
        training_data = processed_data[processed_data['Date'].dt.date < today_date].copy()
        if training_data.empty:
            raise ValueError(f"No completed matches found to train on for {league_name}.")

        estimated_params = fit_dixon_coles_model(training_data, team_mapping, n_teams, league_name)

        if estimated_params:
            model_data_to_save = {'params': estimated_params, 'team_map': team_mapping, 'num_teams': n_teams}
            with open(model_file_path, 'wb') as f:
                pickle.dump(model_data_to_save, f)

            # Clear this league from cache if it exists, so the new model is loaded next time
            if league_name in _model_cache:
                del _model_cache[league_name]

            msg = f"Model for {league_name} trained and saved successfully."
            logging.info(msg)
            return {"status": "success", "message": msg, "model_path": str(model_file_path)}
        else:
            raise RuntimeError(f"Model fitting failed for {league_name}.")

    except (DataNotFoundError, ValueError, RuntimeError) as e:
        logging.error(f"Training failed for {league_name}: {e}")
        raise e


def load_model_for_league(league_name: str) -> Tuple[Dict, Dict, int]:
    """Loads a model from file, using an in-memory cache."""
    # 1. Check cache first
    if league_name in _model_cache:
        logging.info(f"Loading model for '{league_name}' from cache.")
        return _model_cache[league_name]

    # 2. If not in cache, load from disk
    model_file_path = get_model_file_path(league_name)
    if not model_file_path.exists():
        raise ModelNotFoundError(f"No pre-trained model found for league '{league_name}'. Please train it first.")

    logging.info(f"Loading model for '{league_name}' from disk: {model_file_path}")
    try:
        with open(model_file_path, 'rb') as f:
            saved_data = pickle.load(f)

        params = saved_data['params']
        team_map = saved_data['team_map']
        num_teams = saved_data['num_teams']

        # 3. Store in cache for future requests
        _model_cache[league_name] = (params, team_map, num_teams)

        return params, team_map, num_teams
    except Exception as e:
        logging.error(f"Failed to load or parse model file for {league_name}. Error: {e}")
        raise ModelNotFoundError(f"Could not load model for {league_name}.")


def get_prediction(league_name: str, home_team: str, away_team: str) -> Dict:
    """API-facing function to get a match prediction."""
    estimated_params, team_mapping, _ = load_model_for_league(league_name)
    prediction = predict_match(home_team, away_team, estimated_params, team_mapping)
    return prediction


def get_teams_for_league(league_name: str) -> List[str]:
    """Returns a sorted list of teams for a given league model."""
    _, team_mapping, _ = load_model_for_league(league_name)
    return sorted(list(team_mapping.keys()))


def list_available_models() -> List[str]:
    """Scans the models directory and returns a list of available leagues."""
    leagues = []
    for f in MODEL_DIR.glob("*.pkl"):
        # Extract league name from filename like 'dixon_coles_serie_a_model.pkl'
        match = re.search(r'dixon_coles_(.*?)_model.pkl', f.name)
        if match:
            leagues.append(match.group(1).replace("_", " "))  # Make it more readable
    return sorted(leagues)

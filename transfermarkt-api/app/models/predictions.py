from pydantic import BaseModel, Field
from typing import List

class TrainRequest(BaseModel):
    league_name: str = Field(..., example="serie_a", description="The identifier for the league (must match a folder in `/app/data/leagues`).")
    force_refit: bool = Field(False, description="If true, retrains the model even if a saved file exists.")

class TrainResponse(BaseModel):
    status: str
    message: str
    model_path: str = None

class PredictionRequest(BaseModel):
    league_name: str = Field(..., example="serie_a")
    home_team: str = Field(..., example="Inter")
    away_team: str = Field(..., example="Juventus")

class Probabilities1x2(BaseModel):
    home_win: float
    draw: float
    away_win: float

class GoalPredictions(BaseModel):
    most_likely_score: str
    most_likely_score_prob: float
    over_2_5_prob: float
    under_2_5_prob: float
    btts_yes_prob: float
    btts_no_prob: float

class PredictionResponse(BaseModel):
    lambda_home: float = Field(..., description="Expected goals for the home team (λ).")
    lambda_away: float = Field(..., description="Expected goals for the away team (μ).")
    probabilities_1x2: Probabilities1x2
    goal_predictions: GoalPredictions

class TeamListResponse(BaseModel):
    league: str
    teams: List[str]
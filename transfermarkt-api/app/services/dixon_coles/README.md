# Dixon-Coles Model Service

This service provides a clean interface to the Dixon-Coles statistical model for football match predictions.

## 🚀 Features

- **Automatic Path Resolution**: Automatically finds the stats-soccer directory
- **Model Caching**: Caches loaded models and team mappings for performance
- **Comprehensive Error Handling**: Graceful fallbacks and detailed error messages
- **Multiple Import Paths**: Tries several possible locations for the stats-soccer directory

## 📁 Structure

```
app/services/dixon_coles/
├── __init__.py           # Package initialization
├── model_service.py      # Main service class
├── test_service.py       # Test script
└── README.md            # This file
```

## 🔧 Usage

### Basic Usage

```python
from app.services.dixon_coles.model_service import DixonColesModelService

# Initialize the service
service = DixonColesModelService()

# Check if model is available
if service.is_available():
    # Get available leagues
    leagues = service.get_available_leagues()
    
    # Make a prediction
    prediction = service.predict_match("Inter", "Milan", "serie_a")
    
    # Get service status
    status = service.get_status()
```

### Service Methods

#### `is_available() -> bool`
Check if the Dixon-Coles model is available.

#### `get_available_leagues() -> List[str]`
Get list of all available leagues.

#### `get_league_info(league_name: str) -> Optional[Dict]`
Get detailed information about a specific league.

#### `get_available_teams(league_name: str) -> List[str]`
Get list of available teams for a league.

#### `predict_match(home_team: str, away_team: str, league: str) -> Optional[Dict]`
Predict match outcome for a single match.

#### `predict_multiple_matches(league: str, matches: List[Dict]) -> Dict`
Predict multiple matches at once.

#### `get_status() -> Dict`
Get current service status and statistics.

#### `clear_cache() -> None`
Clear the model and team caches.

## 🛠️ Path Resolution

The service automatically tries to find the stats-soccer directory in the following order:

1. **Relative to service file**: `app/services/dixon_coles -> app/services -> app -> transfermarkt-api -> stats-soccer`
2. **Current working directory**: `./stats-soccer`
3. **Parent of transfermarkt-api**: `../stats-soccer`
4. **Root directory**: `./stats-soccer` (if running from Saas-betting-analysis)

## 📊 Caching

The service implements intelligent caching:

- **Model Cache**: Loaded models are cached to avoid repeated loading
- **Team Cache**: Team mappings are cached for quick access
- **Automatic Cache Management**: Caches are automatically populated as needed

## 🧪 Testing

Test the service using the provided test script:

```bash
cd transfermarkt-api
python app/services/dixon_coles/test_service.py
```

## 🔍 Debugging

Use the `/debug` endpoint to troubleshoot import path issues:

```bash
curl "http://localhost:9000/api/predictions/debug"
```

This will show:
- All attempted import paths
- Which paths exist
- Current Python path
- Service status

## 🚨 Error Handling

The service provides comprehensive error handling:

- **Import Errors**: Graceful fallback if stats-soccer is not found
- **Model Errors**: Clear error messages for corrupted or missing models
- **Team Errors**: Validation that teams exist in specified leagues
- **Path Errors**: Multiple fallback paths for directory resolution

## 💡 Best Practices

1. **Initialize Once**: Create the service once and reuse it
2. **Check Availability**: Always check `is_available()` before using
3. **Handle Errors**: Wrap calls in try-catch blocks
4. **Clear Cache**: Use `clear_cache()` if you need fresh models
5. **Monitor Status**: Use `get_status()` for debugging and monitoring

## 🔮 Future Enhancements

- **Async Support**: Make prediction methods async for better performance
- **Model Validation**: Add validation for model parameters
- **Performance Metrics**: Track prediction speed and accuracy
- **Configuration**: Allow custom path configuration
- **Model Updates**: Support for real-time model updates


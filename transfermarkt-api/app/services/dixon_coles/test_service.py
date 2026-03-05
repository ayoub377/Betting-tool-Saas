#!/usr/bin/env python3
"""
Test script for the Dixon-Coles Model Service
"""

import sys
from pathlib import Path

# Add the app directory to Python path
app_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(app_path))

from app.services.dixon_coles.model_service import DixonColesModelService

def test_service():
    """Test the Dixon-Coles service"""
    print("🧪 Testing Dixon-Coles Model Service")
    print("=" * 50)
    
    # Initialize the service
    service = DixonColesModelService()
    
    # Check if model is available
    print(f"✅ Model available: {service.is_available()}")
    
    if not service.is_available():
        print("❌ Model not available. Check the logs above for details.")
        return
    
    # Get status
    status = service.get_status()
    print(f"📊 Status: {status['status']}")
    print(f"🏆 Available leagues: {status['available_leagues']}")
    
    if not status['available_leagues']:
        print("⚠️  No leagues available")
        return
    
    # Test with first available league
    league = status['available_leagues'][0]
    print(f"\n🎯 Testing with league: {league}")
    
    # Get league info
    league_info = service.get_league_info(league)
    if league_info:
        print(f"📋 League info: {league_info['model_status']}")
        print(f"👥 Teams: {len(league_info['available_teams'])}")
        
        if league_info['available_teams']:
            teams = league_info['available_teams']
            if len(teams) >= 2:
                home_team = teams[0]
                away_team = teams[1]
                
                print(f"\n⚽ Testing prediction: {home_team} vs {away_team}")
                
                # Make prediction
                prediction = service.predict_match(home_team, away_team, league)
                
                if prediction:
                    print("✅ Prediction successful!")
                    
                    # Show prediction details
                    probs = prediction.get("probabilities_1x2", {})
                    print(f"📊 Match Outcome Probabilities:")
                    print(f"   🏠 Home Win: {probs.get('home_win', 'N/A'):.1%}" if probs.get('home_win') else "   🏠 Home Win: N/A")
                    print(f"   🤝 Draw: {probs.get('draw', 'N/A'):.1%}" if probs.get('draw') else "   🤝 Draw: N/A")
                    print(f"   ✈️  Away Win: {probs.get('away_win', 'N/A'):.1%}" if probs.get('away_win') else "   ✈️  Away Win: N/A")
                    
                    goals = prediction.get("goal_predictions", {})
                    print(f"\n⚽ Goal Predictions:")
                    print(f"   🎯 Most Likely Score: {goals.get('most_likely_score', 'N/A')}")
                    print(f"   📈 Over 2.5 Goals: {goals.get('over_2_5_prob', 'N/A'):.1%}" if goals.get('over_2_5_prob') else "   📈 Over 2.5 Goals: N/A")
                    print(f"   🔥 Both Teams to Score: {goals.get('btts_yes_prob', 'N/A'):.1%}" if goals.get('btts_yes_prob') else "   🔥 Both Teams to Score: N/A")
                    
                    model_info = prediction.get("model_info", {})
                    print(f"\n🔧 Model Information:")
                    print(f"   🏆 Total Teams: {model_info.get('total_teams', 'N/A')}")
                    print(f"   🏠 Home Advantage: {model_info.get('home_advantage', 'N/A')}")
                else:
                    print("❌ Prediction failed")
            else:
                print("⚠️  Not enough teams for prediction")
        else:
            print("⚠️  No teams available")
    else:
        print(f"❌ Failed to get league info for {league}")
    
    print("\n" + "=" * 50)
    print("🎉 Service test completed!")

if __name__ == "__main__":
    test_service()

from scipy.stats import poisson


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

    xG_home = (home_attack / league_avg_home_goals) * (away_defense / league_avg_away_goals)
    xG_away = (away_attack / league_avg_away_goals) * (home_defense / league_avg_home_goals)
    return xG_home, xG_away


def simulate_match_poisson(home_goals_exp, away_goals_exp, max_goals=10):
    probabilities = {'home_win': 0.0, 'draw': 0.0, 'away_win': 0.0}

    for home_goals in range(max_goals):
        for away_goals in range(max_goals):
            p_home = poisson.pmf(home_goals, home_goals_exp)
            p_away = poisson.pmf(away_goals, away_goals_exp)
            prob = p_home * p_away

            if home_goals > away_goals:
                probabilities['home_win'] += prob
            elif home_goals == away_goals:
                probabilities['draw'] += prob
            else:
                probabilities['away_win'] += prob

    return probabilities


def adjust_with_ppi(probabilities, home_ppi, away_ppi):
    ppi_ratio = home_ppi / (home_ppi + away_ppi)

    # Soft influence from PPI ratio (range: ~0.9 to 1.1 multiplier)
    home_adj = 1 + (ppi_ratio - 0.5) * 0.2
    away_adj = 1 - (ppi_ratio - 0.5) * 0.2

    probabilities['home_win'] *= home_adj
    probabilities['away_win'] *= away_adj

    # Normalize to ensure total = 1
    total = sum(probabilities.values())
    for key in probabilities:
        probabilities[key] /= total

    return probabilities


import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


def plot_goal_distribution_matrix(home_exp, away_exp, max_goals=5):
    matrix = np.zeros((max_goals + 1, max_goals + 1))

    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            p = poisson.pmf(home_goals, home_exp) * poisson.pmf(away_goals, away_exp)
            matrix[home_goals][away_goals] = p

    plt.figure(figsize=(8, 6))
    sns.heatmap(matrix, annot=True, fmt=".2%", cmap="Blues", cbar=True,
                xticklabels=[str(i) for i in range(max_goals + 1)],
                yticklabels=[str(i) for i in range(max_goals + 1)])
    plt.xlabel("Away Team Goals")
    plt.ylabel("Home Team Goals")
    plt.title("Goal Distribution Probability Matrix")
    plt.show()


def calculate_over_under_probabilities(home_exp, away_exp):
    total_probs = {}
    max_goals = 10

    # Compute probability of total goals for each sum
    goal_probs = [0.0] * (2 * max_goals)
    for home_goals in range(max_goals):
        for away_goals in range(max_goals):
            total_goals = home_goals + away_goals
            prob = poisson.pmf(home_goals, home_exp) * poisson.pmf(away_goals, away_exp)
            goal_probs[total_goals] += prob

    # Cumulative probabilities for under thresholds
    total = 0
    for i, prob in enumerate(goal_probs):
        total += prob
        total_probs[i] = total

    return {
        'under_1.5': total_probs.get(1, 0.0),
        'over_1.5': 1 - total_probs.get(1, 0.0),
        'under_2.5': total_probs.get(2, 0.0),
        'over_2.5': 1 - total_probs.get(2, 0.0),
        'under_3.5': total_probs.get(3, 0.0),
        'over_3.5': 1 - total_probs.get(3, 0.0),
    }


def calculate_ev(probability, odds):
    return (probability * (odds - 1)) - (1 - probability)


def kelly_bet(prob, odds, bankroll, fraction=0.8):
    edge = (odds * prob) - 1
    denom = odds - 1
    if denom == 0:
        return 0
    kelly_fraction = edge / denom
    kelly_fraction = max(0, kelly_fraction)  # No negative bets
    return bankroll * kelly_fraction * fraction


def run_match_prediction():
    print("=== Soccer Match Outcome Predictor ===")

    # xG estimation
    xG_home, xG_away = estimate_xg_from_user()

    # Adjust for home advantage
    home_adv_ppg_diff = float(input("PPG Difference (Home Advantage): "))
    xG_home += home_adv_ppg_diff * 1.1  # Tweak factor if needed

    # Adjust for relative form
    home_form_pct = float(input("Home Form Change (%): ")) / 100
    away_form_pct = float(input("Away Form Change (%): ")) / 100
    xG_home *= (1 + home_form_pct)
    xG_away *= (1 + away_form_pct)

    print(f"\n🔢 Adjusted xG — Home: {xG_home:.2f}, Away: {xG_away:.2f}")
    plot_goal_distribution_matrix(xG_home, xG_away)

    # Simulate base probabilities
    result_probs = simulate_match_poisson(xG_home, xG_away)

    # PPI adjustment
    home_ppi = float(input("Home team PPI (e.g. 1.2): "))
    away_ppi = float(input("Away team PPI (e.g. 0.9): "))
    final_probs = adjust_with_ppi(result_probs, home_ppi, away_ppi)

    # Output
    print("\n--- Final Match Outcome Probabilities ---")
    print(f"🏠 Home Win Probability: {final_probs['home_win']:.2%}")
    print(f"🤝 Draw Probability:     {final_probs['draw']:.2%}")
    print(f"🛫 Away Win Probability: {final_probs['away_win']:.2%}")
    while True:
        choice = input("\nDo you want to analyze another match? (yes/no): ").strip().lower()
        if choice != "yes":
            print("👋 Exiting... Good luck with your bets!")
            break
        print("\n=== Optional: Add Betting Odds to Calculate EV & Kelly ===")
        bankroll = float(input("Enter your bankroll (dhs): "))

        # Odds input
        odds = {
            'home_win': float(input("Odds for Home Win: ")),
            'draw': float(input("Odds for Draw: ")),
            'away_win': float(input("Odds for Away Win: ")),
            'over_1.5': float(input("Odds for Over 1.5 goals: ")),
            'under_1.5': float(input("Odds for Under 1.5 goals: ")),
            'over_2.5': float(input("Odds for Over 2.5 goals: ")),
            'under_2.5': float(input("Odds for Under 2.5 goals: ")),
            'over_3.5': float(input("Odds for Over 3.5 goals: ")),
            'under_3.5': float(input("Odds for Under 3.5 goals: "))
        }

        # Total goals probabilities
        goal_line_probs = calculate_over_under_probabilities(xG_home, xG_away)

        all_probs = {**final_probs, **goal_line_probs}

        print("\n--- EV and Kelly Criterion ---")
        for bet, prob in all_probs.items():
            ev = calculate_ev(prob, odds[bet])
            stake = kelly_bet(prob, odds[bet], bankroll, fraction=0.8)
            sign = "✅" if ev > 0 else "❌"
            print(f"{bet:>12}: Prob={prob:.2%}, Odds={odds[bet]}, EV={ev:.2f} {sign} | Bet €{stake:.2f}")


# Run it
run_match_prediction()

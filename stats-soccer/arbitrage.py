def calculate_equal_profit_arb(odds_draw, odds_home, total_stake):
    """
    Calculates equal-profit stakes for two outcomes:
      - Draw at odds_draw
      - Home win at odds_home
    given a total amount to bet (total_stake).
    """

    # Solve stake_draw + stake_home = total_stake
    # and stake_draw*odds_draw = stake_home*odds_home for equal returns
    stake_draw = total_stake * odds_home / (odds_draw + odds_home)
    stake_home = total_stake - stake_draw

    # Compute returns and profits
    return_draw = stake_draw * odds_draw
    return_home = stake_home * odds_home
    guaranteed_return = return_draw  # == return_home
    profit = guaranteed_return - total_stake
    loss_if_away = -total_stake

    # Display results
    print("\n=== Equal-Profit Arbitrage Calculator ===")
    print(f"Draw odds = {odds_draw}, Home odds = {odds_home}, Total stake = {total_stake}")
    print(f"\nStake on Draw  @ {odds_draw}: {stake_draw:.2f}")
    print(f"Stake on Home  @ {odds_home}: {stake_home:.2f}")

    print(f"\nIf Draw:  Return = {return_draw:.2f}, Profit = {profit:.2f}")
    print(f"If Home:  Return = {return_home:.2f}, Profit = {profit:.2f}")
    print(f"If Away:  Profit = {loss_if_away:.2f}   (full loss of stake)")

    if profit > 0:
        print(f"\n✅ This is a true arbitrage: you lock in a profit of {profit:.2f}.")
    else:
        print(f"\n⚠️  No true arbitrage: you’ll still lose {-profit:.2f} if Draw/Home occurs.")


if __name__ == "__main__":
    try:
        odds_draw = float(input("Enter Draw odds (e.g. 2.25): "))
        odds_home = float(input("Enter Home-win odds (e.g. 3.53): "))
        total_stake = float(input("Enter your total stake (e.g. 100): "))
    except ValueError:
        print("Invalid input. Please enter numeric values.")
        exit(1)

    calculate_equal_profit_arb(odds_draw, odds_home, total_stake)

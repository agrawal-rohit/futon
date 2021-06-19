def percent_change(d1, d2):
    return (d2 - d1) / d1


def profit(initial_capital, multiplier):
    return initial_capital * (multiplier + 1.0) - initial_capital

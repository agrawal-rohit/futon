def percent_change(d1, d2):
    """
    Calculate percent change between two values

    Parameters
    ----------
    d1 : float or int
        Base value
    d2 : float or int
        Target value

    Returns
    -------
    float
        Percent change between the provided values
    """
    return (d2 - d1) / d1


def profit(initial_capital, multiplier):
    """
    Return profit based on a multiplier

    Parameters
    ----------
    initial_capital : float or int
        Base value
    multiplier : float or int
        Multiplier value for the final value

    Returns
    -------
    float
        Calculated profit based on the multiplier
    """
    return initial_capital * (multiplier + 1.0) - initial_capital

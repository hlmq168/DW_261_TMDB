
from .decision.decision_engine import run_investment_analysis


def analyze_investment(
    budget,
    genres=None,
    objective="BALANCED",
    min_votes=100,
    top_n=20
):
    """
    Public service interface for the investment DSS.

    Parameters
    ----------
    budget : float
        Maximum investment budget.
    genres : str or list, optional
        Target movie genres.
    objective : str
        Investment objective:
        BALANCED, HIGH_ROI, HIGH_PROFIT, POPULARITY, LOW_RISK.
    min_votes : int
        Minimum number of votes.
    top_n : int
        Number of top investment candidates to return.

    Returns
    -------
    dict
        Investment analysis results.
    """

    if budget is None or budget <= 0:
        raise ValueError("Budget must be greater than zero.")

    return run_investment_analysis(
        budget=budget,
        genres=genres,
        objective=objective,
        min_votes=min_votes,
        top_n=top_n
    )

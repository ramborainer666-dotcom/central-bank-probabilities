"""Independent meeting-rate inference from licensed, user-supplied futures quotations.

Rates in percent (4.85 means 4.85%, not decimal 0.0485).
For arithmetic-average contracts (ASX cash-rate, CME fed funds), a meeting
inside a month splits the future's monthly arithmetic average into pre- and
post-meeting segments. CORRA COA instead compounds daily; use the exact
compounded solver below. Does not access any external website.

CME-style binary probabilities are a *model*, not an observable market
distribution. Outputs above 100% are not silently clipped or mislabeled.
"""
from __future__ import annotations
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite
from typing import Literal

class InferenceError(ValueError):
    pass

def rate_from_futures_price(price: float) -> float:
    if not isfinite(price) or not 50 < price <= 101:
        raise InferenceError("Futures price must be in plausible 100-minus-rate units")
    return 100.0 - price

def month_dates(year: int, month: int) -> tuple[date, date]:
    if not (1 <= month <= 12):
        raise InferenceError("Invalid month")
    start=date(year,month,1)
    end=start+timedelta(days=monthrange(year,month)[1])
    return start,end

def validate_single_meeting(start: date, end: date, meeting_effective: date) -> tuple[int,int]:
    if not(start < meeting_effective < end):
        raise InferenceError("Meeting effective date must be strictly inside contract period")
    before=(meeting_effective-start).days
    after=(end-meeting_effective).days
    return before,after

def arithmetic_after_rate(
    futures_price: float, start: date, end: date,
    meeting_effective: date, pre_reference_rate_pct: float,
) -> float:
    """Post-meeting expected reference rate; day-weighted arithmetic average."""
    before,after=validate_single_meeting(start,end,meeting_effective)
    implied=rate_from_futures_price(futures_price)
    return ((before+after)*implied-before*pre_reference_rate_pct)/after

def daily_compounded_annualized_rate(rates_pct: list[float], day_counts: list[int]) -> float:
    """COA-style compounded overnight rate. 365-day denominator.

    Rates are assigned to calendar-day blocks (including weekend carry).
    Actual CORRA fixing calendars must be supplied by an authorized source.
    """
    if not rates_pct or len(rates_pct)!=len(day_counts) or any(n<=0 for n in day_counts):
        raise InferenceError("Provide nonempty daily fixing blocks with positive day counts")
    days=sum(day_counts)
    product=1.0
    for rate,n in zip(rates_pct,day_counts):
        if not isfinite(rate) or rate < -10 or rate > 50:
            raise InferenceError("Invalid reference rate")
        product*=1.0+(rate/100.0)*n/365.0
    return (product-1.0)*365.0/days*100.0

def compounded_after_rate(
    futures_price: float, start: date, end: date,
    meeting_effective: date, pre_reference_rate_pct: float,
) -> float:
    """Two-block compounding approximation for COA futures.

    This is exact only if pre/post overnight rates are constant for each
    segment and fixing-day carry matches these calendar-day blocks.
    """
    before,after=validate_single_meeting(start,end,meeting_effective)
    target=rate_from_futures_price(futures_price)
    term=1.0+target/100.0*(before+after)/365.0
    pre=1.0+pre_reference_rate_pct/100.0*before/365.0
    if pre<=0:
        raise InferenceError("Invalid pre-meeting compound factor")
    return ((term/pre)-1.0)*365.0/after*100.0

@dataclass(frozen=True)
class MeetingInference:
    implied_pre_rate_pct: float
    implied_post_rate_pct: float
    expected_move_bps: float
    hike_pct: float | None
    hold_pct: float | None
    cut_pct: float | None
    model: str
    notes: str

def binary_outcomes(move_bps: float, step_bps: float=25.0) -> tuple[float,float,float] | None:
    """Only zero-or-one-step outcomes. Return None outside identified range."""
    if not isfinite(move_bps) or step_bps<=0:
        raise InferenceError("Invalid expected move or step")
    if abs(move_bps)>step_bps+1e-7:
        return None
    p=min(abs(move_bps)/step_bps,1.0)*100
    if move_bps>1e-7:
        return (p,100-p,0.0)
    if move_bps < -1e-7:
        return (0.0,100-p,p)
    return (0.0,100.0,0.0)

def infer_meeting(
    *, future_price: float, year: int, month: int,
    meeting_effective: date, current_policy_rate_pct: float,
    current_reference_rate_pct: float,
    contract: Literal["arithmetic", "corra_compounded"],
    step_bps: float=25.0,
) -> MeetingInference:
    start,end=month_dates(year,month)
    if contract=="arithmetic":
        after=arithmetic_after_rate(future_price,start,end,meeting_effective,current_reference_rate_pct)
    elif contract=="corra_compounded":
        after=compounded_after_rate(future_price,start,end,meeting_effective,current_reference_rate_pct)
    else:
        raise InferenceError("Unsupported contract")
    # Assume benchmark-policy spread remains constant across meeting.
    spread=current_reference_rate_pct-current_policy_rate_pct
    post_policy=after-spread
    move=(post_policy-current_policy_rate_pct)*100
    probs=binary_outcomes(move,step_bps)
    note=("One meeting inside the contract; constant policy-reference spread; "
          "binary Hold vs one +/- step assumption only. Compounded CORRA "
          "uses two constant overnight-rate blocks, not an exact settlement-calendar engine."
          if contract=="corra_compounded" else
          "One meeting inside the contract; constant policy-reference spread; "
          "arithmetic monthly-average rate; binary Hold vs one +/- step assumption only.")
    return MeetingInference(current_policy_rate_pct,post_policy,move,
       *(probs if probs is not None else (None,None,None)),
       "binary_one_step" if probs is not None else "unidentified_multiple_steps",note)

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user
from app.models import User
from app.services.bnr import BNR_DAILY_URL, BnrRateError, get_rate, rate_public_dict

router = APIRouter(prefix="/fx", tags=["fx"])


@router.get("/bnr")
def bnr_rate(
    currency: str = Query(default="EUR", min_length=3, max_length=8),
    user: User = Depends(get_current_user),
) -> dict:
    _ = user
    code = currency.strip().upper()
    if code in {"RON", "LEI"}:
        return {
            "currency": "RON",
            "rate": 1.0,
            "rate_raw": 1.0,
            "multiplier": 1,
            "rate_date": None,
            "source": "RON",
            "source_label": "RON",
            "source_url": BNR_DAILY_URL,
        }
    try:
        rate = get_rate(code)
    except BnrRateError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return rate_public_dict(rate)

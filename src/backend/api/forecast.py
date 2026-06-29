"""GET /api/forecast — thin router; logic lives in services/forecast.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.forecast import ForecastHorizonSchema, ForecastResponse
from services import forecast as forecast_svc

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("", response_model=ForecastResponse)
def get_forecast(
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = forecast_svc.get_forecast(db)
    return ForecastResponse(
        cash_total=result.cash_total,
        loans_total=result.loans_total,
        net_funds=result.net_funds,
        avg_monthly_change=result.avg_monthly_change,
        months_of_data=result.months_of_data,
        data_warning=result.data_warning,
        horizons=[
            ForecastHorizonSchema(
                months=h.months,
                projected_net_funds=h.projected_net_funds,
                delta=h.delta,
            )
            for h in result.horizons
        ],
    )

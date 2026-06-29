from decimal import Decimal

from pydantic import BaseModel


class ForecastHorizonSchema(BaseModel):
    months: int
    projected_net_funds: Decimal
    delta: Decimal


class ForecastResponse(BaseModel):
    cash_total: Decimal
    loans_total: Decimal       # negative — signed sum of loan + credit balances
    net_funds: Decimal
    avg_monthly_change: Decimal
    months_of_data: int
    data_warning: bool
    horizons: list[ForecastHorizonSchema]  # empty when months_of_data == 0

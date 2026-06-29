export interface ForecastHorizon {
  months: number;
  projected_net_funds: string;  // Decimal as string; may be negative
  delta: string;                // signed — negative when declining
}

export interface ForecastData {
  cash_total: string;
  loans_total: string;          // negative string
  net_funds: string;
  avg_monthly_change: string;
  months_of_data: number;
  data_warning: boolean;
  horizons: ForecastHorizon[];  // empty array when months_of_data === 0
}

export async function getForecast(): Promise<ForecastData> {
  const res = await fetch('/api/forecast');
  if (!res.ok) throw new Error('Failed to load forecast');
  return res.json();
}

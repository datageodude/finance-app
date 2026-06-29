export interface LoanDetail {
  id: string;
  display_name: string;
  bank_code: string;
  balance_owing: string;        // positive decimal string — abs(current_balance)
  available_balance: string | null;
  original_principal: string;
  interest_rate: string;
  term_months: number;
  start_date: string | null;    // "YYYY-MM-DD"
  end_date: string | null;      // "YYYY-MM-DD"
  last_import_at: string | null;
}

export async function getLoans(): Promise<LoanDetail[]> {
  const res = await fetch('/api/loans');
  if (!res.ok) throw new Error('Failed to load loans');
  return res.json();
}

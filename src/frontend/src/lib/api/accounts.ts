export interface AccountSummary {
  id: string;
  display_name: string;
  bank_code: string;
  account_code: string;
  type: string;
}

export interface AccountBalance {
  id: string;
  display_name: string;
  bank_code: string;
  type: string;
  current_balance: string;
  available_balance: string | null;
  last_import_at: string | null;
}

export async function getAccounts(): Promise<AccountSummary[]> {
  const res = await fetch('/api/accounts');
  if (!res.ok) throw new Error('Failed to load accounts');
  return res.json();
}

export async function getAccountBalances(): Promise<AccountBalance[]> {
  const res = await fetch('/api/accounts/balances');
  if (!res.ok) throw new Error('Failed to load account balances');
  return res.json();
}

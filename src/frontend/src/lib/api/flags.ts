export interface FlagItem {
  flag_id: number;
  flag_type: string;
  reason: string;
  status: string;
  created_at: string;
  txn_id: string;
  txn_date: string;
  txn_amount: string;
  txn_description_raw: string;
  account_display_name: string;
  merchant_name: string | null;
  related_txn_id: string | null;
  related_txn_date: string | null;
  related_txn_amount: string | null;
}

export async function getFlags(): Promise<FlagItem[]> {
  const res = await fetch('/api/flags');
  if (!res.ok) throw new Error('Failed to load flags');
  return res.json();
}

export async function approveFlag(
  flagId: number,
  customThreshold?: number,
): Promise<{ flag_id: number; status: string }> {
  const res = await fetch(`/api/flags/${flagId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ custom_threshold: customThreshold ?? null }),
  });
  if (!res.ok) throw new Error('Failed to approve flag');
  return res.json();
}

export async function dismissFlag(
  flagId: number,
): Promise<{ flag_id: number; status: string }> {
  const res = await fetch(`/api/flags/${flagId}/dismiss`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to dismiss flag');
  return res.json();
}

export async function generateFlags(
  accountId: string,
): Promise<{ flags_created: number }> {
  const res = await fetch(`/api/flags/generate?account_id=${accountId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to generate flags');
  return res.json();
}

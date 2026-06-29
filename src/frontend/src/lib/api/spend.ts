export interface CategorySpendRow {
  category_id: number;
  name: string;
  actual: string;
  budget: string | null;
}

export interface SpendSummary {
  rows: CategorySpendRow[];
  uncategorised_actual: string;
  total_actual: string;
  total_budget: string | null;
  has_transactions: boolean;
}

export async function getSpendSummary(): Promise<SpendSummary> {
  const res = await fetch('/api/spend/summary');
  if (!res.ok) throw new Error('Failed to load spend summary');
  return res.json();
}

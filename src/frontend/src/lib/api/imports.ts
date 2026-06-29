export interface PreviewResult {
  account_id: string;
  account_display_name: string;
  bank_code: string;
  account_code: string;
  txn_date_min: string | null;
  txn_date_max: string | null;
  rows_found: number;
  rows_to_add: number;
  rows_duplicate: number;
  filename_seen_before: boolean;
  filename_seen_at: string | null;
}

export interface ImportResult {
  import_id: string;
  rows_added: number;
  rows_skipped: number;
  reconciliation_ok: boolean;
  drift: string;
}

export interface ImportHistoryItem {
  import_id: string;
  filename: string;
  account_display_name: string;
  rows_added: number;
  rows_skipped: number;
  created_at: string;
}

export interface ImportApiError {
  error: string;
  detail: string;
}

async function uploadFile(
  endpoint: string,
  file: File,
  accountId?: string,
): Promise<Response> {
  const form = new FormData();
  form.append('file', file);
  const url = accountId
    ? `/api/imports/${endpoint}?account_id=${accountId}`
    : `/api/imports/${endpoint}`;
  return fetch(url, { method: 'POST', body: form });
}

export async function previewImport(
  file: File,
  accountId?: string,
): Promise<PreviewResult> {
  const res = await uploadFile('preview', file, accountId);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const body = err as { detail?: ImportApiError };
    throw Object.assign(
      new Error(body.detail?.detail ?? 'Preview failed'),
      { errorCode: body.detail?.error ?? 'unknown' },
    );
  }
  return res.json();
}

export async function confirmImport(
  file: File,
  accountId?: string,
): Promise<ImportResult> {
  const res = await uploadFile('confirm', file, accountId);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const body = err as { detail?: ImportApiError };
    throw Object.assign(
      new Error(body.detail?.detail ?? 'Import failed'),
      { errorCode: body.detail?.error ?? 'unknown' },
    );
  }
  return res.json();
}

export async function getImportHistory(limit = 10): Promise<ImportHistoryItem[]> {
  const res = await fetch(`/api/imports/history?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to load import history');
  return res.json();
}

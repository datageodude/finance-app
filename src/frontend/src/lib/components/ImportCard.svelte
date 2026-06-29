<script lang="ts">
  import { onMount } from 'svelte';
  import { confirmImport, previewImport, type PreviewResult } from '$lib/api/imports';
  import { getAccounts, type AccountSummary } from '$lib/api/accounts';

  type CardState = 'loading' | 'preview' | 'needs_account' | 'confirming' | 'success' | 'error';

  let {
    file,
    confirmTrigger,
    onDismiss,
    onReady,
    onNotReady,
    onSuccess,
  }: {
    file: File;
    confirmTrigger: number;
    onDismiss: () => void;
    onReady: (info: { accountId: string; rowsToAdd: number }) => void;
    onNotReady: () => void;
    onSuccess: () => void;
  } = $props();

  let cardState = $state('loading' as CardState);
  let preview = $state(null as PreviewResult | null);
  let errorMsg = $state('');
  let accounts = $state([] as AccountSummary[]);
  let selectedAccountId = $state('');
  // Initialise to 0 — matches the parent's initial confirmTrigger value
  let prevTrigger = $state(0);

  async function runPreview(accountId?: string) {
    cardState = 'loading';
    try {
      preview = await previewImport(file, accountId);
      cardState = 'preview';
      onReady({ accountId: preview.account_id, rowsToAdd: preview.rows_to_add });
    } catch (err: unknown) {
      const e = err as Error & { errorCode?: string };
      if (e.errorCode === 'unknown_account') {
        try { accounts = await getAccounts(); } catch { accounts = []; }
        cardState = 'needs_account';
      } else {
        errorMsg = e.message;
        cardState = 'error';
      }
      onNotReady();
    }
  }

  async function doConfirm() {
    if (cardState !== 'preview' || !preview) return;
    cardState = 'confirming';
    try {
      await confirmImport(file, selectedAccountId || undefined);
      cardState = 'success';
      onSuccess();
    } catch (err: unknown) {
      const e = err as Error;
      errorMsg = e.message;
      cardState = 'error';
      onNotReady();
    }
  }

  // When parent increments confirmTrigger, confirm if in preview state
  $effect(() => {
    if (confirmTrigger !== prevTrigger) {
      prevTrigger = confirmTrigger;
      if (cardState === 'preview') doConfirm();
    }
  });

  onMount(() => { runPreview(); });

  function formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d + 'T00:00:00').toLocaleDateString('en-AU', {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  }
</script>

<div
  class="card"
  class:card-success={cardState === 'success'}
  class:card-error={cardState === 'error'}
>
  <div class="card-header">
    <span class="filename" title={file.name}>{file.name}</span>
    {#if cardState !== 'confirming' && cardState !== 'success'}
      <button class="dismiss-btn" onclick={onDismiss} aria-label="Remove">✕</button>
    {/if}
  </div>

  {#if cardState === 'loading' || cardState === 'confirming'}
    <div class="status-row">
      <span class="spinner" aria-busy="true"></span>
      <span class="status-text">{cardState === 'confirming' ? 'Importing…' : 'Checking file…'}</span>
    </div>

  {:else if cardState === 'preview' && preview}
    <div class="preview-body">
      <p class="account-name">{preview.account_display_name}</p>
      <div class="stat-row">
        <span class="stat"><strong>{preview.rows_found}</strong> rows found</span>
        <span class="stat new"><strong>{preview.rows_to_add}</strong> new</span>
        <span class="stat dup"><strong>{preview.rows_duplicate}</strong> duplicate{preview.rows_duplicate !== 1 ? 's' : ''}</span>
      </div>
      {#if preview.txn_date_min}
        <p class="date-range">{formatDate(preview.txn_date_min)} → {formatDate(preview.txn_date_max)}</p>
      {/if}
      {#if preview.filename_seen_before}
        <p class="warn">⚠ This filename was imported before{preview.filename_seen_at ? ` on ${new Date(preview.filename_seen_at).toLocaleDateString('en-AU')}` : ''}.</p>
      {/if}
      {#if preview.rows_to_add === 0}
        <p class="info">Nothing new to add — all rows are duplicates.</p>
      {/if}
    </div>

  {:else if cardState === 'needs_account'}
    <div class="needs-account-body">
      <p class="hint">Filename doesn't match an account. Pick one to continue:</p>
      <select bind:value={selectedAccountId} class="account-select">
        <option value="">— select account —</option>
        {#each accounts as acct}
          <option value={acct.id}>{acct.display_name}</option>
        {/each}
      </select>
      <button
        class="pick-btn"
        disabled={!selectedAccountId}
        onclick={() => runPreview(selectedAccountId)}
      >
        Continue
      </button>
    </div>

  {:else if cardState === 'success'}
    <div class="status-row">
      <span class="success-icon">✓</span>
      <span class="status-text">Imported successfully</span>
    </div>

  {:else if cardState === 'error'}
    <div class="error-body">
      <p class="error-msg">{errorMsg}</p>
    </div>
  {/if}
</div>

<style>
  .card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 12px 14px;
    transition: border-color 0.15s;
  }

  .card-success { border-color: #16a34a; }
  .card-error   { border-color: #dc2626; }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .filename {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: calc(100% - 28px);
  }

  .dismiss-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: #9ca3af;
    font-size: 14px;
    padding: 0 2px;
    line-height: 1;
    flex-shrink: 0;
  }

  .status-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
  }

  .status-text {
    font-size: 13px;
    color: #6b7280;
  }

  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid #e5e7eb;
    border-top-color: #2563eb;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .success-icon {
    color: #16a34a;
    font-size: 16px;
    font-weight: 700;
  }

  .preview-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .account-name {
    font-size: 14px;
    font-weight: 600;
    color: #111827;
    margin: 0;
  }

  .stat-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .stat {
    font-size: 13px;
    color: #6b7280;
  }

  .stat.new strong { color: #16a34a; }
  .stat.dup strong { color: #9ca3af; }

  .date-range {
    font-size: 12px;
    color: #9ca3af;
    margin: 0;
  }

  .warn {
    font-size: 12px;
    color: #d97706;
    margin: 0;
  }

  .info {
    font-size: 12px;
    color: #9ca3af;
    margin: 0;
  }

  .needs-account-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .hint {
    font-size: 13px;
    color: #6b7280;
    margin: 0;
  }

  .account-select {
    font-size: 14px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 8px;
    background: #fff;
    color: #111827;
    width: 100%;
  }

  .pick-btn {
    align-self: flex-start;
    padding: 6px 14px;
    font-size: 14px;
    font-weight: 600;
    color: #fff;
    background: #2563eb;
    border: none;
    border-radius: 6px;
    cursor: pointer;
  }

  .pick-btn:disabled {
    background: #93c5fd;
    cursor: default;
  }

  .error-body { padding: 2px 0; }

  .error-msg {
    font-size: 13px;
    color: #dc2626;
    margin: 0;
  }
</style>

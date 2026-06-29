<script lang="ts">
  import { approveFlag, dismissFlag, type FlagItem } from '$lib/api/flags';

  const FLAG_TYPE_LABELS: Record<string, string> = {
    over_threshold: 'Over Threshold',
    double_charge: 'Possible Double Charge',
    new_merchant: 'New Merchant',
    recurring_change: 'Change in Regular Payment',
  };

  let {
    flag,
    onResolve,
  }: {
    flag: FlagItem;
    onResolve: () => void;
  } = $props();

  let resolving = $state(false);
  let showThresholdInput = $state(false);
  let customThreshold = $state('');
  let errorMsg = $state('');

  const formattedAmount = $derived(
    new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(
      Math.abs(parseFloat(flag.txn_amount)),
    ),
  );

  const formattedDate = $derived(
    new Date(flag.txn_date).toLocaleDateString('en-AU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }),
  );

  async function handleApprove() {
    if (flag.flag_type === 'over_threshold' && !showThresholdInput) {
      showThresholdInput = true;
      return;
    }
    resolving = true;
    errorMsg = '';
    try {
      const threshold = customThreshold ? parseFloat(customThreshold) : undefined;
      await approveFlag(flag.flag_id, threshold);
      onResolve();
    } catch {
      errorMsg = 'Failed to approve — try again.';
      resolving = false;
    }
  }

  async function handleDismiss() {
    resolving = true;
    errorMsg = '';
    try {
      await dismissFlag(flag.flag_id);
      onResolve();
    } catch {
      errorMsg = 'Failed to dismiss — try again.';
      resolving = false;
    }
  }

  function skipThreshold() {
    customThreshold = '';
    handleApprove();
  }
</script>

<div class="flag-card">
  <div class="flag-header">
    <span class="flag-type-badge flag-type-{flag.flag_type}">
      {FLAG_TYPE_LABELS[flag.flag_type] ?? flag.flag_type}
    </span>
    <span class="flag-date">{formattedDate}</span>
  </div>

  <div class="flag-body">
    <div class="txn-row">
      <span class="txn-desc">{flag.txn_description_raw}</span>
      <span class="txn-amount">{formattedAmount}</span>
    </div>
    <div class="txn-account">{flag.account_display_name}</div>
    {#if flag.merchant_name}
      <div class="txn-merchant">{flag.merchant_name}</div>
    {/if}
    <p class="flag-reason">{flag.reason}</p>

    {#if flag.related_txn_id}
      <div class="related-txn">
        Earlier charge: {new Date(flag.related_txn_date!).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}
        — {new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(Math.abs(parseFloat(flag.related_txn_amount!)))}
      </div>
    {/if}
  </div>

  {#if showThresholdInput}
    <div class="threshold-prompt">
      <label for="threshold-{flag.flag_id}">Set custom threshold for {flag.merchant_name ?? 'this merchant'} (optional)</label>
      <div class="threshold-row">
        <span class="dollar-sign">$</span>
        <input
          id="threshold-{flag.flag_id}"
          type="number"
          min="0"
          step="10"
          placeholder="e.g. 3000"
          bind:value={customThreshold}
          disabled={resolving}
        />
      </div>
      <div class="threshold-actions">
        <button class="btn-approve" onclick={handleApprove} disabled={resolving}>
          {customThreshold ? 'Save & Approve' : 'Approve'}
        </button>
        <button class="btn-skip" onclick={skipThreshold} disabled={resolving}>
          Skip — approve without threshold
        </button>
      </div>
    </div>
  {:else}
    <div class="flag-actions">
      <button class="btn-approve" onclick={handleApprove} disabled={resolving}>
        {resolving ? 'Saving…' : 'Approve'}
      </button>
      <button class="btn-dismiss" onclick={handleDismiss} disabled={resolving}>
        {resolving ? '…' : 'Dismiss'}
      </button>
    </div>
  {/if}

  {#if errorMsg}
    <p class="error-msg">{errorMsg}</p>
  {/if}
</div>

<style>
  .flag-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .flag-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .flag-type-badge {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 3px 8px;
    border-radius: 999px;
  }

  .flag-type-over_threshold { background: #fef3c7; color: #92400e; }
  .flag-type-double_charge  { background: #fee2e2; color: #991b1b; }
  .flag-type-new_merchant   { background: #ede9fe; color: #5b21b6; }
  .flag-type-recurring_change { background: #dbeafe; color: #1e40af; }

  .flag-date { font-size: 12px; color: #9ca3af; }

  .txn-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
  }

  .txn-desc {
    font-size: 14px;
    font-weight: 500;
    color: #111827;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .txn-amount {
    font-size: 16px;
    font-weight: 700;
    color: #dc2626;
    white-space: nowrap;
  }

  .txn-account, .txn-merchant {
    font-size: 12px;
    color: #6b7280;
  }

  .flag-reason {
    font-size: 13px;
    color: #374151;
    margin: 0;
    font-style: italic;
  }

  .related-txn {
    font-size: 12px;
    color: #6b7280;
    background: #f9fafb;
    border-radius: 6px;
    padding: 6px 10px;
  }

  .flag-actions {
    display: flex;
    gap: 8px;
  }

  .threshold-prompt {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .threshold-prompt label {
    font-size: 13px;
    color: #374151;
  }

  .threshold-row {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .dollar-sign {
    font-size: 14px;
    color: #6b7280;
  }

  .threshold-row input {
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
    width: 120px;
  }

  .threshold-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .btn-approve {
    background: #16a34a;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-approve:disabled { opacity: 0.6; cursor: not-allowed; }

  .btn-dismiss {
    background: #f3f4f6;
    color: #374151;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    cursor: pointer;
  }

  .btn-dismiss:disabled { opacity: 0.6; cursor: not-allowed; }

  .btn-skip {
    background: none;
    border: none;
    color: #6b7280;
    font-size: 12px;
    cursor: pointer;
    padding: 0;
    text-decoration: underline;
  }

  .btn-skip:disabled { opacity: 0.6; cursor: not-allowed; }

  .error-msg {
    font-size: 12px;
    color: #dc2626;
    margin: 0;
  }
</style>

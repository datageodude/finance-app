<script lang="ts">
  import { onMount } from 'svelte';
  import { getAccountBalances, type AccountBalance } from '$lib/api/accounts';

  const STORAGE_KEY = 'cash-show-loans';
  const TYPE_ORDER = ['savings', 'transaction', 'loan'];
  const TYPE_LABELS: Record<string, string> = {
    savings: 'Savings',
    transaction: 'Transaction',
    loan: 'Loans',
  };

  let accounts = $state<AccountBalance[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let showLoans = $state(false);

  onMount(async () => {
    showLoans = localStorage.getItem(STORAGE_KEY) === 'true';
    try {
      accounts = await getAccountBalances();
    } catch {
      error = 'Failed to load account balances.';
    } finally {
      loading = false;
    }
  });

  function toggleLoans() {
    showLoans = !showLoans;
    localStorage.setItem(STORAGE_KEY, String(showLoans));
  }

  const cashAccounts = $derived(accounts.filter(a => a.type !== 'loan'));
  const loanAccounts = $derived(accounts.filter(a => a.type === 'loan'));
  const hasLoans = $derived(loanAccounts.length > 0);

  const cashTotal = $derived(
    cashAccounts.reduce((sum, a) => sum + parseFloat(a.current_balance), 0)
  );

  const loanRedrawTotal = $derived(
    loanAccounts.reduce(
      (sum, a) => sum + (a.available_balance != null ? parseFloat(a.available_balance) : 0),
      0
    )
  );

  const grandTotal = $derived(showLoans ? cashTotal + loanRedrawTotal : cashTotal);

  // Groups to render: type → AccountBalance[]; ordered by TYPE_ORDER
  const visibleGroups = $derived(
    (() => {
      const shown = showLoans ? accounts : cashAccounts;
      const map = new Map<string, AccountBalance[]>();
      for (const a of shown) {
        if (!map.has(a.type)) map.set(a.type, []);
        map.get(a.type)!.push(a);
      }
      return TYPE_ORDER.filter(t => map.has(t)).map(t => ({ type: t, rows: map.get(t)! }));
    })()
  );

  function groupSubtotal(type: string, rows: AccountBalance[]): number {
    if (type === 'loan') {
      return rows.reduce(
        (sum, a) => sum + (a.available_balance != null ? parseFloat(a.available_balance) : 0),
        0
      );
    }
    return rows.reduce((sum, a) => sum + parseFloat(a.current_balance), 0);
  }

  function fmt(value: number): string {
    return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(value);
  }
</script>

<div class="page">
  <div class="page-header">
    <h2>Cash Reserves</h2>
    {#if !loading && !error}
      <p class="grand-total">{fmt(grandTotal)}</p>
    {/if}
  </div>

  {#if loading}
    <p class="status-msg">Loading…</p>
  {:else if error}
    <p class="status-msg error">{error}</p>
  {:else}
    {#if hasLoans}
      <label class="loan-toggle">
        <input type="checkbox" checked={showLoans} onchange={toggleLoans} />
        Include loan redraw
      </label>
    {/if}

    {#each visibleGroups as group}
      <section class="account-group">
        <h3 class="group-label">{TYPE_LABELS[group.type] ?? group.type}</h3>
        {#each group.rows as account}
          <div class="account-row">
            <div class="account-info">
              <span class="account-name">{account.display_name}</span>
              {#if account.last_import_at == null}
                <span class="no-import">No imports yet</span>
              {/if}
            </div>
            <div class="account-balances">
              {#if account.type === 'loan'}
                {#if account.available_balance != null}
                  <span class="balance redraw">{fmt(parseFloat(account.available_balance))}</span>
                  <span class="balance-label">redraw</span>
                {:else}
                  <span class="balance muted">—</span>
                {/if}
              {:else}
                <span class="balance" class:muted={account.last_import_at == null}>
                  {account.last_import_at == null ? '$0.00' : fmt(parseFloat(account.current_balance))}
                </span>
              {/if}
            </div>
          </div>
        {/each}
        <div class="group-subtotal">
          <span>Subtotal</span>
          <span>{fmt(groupSubtotal(group.type, group.rows))}</span>
        </div>
      </section>
    {/each}
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .page-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  h2 {
    font-size: 20px;
    font-weight: 700;
    color: #111827;
    margin: 0;
  }

  .grand-total {
    font-size: 32px;
    font-weight: 700;
    color: #111827;
    margin: 0;
    letter-spacing: -0.5px;
  }

  .status-msg {
    color: #9ca3af;
    font-size: 14px;
    margin: 0;
  }

  .status-msg.error {
    color: #dc2626;
  }

  .loan-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #374151;
    cursor: pointer;
    user-select: none;
  }

  .loan-toggle input[type='checkbox'] {
    width: 16px;
    height: 16px;
    cursor: pointer;
  }

  .account-group {
    display: flex;
    flex-direction: column;
    gap: 0;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
  }

  .group-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6b7280;
    margin: 0;
    padding: 10px 16px 8px;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
  }

  .account-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #f3f4f6;
  }

  .account-row:last-of-type {
    border-bottom: none;
  }

  .account-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .account-name {
    font-size: 15px;
    font-weight: 500;
    color: #111827;
  }

  .no-import {
    font-size: 12px;
    color: #9ca3af;
  }

  .account-balances {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .balance {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
  }

  .balance.muted {
    color: #9ca3af;
    font-weight: 400;
  }

  .balance.redraw {
    color: #059669;
  }

  .balance-label {
    font-size: 11px;
    color: #6b7280;
  }

  .group-subtotal {
    display: flex;
    justify-content: space-between;
    padding: 10px 16px;
    background: #f9fafb;
    border-top: 1px solid #e5e7eb;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
  }
</style>

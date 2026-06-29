<script lang="ts">
  import { onMount } from 'svelte';
  import { getLoans, type LoanDetail } from '$lib/api/loans';

  let loans = $state<LoanDetail[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      loans = await getLoans();
    } catch {
      error = 'Failed to load loans.';
    } finally {
      loading = false;
    }
  });

  const totalOwing = $derived(
    loans.reduce((sum, l) => sum + parseFloat(l.balance_owing), 0)
  );

  function progressPct(loan: LoanDetail): number {
    const principal = parseFloat(loan.original_principal);
    if (principal === 0) return 0;
    const repaid = principal - parseFloat(loan.balance_owing);
    return Math.max(0, Math.min(1, repaid / principal));
  }

  function amountRepaid(loan: LoanDetail): number {
    return parseFloat(loan.original_principal) - parseFloat(loan.balance_owing);
  }

  function fmtMonthYear(iso: string): string {
    // iso is "YYYY-MM-DD"; append time to avoid UTC-shift on date parsing
    return new Date(iso + 'T00:00:00').toLocaleDateString('en-AU', {
      month: 'short',
      year: 'numeric',
    });
  }

  function timeRemaining(endIso: string): string {
    const end = new Date(endIso + 'T00:00:00');
    const now = new Date();
    const months =
      (end.getFullYear() - now.getFullYear()) * 12 +
      (end.getMonth() - now.getMonth());
    if (months <= 0) return 'Paid off';
    const yrs = Math.floor(months / 12);
    const mos = months % 12;
    if (yrs === 0) return `${mos}mo remaining`;
    if (mos === 0) return `${yrs}yr remaining`;
    return `${yrs}yr ${mos}mo remaining`;
  }

  function fmtLastImport(iso: string): string {
    return new Date(iso).toLocaleDateString('en-AU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  }

  function fmt(value: number): string {
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: 'AUD',
    }).format(value);
  }

  function fmtRate(rate: string): string {
    return `${parseFloat(rate).toFixed(2)}% p.a.`;
  }
</script>

<div class="page">
  <div class="page-header">
    <h2>Loans</h2>
    {#if !loading && !error && loans.length > 0}
      <p class="grand-total">
        {fmt(totalOwing)} <span class="owing-label">owing</span>
      </p>
    {/if}
  </div>

  {#if loading}
    <p class="status-msg">Loading…</p>
  {:else if error}
    <p class="status-msg error">{error}</p>
  {:else if loans.length === 0}
    <p class="status-msg">No loans.</p>
  {:else}
    {#each loans as loan}
      <div class="loan-card">
        <div class="card-header">
          <div class="card-names">
            <span class="loan-name">{loan.display_name}</span>
            <span class="bank-label">{loan.bank_code.toUpperCase()}</span>
          </div>
          <div class="card-balance">
            <span class="balance-owing">{fmt(parseFloat(loan.balance_owing))}</span>
            <span class="owing-tag">owing</span>
          </div>
        </div>

        <div class="card-meta">
          <span class="rate">{fmtRate(loan.interest_rate)}</span>
          {#if loan.available_balance != null}
            <span class="redraw">{fmt(parseFloat(loan.available_balance))} redraw</span>
          {/if}
        </div>

        <div class="progress-section">
          <div class="progress-track">
            <div
              class="progress-fill"
              style="width: {(progressPct(loan) * 100).toFixed(1)}%"
            ></div>
          </div>
          <p class="progress-label">
            {fmt(amountRepaid(loan))} repaid of {fmt(parseFloat(loan.original_principal))}
          </p>
        </div>

        {#if loan.start_date && loan.end_date}
          <p class="date-range">
            {fmtMonthYear(loan.start_date)} → {fmtMonthYear(loan.end_date)}
            · {timeRemaining(loan.end_date)}
          </p>
        {:else if loan.start_date}
          <p class="date-range">Started {fmtMonthYear(loan.start_date)}</p>
        {/if}

        <p class="last-updated">
          {#if loan.last_import_at}
            Last updated {fmtLastImport(loan.last_import_at)}
          {:else}
            Not yet imported
          {/if}
        </p>
      </div>
    {/each}
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 20px;
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

  .owing-label {
    font-size: 16px;
    font-weight: 400;
    color: #6b7280;
  }

  .status-msg {
    color: #9ca3af;
    font-size: 14px;
    margin: 0;
  }

  .status-msg.error {
    color: #dc2626;
  }

  .loan-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 16px;
    background: #ffffff;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
  }

  .card-names {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .loan-name {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
  }

  .bank-label {
    font-size: 11px;
    font-weight: 500;
    color: #9ca3af;
    letter-spacing: 0.04em;
  }

  .card-balance {
    display: flex;
    align-items: baseline;
    gap: 4px;
    flex-shrink: 0;
  }

  .balance-owing {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
  }

  .owing-tag {
    font-size: 12px;
    color: #6b7280;
  }

  .card-meta {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .rate {
    font-size: 13px;
    color: #374151;
    font-weight: 500;
  }

  .redraw {
    font-size: 13px;
    color: #059669;
    font-weight: 500;
  }

  .progress-section {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .progress-track {
    height: 6px;
    background: #e5e7eb;
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: #2563eb;
    border-radius: 3px;
    transition: width 0.3s ease;
  }

  .progress-label {
    font-size: 12px;
    color: #6b7280;
    margin: 0;
  }

  .date-range {
    font-size: 12px;
    color: #6b7280;
    margin: 0;
  }

  .last-updated {
    font-size: 12px;
    color: #9ca3af;
    margin: 0;
  }
</style>

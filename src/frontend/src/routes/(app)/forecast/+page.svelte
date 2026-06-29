<script lang="ts">
  import { onMount } from 'svelte';
  import { getForecast, type ForecastData } from '$lib/api/forecast';

  let data = $state<ForecastData | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      data = await getForecast();
    } catch {
      error = 'Failed to load forecast.';
    } finally {
      loading = false;
    }
  });

  function fmt(value: number): string {
    return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(value);
  }

  function fmtShort(value: number): string {
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: 'AUD',
      maximumFractionDigits: 0,
    }).format(value);
  }

  function fmtDelta(delta: number): string {
    const abs = fmtShort(Math.abs(delta));
    return delta >= 0 ? `+${abs}` : `-${abs}`;
  }

  function horizonLabel(months: number): string {
    return months === 1 ? '1 month' : `${months} months`;
  }
</script>

<div class="page">
  <h2>Forecast</h2>

  {#if loading}
    <p class="status-msg">Loading…</p>
  {:else if error}
    <p class="status-msg error">{error}</p>
  {:else if data}
    <!-- Today header: Cash / Loans breakdown + net Funds -->
    <div class="today-box">
      <p class="today-label">Your funds today</p>
      <div class="breakdown">
        <div class="breakdown-row">
          <span class="bl">Cash</span>
          <span class="bv">{fmt(parseFloat(data.cash_total))}</span>
        </div>
        <div class="breakdown-row">
          <span class="bl">Loans</span>
          <span class="bv">{fmt(parseFloat(data.loans_total))}</span>
        </div>
        <div class="breakdown-divider"></div>
        <div class="breakdown-row net-row">
          <span class="bl net-label">Funds</span>
          <span class="bv net-value">{fmt(parseFloat(data.net_funds))}</span>
        </div>
      </div>
    </div>

    <!-- Warning banner when <3 months of data but at least 1 -->
    {#if data.data_warning && data.months_of_data > 0}
      <div class="warning-banner">
        Based on {data.months_of_data}
        {data.months_of_data === 1 ? 'month' : 'months'} of data — import more for accuracy.
      </div>
    {/if}

    <!-- Three side-by-side horizon cards, or empty state -->
    {#if data.horizons.length === 0}
      <div class="empty-state">
        Import at least 1 month of transactions to see your forecast.
      </div>
    {:else}
      <div class="horizons">
        {#each data.horizons as h}
          {@const delta = parseFloat(h.delta)}
          {@const improving = delta >= 0}
          <div class="horizon-card">
            <p class="horizon-label">{horizonLabel(h.months)}</p>
            <p class="horizon-value">{fmtShort(parseFloat(h.projected_net_funds))}</p>
            <p class="horizon-delta" class:positive={improving} class:negative={!improving}>
              {improving ? '↑' : '↓'} {fmtDelta(delta)}
            </p>
          </div>
        {/each}
      </div>
    {/if}

    <!-- Static footnote -->
    <p class="footnote">
      Based on your last 3 months. Doesn't account for irregular expenses.
    </p>
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  h2 {
    font-size: 20px;
    font-weight: 700;
    color: #111827;
    margin: 0;
  }

  .status-msg {
    color: #9ca3af;
    font-size: 14px;
    margin: 0;
  }

  .status-msg.error {
    color: #dc2626;
  }

  /* Today header */
  .today-box {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 16px;
    background: #ffffff;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .today-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6b7280;
    margin: 0;
  }

  .breakdown {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .breakdown-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }

  .bl {
    font-size: 14px;
    color: #6b7280;
  }

  .bv {
    font-size: 16px;
    font-weight: 600;
    color: #111827;
  }

  .breakdown-divider {
    height: 1px;
    background: #e5e7eb;
    margin: 4px 0;
  }

  .net-label {
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }

  .net-value {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
  }

  /* Warning banner */
  .warning-banner {
    background: #fef9c3;
    border: 1px solid #fde047;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #854d0e;
  }

  /* Three side-by-side horizon cards */
  .horizons {
    display: flex;
    gap: 10px;
  }

  .horizon-card {
    flex: 1;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 14px 8px;
    background: #ffffff;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    text-align: center;
  }

  .horizon-label {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280;
    margin: 0;
  }

  .horizon-value {
    font-size: 15px;
    font-weight: 700;
    color: #111827;
    margin: 0;
  }

  .horizon-delta {
    font-size: 12px;
    font-weight: 600;
    margin: 0;
  }

  .horizon-delta.positive {
    color: #059669;
  }

  .horizon-delta.negative {
    color: #dc2626;
  }

  /* Empty state */
  .empty-state {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 24px 16px;
    background: #f9fafb;
    font-size: 14px;
    color: #6b7280;
    text-align: center;
  }

  /* Footnote */
  .footnote {
    font-size: 12px;
    color: #9ca3af;
    margin: 0;
    text-align: center;
  }
</style>

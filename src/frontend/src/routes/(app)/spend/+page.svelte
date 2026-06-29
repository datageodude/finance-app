<script lang="ts">
  import { onMount } from 'svelte';
  import { getSpendSummary, type SpendSummary } from '$lib/api/spend';

  let loading = $state(true);
  let error = $state<string | null>(null);
  let summary = $state<SpendSummary | null>(null);

  onMount(async () => {
    try {
      summary = await getSpendSummary();
    } catch {
      error = 'Failed to load spend summary.';
    } finally {
      loading = false;
    }
  });

  function fmt(value: number): string {
    return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(value);
  }

  function isOverBudget(actual: string, budget: string | null): boolean {
    if (budget === null) return false;
    return parseFloat(actual) > parseFloat(budget);
  }
</script>

<div class="page">
  <div class="page-header">
    <h2>Spend vs Budget</h2>
    {#if summary && !loading && !error}
      <p class="grand-total">
        {fmt(parseFloat(summary.total_actual))}
        {#if summary.total_budget !== null}
          <span class="grand-total-budget">/ {fmt(parseFloat(summary.total_budget))}</span>
        {/if}
      </p>
      {#if parseFloat(summary.uncategorised_actual) > 0}
        <p class="uncategorised-note">
          + {fmt(parseFloat(summary.uncategorised_actual))} uncategorised
        </p>
      {/if}
    {/if}
  </div>

  {#if loading}
    <p class="status-msg">Loading…</p>
  {:else if error}
    <p class="status-msg error">{error}</p>
  {:else if summary}
    {#if !summary.has_transactions}
      <p class="status-msg">No imports yet this month.</p>
    {/if}

    {#if summary.rows.length > 0}
      <section class="category-list">
        {#each summary.rows as row}
          <div class="category-row">
            <span class="category-name">{row.name}</span>
            <span class="category-amounts">
              <span
                class="actual"
                class:over={isOverBudget(row.actual, row.budget)}
              >{fmt(parseFloat(row.actual))}</span>
              {#if row.budget !== null}
                <span class="budget-cap">/ {fmt(parseFloat(row.budget))}</span>
              {/if}
            </span>
          </div>
        {/each}

        {#if parseFloat(summary.uncategorised_actual) > 0}
          <div class="category-row uncategorised">
            <span class="category-name">Uncategorised</span>
            <span class="category-amounts">
              <span class="actual muted">{fmt(parseFloat(summary.uncategorised_actual))}</span>
            </span>
          </div>
        {/if}
      </section>
    {/if}
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

  .grand-total-budget {
    font-size: 20px;
    font-weight: 400;
    color: #9ca3af;
  }

  .uncategorised-note {
    font-size: 13px;
    color: #6b7280;
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

  .category-list {
    display: flex;
    flex-direction: column;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
  }

  .category-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #f3f4f6;
  }

  .category-row:last-child {
    border-bottom: none;
  }

  .category-row.uncategorised {
    background: #fafafa;
  }

  .category-name {
    font-size: 15px;
    font-weight: 500;
    color: #111827;
  }

  .category-row.uncategorised .category-name {
    color: #6b7280;
    font-weight: 400;
  }

  .category-amounts {
    display: flex;
    align-items: baseline;
    gap: 4px;
  }

  .actual {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
  }

  .actual.over {
    color: #dc2626;
  }

  .actual.muted {
    color: #9ca3af;
    font-weight: 400;
  }

  .budget-cap {
    font-size: 13px;
    color: #9ca3af;
    font-weight: 400;
  }
</style>

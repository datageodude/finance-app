<script lang="ts">
  import { onMount } from 'svelte';
  import { getFlags, type FlagItem } from '$lib/api/flags';
  import FlagCard from '$lib/components/FlagCard.svelte';

  let flags = $state<FlagItem[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      flags = await getFlags();
    } catch {
      error = 'Failed to load flags. Try refreshing.';
    } finally {
      loading = false;
    }
  });

  function resolveFlag(flagId: number) {
    flags = flags.filter(f => f.flag_id !== flagId);
  }
</script>

<div class="page">
  <h2>Flagged Transactions</h2>

  {#if loading}
    <p class="status-msg">Loading…</p>
  {:else if error}
    <p class="error-msg">{error}</p>
  {:else if flags.length === 0}
    <div class="empty-state">
      <p class="empty-title">All clear</p>
      <p class="empty-sub">No flagged transactions to review.</p>
    </div>
  {:else}
    <p class="flag-count">{flags.length} item{flags.length === 1 ? '' : 's'} to review</p>
    <div class="flag-list">
      {#each flags as flag (flag.flag_id)}
        <FlagCard {flag} onResolve={() => resolveFlag(flag.flag_id)} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .page {
    padding: 16px;
    max-width: 600px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  h2 {
    font-size: 20px;
    font-weight: 700;
    color: #111827;
    margin: 0;
  }

  .status-msg, .error-msg {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  .error-msg { color: #dc2626; }

  .empty-state {
    text-align: center;
    padding: 48px 0;
  }

  .empty-title {
    font-size: 18px;
    font-weight: 600;
    color: #111827;
    margin: 0 0 4px;
  }

  .empty-sub {
    font-size: 14px;
    color: #9ca3af;
    margin: 0;
  }

  .flag-count {
    font-size: 13px;
    color: #6b7280;
    margin: 0;
  }

  .flag-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
</style>

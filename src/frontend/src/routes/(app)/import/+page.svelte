<script lang="ts">
  import { onMount } from 'svelte';
  import DropZone from '$lib/components/DropZone.svelte';
  import ImportCard from '$lib/components/ImportCard.svelte';
  import { getImportHistory, type ImportHistoryItem } from '$lib/api/imports';

  interface CardEntry {
    id: number;
    file: File;
    ready: boolean;
    done: boolean;
  }

  let nextId = 0;
  let cards: CardEntry[] = $state([]);
  let confirmTrigger: number = $state(0);
  let history: ImportHistoryItem[] = $state([]);
  let historyLoading: boolean = $state(true);
  // Track which cards have called onReady or onNotReady (i.e. are no longer loading)
  let resolvedIds: Set<number> = $state(new Set());

  let readyCount = $derived(cards.filter((c) => c.ready && !c.done).length);
  let allSettled = $derived(
    cards.length > 0 && cards.every((c) => resolvedIds.has(c.id)),
  );

  function addFiles(files: File[]) {
    for (const file of files) {
      cards.push({ id: nextId++, file, ready: false, done: false });
    }
  }

  function markReady(id: number) {
    const card = cards.find((c) => c.id === id);
    if (card) card.ready = true;
    resolvedIds = new Set([...resolvedIds, id]);
  }

  function markNotReady(id: number) {
    const card = cards.find((c) => c.id === id);
    if (card) card.ready = false;
    resolvedIds = new Set([...resolvedIds, id]);
  }

  function markSuccess(id: number) {
    const card = cards.find((c) => c.id === id);
    if (card) { card.done = true; card.ready = false; }
  }

  function dismissCard(id: number) {
    cards = cards.filter((c) => c.id !== id);
    const next = new Set(resolvedIds);
    next.delete(id);
    resolvedIds = next;
  }

  // After all settled cards are done or errored, pause then reset
  $effect(() => {
    if (
      cards.length > 0 &&
      cards.every((c) => c.done || (resolvedIds.has(c.id) && !c.ready))
    ) {
      const hadSuccess = cards.some((c) => c.done);
      if (hadSuccess) {
        setTimeout(async () => {
          cards = [];
          resolvedIds = new Set();
          await refreshHistory();
        }, 2000);
      }
    }
  });

  async function refreshHistory() {
    try {
      history = await getImportHistory(10);
    } catch { /* non-fatal */ }
  }

  onMount(async () => {
    historyLoading = true;
    await refreshHistory();
    historyLoading = false;
  });

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-AU', {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  }
</script>

<div class="page">
  <h2>Import</h2>

  <DropZone onFiles={addFiles} />

  {#if cards.length > 0}
    <div class="cards-list">
      {#each cards as card (card.id)}
        <ImportCard
          file={card.file}
          {confirmTrigger}
          onDismiss={() => dismissCard(card.id)}
          onReady={() => markReady(card.id)}
          onNotReady={() => markNotReady(card.id)}
          onSuccess={() => markSuccess(card.id)}
        />
      {/each}
    </div>

    <div class="import-bar">
      <button
        class="import-btn"
        disabled={readyCount === 0 || !allSettled}
        onclick={() => { confirmTrigger += 1; }}
      >
        {readyCount > 0 ? `Import ${readyCount} file${readyCount !== 1 ? 's' : ''}` : 'No files ready'}
      </button>
    </div>
  {/if}

  <section class="history">
    <h3>Recent imports</h3>
    {#if historyLoading}
      <p class="muted">Loading…</p>
    {:else if history.length === 0}
      <p class="muted">No imports yet.</p>
    {:else}
      <ul class="history-list">
        {#each history as item (item.import_id)}
          <li class="history-item">
            <div class="history-left">
              <span class="h-filename">{item.filename}</span>
              <span class="h-account">{item.account_display_name}</span>
            </div>
            <div class="history-right">
              <span class="h-rows">{item.rows_added} added</span>
              <span class="h-date">{formatDate(item.created_at)}</span>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
</div>

<style>
  .page {
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

  .cards-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .import-bar {
    display: flex;
    justify-content: flex-end;
  }

  .import-btn {
    padding: 10px 20px;
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    background: #2563eb;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .import-btn:disabled {
    background: #93c5fd;
    cursor: default;
  }

  .history h3 {
    font-size: 15px;
    font-weight: 600;
    color: #374151;
    margin: 0 0 8px;
  }

  .muted {
    font-size: 13px;
    color: #9ca3af;
    margin: 0;
  }

  .history-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .history-item {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 8px 0;
    border-bottom: 1px solid #f3f4f6;
  }

  .history-left {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
    padding-right: 8px;
  }

  .h-filename {
    font-size: 13px;
    font-weight: 500;
    color: #111827;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .h-account {
    font-size: 12px;
    color: #9ca3af;
  }

  .history-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
    flex-shrink: 0;
  }

  .h-rows {
    font-size: 13px;
    font-weight: 600;
    color: #16a34a;
  }

  .h-date {
    font-size: 12px;
    color: #9ca3af;
  }
</style>

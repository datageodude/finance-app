<script lang="ts">
  let { onFiles }: { onFiles: (files: File[]) => void } = $props();

  let dragOver = $state(false);
  let rejectMsg = $state('');
  let inputEl: HTMLInputElement;

  function filterCsv(files: FileList | File[]): File[] {
    return Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.csv'));
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragOver = false;
    rejectMsg = '';
    const all = Array.from(e.dataTransfer?.files ?? []);
    const csvs = filterCsv(all);
    if (csvs.length === 0) {
      rejectMsg = 'CSV files only';
      return;
    }
    if (csvs.length < all.length) rejectMsg = 'Non-CSV files ignored';
    onFiles(csvs);
  }

  function handlePick(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    const csvs = filterCsv(input.files ?? []);
    if (csvs.length > 0) onFiles(csvs);
    input.value = '';
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="drop-zone"
  class:drag-over={dragOver}
  role="button"
  tabindex="0"
  aria-label="Drop CSV files here or click to browse"
  onclick={() => inputEl.click()}
  onkeydown={(e) => e.key === 'Enter' || e.key === ' ' ? inputEl.click() : null}
  ondragover={(e) => { e.preventDefault(); dragOver = true; }}
  ondragleave={() => { dragOver = false; }}
  ondrop={handleDrop}
>
  <input
    bind:this={inputEl}
    type="file"
    accept=".csv"
    multiple
    hidden
    onchange={handlePick}
  />
  <span class="icon">📂</span>
  <p class="primary">Drop CSV files here</p>
  <p class="secondary">or click to browse</p>
  {#if rejectMsg}
    <p class="reject">{rejectMsg}</p>
  {/if}
</div>

<style>
  .drop-zone {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    border: 2px dashed #d1d5db;
    border-radius: 12px;
    padding: 32px 16px;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    text-align: center;
  }

  .drop-zone.drag-over {
    border-color: #2563eb;
    background: #eff6ff;
  }

  .icon {
    font-size: 32px;
    line-height: 1;
    margin-bottom: 4px;
  }

  .primary {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
    margin: 0;
  }

  .secondary {
    font-size: 13px;
    color: #9ca3af;
    margin: 0;
  }

  .reject {
    font-size: 13px;
    color: #dc2626;
    margin: 4px 0 0;
  }
</style>

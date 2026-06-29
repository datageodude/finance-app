<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { getMe, logout as apiLogout } from '$lib/api/auth';
  import { user } from '$lib/stores/user';
  import TabNav from '$lib/components/TabNav.svelte';

  let { children } = $props();
  let loading = $state(true);

  onMount(async () => {
    try {
      const me = await getMe();
      if (!me) {
        goto('/login');
        return;
      }
      user.set(me);
    } catch {
      goto('/login');
    } finally {
      loading = false;
    }
  });

  async function handleLogout() {
    await apiLogout();
    user.set(null);
    goto('/login');
  }
</script>

{#if loading}
  <div class="loading" aria-busy="true">Loading…</div>
{:else}
  <div class="app-shell">
    <header class="app-header">
      <span class="app-title">Finance</span>
      <div class="header-right">
        <span class="user-name">{$user?.display_name}</span>
        <a href="/import" class="import-link">Import</a>
        <button class="logout-btn" onclick={handleLogout}>Log out</button>
      </div>
    </header>
    <main class="app-content">
      {@render children()}
    </main>
    <TabNav />
  </div>
{/if}

<style>
  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100dvh;
    color: #9ca3af;
  }

  .app-shell {
    display: flex;
    flex-direction: column;
    min-height: 100dvh;
  }

  .app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    height: 52px;
    background: #ffffff;
    border-bottom: 1px solid #e5e7eb;
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .app-title {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .user-name {
    font-size: 14px;
    color: #6b7280;
  }

  .import-link {
    font-size: 14px;
    color: #2563eb;
    text-decoration: none;
  }

  .logout-btn {
    font-size: 14px;
    color: #2563eb;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
  }

  .app-content {
    flex: 1;
    padding: 16px 16px 72px;
  }
</style>

<script lang="ts">
  import { page } from '$app/stores';

  const tabs = [
    { href: '/cash', label: 'Cash' },
    { href: '/spend', label: 'Spend' },
    { href: '/flagged', label: 'Flagged' },
    { href: '/loans', label: 'Loans' },
    { href: '/forecast', label: 'Forecast' },
  ] as const;
</script>

<nav class="tab-nav" aria-label="Main navigation">
  {#each tabs as tab}
    <a
      href={tab.href}
      class:active={$page.url.pathname.startsWith(tab.href)}
      aria-current={$page.url.pathname.startsWith(tab.href) ? 'page' : undefined}
    >
      {tab.label}
    </a>
  {/each}
</nav>

<style>
  .tab-nav {
    display: flex;
    justify-content: space-around;
    align-items: center;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: #ffffff;
    border-top: 1px solid #e5e7eb;
    padding-bottom: env(safe-area-inset-bottom);
  }

  a {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-decoration: none;
    color: #9ca3af;
    font-size: 13px;
    font-weight: 500;
    transition: color 0.15s;
  }

  a.active {
    color: #2563eb;
  }
</style>

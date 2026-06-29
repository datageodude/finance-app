<script lang="ts">
  import { goto } from '$app/navigation';
  import { login } from '$lib/api/auth';
  import { user } from '$lib/stores/user';

  let email = $state('');
  let password = $state('');
  let error = $state('');
  let loading = $state(false);

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    loading = true;
    error = '';
    try {
      const me = await login(email, password);
      user.set(me);
      goto('/cash');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Login failed';
    } finally {
      loading = false;
    }
  }
</script>

<div class="login-page">
  <h1>Finance</h1>
  <form onsubmit={handleSubmit}>
    <label>
      Email
      <input
        type="email"
        bind:value={email}
        required
        autocomplete="email"
        disabled={loading}
      />
    </label>
    <label>
      Password
      <input
        type="password"
        bind:value={password}
        required
        autocomplete="current-password"
        disabled={loading}
      />
    </label>
    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}
    <button type="submit" disabled={loading}>
      {loading ? 'Signing in…' : 'Sign in'}
    </button>
  </form>
</div>

<style>
  .login-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100dvh;
    padding: 24px;
    gap: 32px;
  }

  h1 {
    font-size: 28px;
    font-weight: 700;
    color: #111827;
    margin: 0;
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 16px;
    width: 100%;
    max-width: 360px;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 14px;
    font-weight: 500;
    color: #374151;
  }

  input {
    padding: 10px 14px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 16px;
    outline: none;
    transition: border-color 0.15s;
  }

  input:focus {
    border-color: #2563eb;
  }

  button {
    padding: 12px;
    background: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }

  button:disabled {
    background: #93c5fd;
    cursor: not-allowed;
  }

  .error {
    color: #dc2626;
    font-size: 14px;
    margin: 0;
  }
</style>

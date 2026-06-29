<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  onMount(() => goto('/cash', { replaceState: true }));
</script>

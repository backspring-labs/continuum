<script lang="ts">
	import { onMount } from 'svelte';

	interface SlotInfo {
		id: string;
		count: number;
	}

	let slots = $state<SlotInfo[]>([]);
	let fingerprint = $state('');
	let loading = $state(true);

	onMount(async () => {
		try {
			const res = await fetch('/api/registry');
			const data = await res.json();
			fingerprint = data.registry_fingerprint;
			slots = Object.entries(data.regions).map(([id, contributions]) => ({
				id,
				count: (contributions as any[]).length,
			})).sort((a, b) => b.count - a.count);
		} catch (e) {
			console.error('Failed to fetch registry:', e);
		} finally {
			loading = false;
		}
	});
</script>

<div class="registry-panel">
	<header class="panel-header">
		<h3>Registry Slots</h3>
		<code class="fingerprint">{fingerprint}</code>
	</header>
	<div class="slots-list">
		{#if loading}
			<div class="loading">Loading registry...</div>
		{:else}
			{#each slots as slot}
				<div class="slot-item">
					<code class="slot-id">{slot.id}</code>
					<div class="slot-bar">
						<div
							class="slot-fill"
							style="width: {Math.min(slot.count * 15, 100)}%"
						></div>
					</div>
					<span class="slot-count">{slot.count}</span>
				</div>
			{/each}
		{/if}
	</div>
</div>

<style>
	.registry-panel {
		background: var(--continuum-bg-secondary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		overflow: hidden;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-bg-tertiary);
		border-bottom: 1px solid var(--continuum-border);
	}

	.panel-header h3 {
		margin: 0;
		font-size: var(--continuum-font-size-md);
		font-weight: 600;
	}

	.fingerprint {
		font-size: var(--continuum-font-size-xs);
		padding: 2px 6px;
		background: var(--continuum-bg-hover);
		border-radius: var(--continuum-radius-sm);
		color: var(--continuum-text-secondary);
	}

	.slots-list {
		padding: var(--continuum-space-md);
	}

	.loading {
		text-align: center;
		color: var(--continuum-text-secondary);
	}

	.slot-item {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-sm);
		margin-bottom: var(--continuum-space-sm);
	}

	.slot-id {
		width: 140px;
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-accent-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.slot-bar {
		flex: 1;
		height: 6px;
		background: var(--continuum-bg-tertiary);
		border-radius: 3px;
		overflow: hidden;
	}

	.slot-fill {
		height: 100%;
		background: var(--continuum-accent-primary);
		border-radius: 3px;
		transition: width 300ms ease;
	}

	.slot-count {
		width: 24px;
		text-align: right;
		font-size: var(--continuum-font-size-sm);
		font-weight: 600;
	}
</style>

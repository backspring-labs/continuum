<script lang="ts">
	import { onMount } from 'svelte';

	interface Plugin {
		id: string;
		name: string;
		version: string;
		status: string;
		contribution_count: number;
	}

	let plugins = $state<Plugin[]>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			const res = await fetch('/api/registry');
			const data = await res.json();
			plugins = data.plugins;
		} catch (e) {
			console.error('Failed to fetch plugins:', e);
		} finally {
			loading = false;
		}
	});

	const statusColors: Record<string, string> = {
		'LOADED': 'var(--continuum-accent-success)',
		'FAILED': 'var(--continuum-accent-danger)',
		'DISABLED': 'var(--continuum-text-muted)',
	};
</script>

<div class="plugins-panel">
	<header class="panel-header">
		<h3>Loaded Plugins</h3>
		<span class="plugin-count">{plugins.length}</span>
	</header>
	<div class="plugins-list">
		{#if loading}
			<div class="loading">Loading plugins...</div>
		{:else}
			{#each plugins as plugin}
				<div class="plugin-item">
					<div class="plugin-status" style="background: {statusColors[plugin.status]}"></div>
					<div class="plugin-info">
						<div class="plugin-name">{plugin.name}</div>
						<div class="plugin-meta">
							<span class="plugin-id">{plugin.id}</span>
							<span class="plugin-version">v{plugin.version}</span>
						</div>
					</div>
					<div class="plugin-contributions">
						<span class="contribution-count">{plugin.contribution_count}</span>
						<span class="contribution-label">contributions</span>
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div>

<style>
	.plugins-panel {
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

	.plugin-count {
		padding: 2px 8px;
		background: var(--continuum-accent-primary);
		border-radius: 10px;
		font-size: var(--continuum-font-size-xs);
		font-weight: 600;
		color: white;
	}

	.plugins-list {
		padding: var(--continuum-space-sm);
	}

	.loading {
		padding: var(--continuum-space-lg);
		text-align: center;
		color: var(--continuum-text-secondary);
	}

	.plugin-item {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-sm);
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-bg-tertiary);
		border-radius: var(--continuum-radius-sm);
		margin-bottom: var(--continuum-space-sm);
	}

	.plugin-status {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.plugin-info {
		flex: 1;
		min-width: 0;
	}

	.plugin-name {
		font-size: var(--continuum-font-size-sm);
		font-weight: 600;
	}

	.plugin-meta {
		display: flex;
		gap: var(--continuum-space-sm);
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
	}

	.plugin-id {
		font-family: var(--continuum-font-mono);
	}

	.plugin-contributions {
		text-align: right;
	}

	.contribution-count {
		display: block;
		font-size: var(--continuum-font-size-lg);
		font-weight: 600;
	}

	.contribution-label {
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
	}
</style>

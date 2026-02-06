<svelte:options customElement="continuum-sample-systems-plugins" />

<script lang="ts">
	import { onMount } from 'svelte';

	interface Plugin {
		id: string;
		name: string;
		version: string;
		status: string;
		discovery_index: number;
		required: boolean;
		error: string | null;
		contribution_count: number;
		load_time_ms?: number;
	}

	let plugins = $state<Plugin[]>([]);
	let loading = $state(true);
	let statusFilter = $state<string>('all');
	let expandedId = $state<string | null>(null);

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

	const filteredPlugins = $derived(
		statusFilter === 'all'
			? plugins
			: plugins.filter(p => p.status === statusFilter)
	);

	const statusCounts = $derived({
		all: plugins.length,
		LOADED: plugins.filter(p => p.status === 'LOADED').length,
		FAILED: plugins.filter(p => p.status === 'FAILED').length,
		DISABLED: plugins.filter(p => p.status === 'DISABLED').length,
	});

	const statusColors: Record<string, string> = {
		'LOADED': 'var(--continuum-accent-success, #3fb950)',
		'FAILED': 'var(--continuum-accent-danger, #f85149)',
		'DISABLED': 'var(--continuum-text-muted, #6e6e80)',
	};

	function toggleExpand(id: string) {
		expandedId = expandedId === id ? null : id;
	}
</script>

<div class="plugins-panel">
	<header class="panel-header">
		<h3>Loaded Plugins</h3>
		<span class="plugin-count">{plugins.length}</span>
	</header>

	<div class="filter-bar">
		<button
			class="filter-btn"
			class:active={statusFilter === 'all'}
			onclick={() => statusFilter = 'all'}
		>
			All ({statusCounts.all})
		</button>
		<button
			class="filter-btn loaded"
			class:active={statusFilter === 'LOADED'}
			onclick={() => statusFilter = 'LOADED'}
		>
			Loaded ({statusCounts.LOADED})
		</button>
		<button
			class="filter-btn failed"
			class:active={statusFilter === 'FAILED'}
			onclick={() => statusFilter = 'FAILED'}
		>
			Failed ({statusCounts.FAILED})
		</button>
		<button
			class="filter-btn disabled"
			class:active={statusFilter === 'DISABLED'}
			onclick={() => statusFilter = 'DISABLED'}
		>
			Disabled ({statusCounts.DISABLED})
		</button>
	</div>

	<div class="plugins-table">
		{#if loading}
			<div class="loading">Loading plugins...</div>
		{:else if filteredPlugins.length === 0}
			<div class="empty">No plugins match the filter</div>
		{:else}
			<div class="table-header">
				<span class="col-status"></span>
				<span class="col-name">Name</span>
				<span class="col-version">Version</span>
				<span class="col-load-time">Load Time</span>
				<span class="col-contributions">Contributions</span>
				<span class="col-index">Index</span>
			</div>
			{#each filteredPlugins as plugin}
				<div
					class="plugin-row"
					class:expanded={expandedId === plugin.id}
					class:failed={plugin.status === 'FAILED'}
				>
					<button class="plugin-main" onclick={() => toggleExpand(plugin.id)}>
						<span class="col-status">
							<span class="status-dot" style="background: {statusColors[plugin.status]}"></span>
						</span>
						<span class="col-name">
							<span class="plugin-name">{plugin.name}</span>
							<span class="plugin-id">{plugin.id}</span>
						</span>
						<span class="col-version">{plugin.version}</span>
						<span class="col-load-time">{plugin.load_time_ms ? `${plugin.load_time_ms.toFixed(1)}ms` : '-'}</span>
						<span class="col-contributions">{plugin.contribution_count}</span>
						<span class="col-index">{plugin.discovery_index}</span>
						<span class="expand-icon">{expandedId === plugin.id ? '−' : '+'}</span>
					</button>

					{#if expandedId === plugin.id}
						<div class="plugin-details">
							<div class="detail-row">
								<span class="detail-label">Plugin ID</span>
								<code class="detail-value">{plugin.id}</code>
							</div>
							<div class="detail-row">
								<span class="detail-label">Status</span>
								<span class="detail-value" style="color: {statusColors[plugin.status]}">{plugin.status}</span>
							</div>
							<div class="detail-row">
								<span class="detail-label">Required</span>
								<span class="detail-value">{plugin.required ? 'Yes' : 'No'}</span>
							</div>
							<div class="detail-row">
								<span class="detail-label">Discovery Index</span>
								<span class="detail-value">{plugin.discovery_index}</span>
							</div>
							<div class="detail-row">
								<span class="detail-label">Contributions</span>
								<span class="detail-value">{plugin.contribution_count}</span>
							</div>
							{#if plugin.error}
								<div class="detail-error">
									<span class="detail-label">Error</span>
									<pre class="error-text">{plugin.error}</pre>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		{/if}
	</div>
</div>

<style>
	.plugins-panel {
		background: var(--continuum-bg-secondary, #1a1a2e);
		border: 1px solid var(--continuum-border, #2d2d44);
		border-radius: var(--continuum-radius-md, 8px);
		overflow: hidden;
		font-family: var(--continuum-font-sans, system-ui, sans-serif);
		color: var(--continuum-text-primary, #e8e8e8);
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--continuum-space-sm, 8px) var(--continuum-space-md, 16px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-bottom: 1px solid var(--continuum-border, #2d2d44);
	}

	.panel-header h3 {
		margin: 0;
		font-size: var(--continuum-font-size-md, 14px);
		font-weight: 600;
	}

	.plugin-count {
		padding: 2px 8px;
		background: var(--continuum-accent-primary, #58a6ff);
		border-radius: 10px;
		font-size: var(--continuum-font-size-xs, 11px);
		font-weight: 600;
		color: white;
	}

	.filter-bar {
		display: flex;
		gap: var(--continuum-space-xs, 4px);
		padding: var(--continuum-space-sm, 8px) var(--continuum-space-md, 16px);
		border-bottom: 1px solid var(--continuum-border, #2d2d44);
	}

	.filter-btn {
		padding: 4px 10px;
		background: var(--continuum-bg-tertiary, #12121f);
		border: 1px solid var(--continuum-border, #2d2d44);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-text-secondary, #a0a0a0);
		font-size: var(--continuum-font-size-xs, 11px);
		cursor: pointer;
		transition: all 150ms;
	}

	.filter-btn:hover {
		background: var(--continuum-bg-hover, #252538);
	}

	.filter-btn.active {
		background: var(--continuum-accent-primary, #58a6ff);
		border-color: var(--continuum-accent-primary, #58a6ff);
		color: white;
	}

	.filter-btn.loaded.active {
		background: var(--continuum-accent-success, #3fb950);
		border-color: var(--continuum-accent-success, #3fb950);
	}

	.filter-btn.failed.active {
		background: var(--continuum-accent-danger, #f85149);
		border-color: var(--continuum-accent-danger, #f85149);
	}

	.filter-btn.disabled.active {
		background: var(--continuum-text-muted, #6e6e80);
		border-color: var(--continuum-text-muted, #6e6e80);
	}

	.plugins-table {
		padding: var(--continuum-space-sm, 8px);
	}

	.loading, .empty {
		padding: var(--continuum-space-lg, 24px);
		text-align: center;
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.table-header {
		display: flex;
		align-items: center;
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-muted, #6e6e80);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.col-status { width: 24px; }
	.col-name { flex: 1; }
	.col-version { width: 60px; text-align: center; }
	.col-load-time { width: 70px; text-align: right; }
	.col-contributions { width: 80px; text-align: center; }
	.col-index { width: 40px; text-align: center; }

	.plugin-row {
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
		margin-bottom: var(--continuum-space-xs, 4px);
		overflow: hidden;
	}

	.plugin-row.failed {
		border-left: 3px solid var(--continuum-accent-danger, #f85149);
	}

	.plugin-main {
		display: flex;
		align-items: center;
		width: 100%;
		padding: var(--continuum-space-sm, 8px);
		background: transparent;
		border: none;
		color: var(--continuum-text-primary, #e8e8e8);
		cursor: pointer;
		text-align: left;
	}

	.plugin-main:hover {
		background: var(--continuum-bg-hover, #252538);
	}

	.status-dot {
		display: block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}

	.plugin-name {
		display: block;
		font-size: var(--continuum-font-size-sm, 12px);
		font-weight: 600;
	}

	.plugin-id {
		display: block;
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-muted, #6e6e80);
		font-family: var(--continuum-font-mono, monospace);
	}

	.expand-icon {
		width: 20px;
		text-align: center;
		color: var(--continuum-text-muted, #6e6e80);
	}

	.plugin-details {
		padding: var(--continuum-space-sm, 8px) var(--continuum-space-md, 16px);
		border-top: 1px solid var(--continuum-border, #2d2d44);
		background: var(--continuum-bg-secondary, #1a1a2e);
	}

	.detail-row {
		display: flex;
		justify-content: space-between;
		padding: var(--continuum-space-xs, 4px) 0;
		font-size: var(--continuum-font-size-xs, 11px);
	}

	.detail-label {
		color: var(--continuum-text-muted, #6e6e80);
	}

	.detail-value {
		font-weight: 500;
	}

	.detail-value code {
		font-family: var(--continuum-font-mono, monospace);
	}

	.detail-error {
		margin-top: var(--continuum-space-sm, 8px);
		padding-top: var(--continuum-space-sm, 8px);
		border-top: 1px solid var(--continuum-border, #2d2d44);
	}

	.error-text {
		margin: var(--continuum-space-xs, 4px) 0 0;
		padding: var(--continuum-space-sm, 8px);
		background: rgba(248, 81, 73, 0.1);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-accent-danger, #f85149);
		font-size: var(--continuum-font-size-xs, 11px);
		font-family: var(--continuum-font-mono, monospace);
		white-space: pre-wrap;
		overflow-x: auto;
	}
</style>

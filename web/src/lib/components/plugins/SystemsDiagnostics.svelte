<script lang="ts">
	import { onMount } from 'svelte';

	let lifecycleState = $state('');
	let warnings = $state<string[]>([]);
	let errors = $state<string[]>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			const res = await fetch('/diagnostics');
			const data = await res.json();
			lifecycleState = data.lifecycle_state;
			warnings = data.warnings || [];
			errors = data.errors || [];
		} catch (e) {
			console.error('Failed to fetch diagnostics:', e);
			errors = ['Failed to fetch diagnostics'];
		} finally {
			loading = false;
		}
	});

	const stateColors: Record<string, string> = {
		'ready': 'var(--continuum-accent-success)',
		'degraded': 'var(--continuum-accent-warning)',
		'booting': 'var(--continuum-accent-primary)',
	};
</script>

<div class="diagnostics-panel">
	<header class="panel-header">
		<h3>Diagnostics</h3>
	</header>
	<div class="diagnostics-content">
		{#if loading}
			<div class="loading">Loading...</div>
		{:else}
			<div class="state-row">
				<span class="state-label">Lifecycle State</span>
				<span
					class="state-value"
					style="color: {stateColors[lifecycleState] || 'inherit'}"
				>
					{lifecycleState.toUpperCase()}
				</span>
			</div>

			{#if errors.length > 0}
				<div class="issue-section">
					<h4 class="issue-title error">Errors ({errors.length})</h4>
					{#each errors as error}
						<div class="issue-item error">{error}</div>
					{/each}
				</div>
			{/if}

			{#if warnings.length > 0}
				<div class="issue-section">
					<h4 class="issue-title warning">Warnings ({warnings.length})</h4>
					{#each warnings as warning}
						<div class="issue-item warning">{warning}</div>
					{/each}
				</div>
			{/if}

			{#if errors.length === 0 && warnings.length === 0}
				<div class="all-clear">
					<span>✓</span>
					<p>All systems operational</p>
				</div>
			{/if}
		{/if}
	</div>
</div>

<style>
	.diagnostics-panel {
		background: var(--continuum-bg-secondary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		overflow: hidden;
	}

	.panel-header {
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-bg-tertiary);
		border-bottom: 1px solid var(--continuum-border);
	}

	.panel-header h3 {
		margin: 0;
		font-size: var(--continuum-font-size-md);
		font-weight: 600;
	}

	.diagnostics-content {
		padding: var(--continuum-space-md);
	}

	.loading {
		text-align: center;
		color: var(--continuum-text-secondary);
	}

	.state-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--continuum-space-sm);
		background: var(--continuum-bg-tertiary);
		border-radius: var(--continuum-radius-sm);
		margin-bottom: var(--continuum-space-md);
	}

	.state-label {
		font-size: var(--continuum-font-size-sm);
		color: var(--continuum-text-secondary);
	}

	.state-value {
		font-size: var(--continuum-font-size-sm);
		font-weight: 600;
	}

	.issue-section {
		margin-bottom: var(--continuum-space-md);
	}

	.issue-title {
		margin: 0 0 var(--continuum-space-sm);
		font-size: var(--continuum-font-size-sm);
		font-weight: 600;
	}

	.issue-title.error {
		color: var(--continuum-accent-danger);
	}

	.issue-title.warning {
		color: var(--continuum-accent-warning);
	}

	.issue-item {
		padding: var(--continuum-space-xs) var(--continuum-space-sm);
		font-size: var(--continuum-font-size-xs);
		border-radius: var(--continuum-radius-sm);
		margin-bottom: var(--continuum-space-xs);
	}

	.issue-item.error {
		background: rgba(248, 81, 73, 0.1);
		color: var(--continuum-accent-danger);
	}

	.issue-item.warning {
		background: rgba(210, 153, 34, 0.1);
		color: var(--continuum-accent-warning);
	}

	.all-clear {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: var(--continuum-space-md);
		color: var(--continuum-accent-success);
	}

	.all-clear span {
		font-size: 20px;
	}

	.all-clear p {
		margin: var(--continuum-space-xs) 0 0;
		font-size: var(--continuum-font-size-sm);
	}
</style>

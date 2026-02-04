<script lang="ts">
	import { onMount } from 'svelte';

	let metrics = $state([
		{ label: 'Active Signals', value: 147, trend: '+12%', status: 'success' },
		{ label: 'Warnings', value: 23, trend: '+3%', status: 'warning' },
		{ label: 'Critical', value: 2, trend: '-1', status: 'danger' },
		{ label: 'Latency P99', value: '142ms', trend: '-8%', status: 'success' },
	]);

	onMount(() => {
		// Simulate live updates
		const interval = setInterval(() => {
			metrics = metrics.map(m => ({
				...m,
				value: typeof m.value === 'number'
					? m.value + Math.floor(Math.random() * 5) - 2
					: m.value
			}));
		}, 3000);
		return () => clearInterval(interval);
	});
</script>

<div class="metrics-panel">
	<header class="panel-header">
		<h3>Signal Metrics</h3>
		<span class="live-indicator">● Live</span>
	</header>
	<div class="metrics-grid">
		{#each metrics as metric}
			<div class="metric-card" data-status={metric.status}>
				<div class="metric-value">{metric.value}</div>
				<div class="metric-label">{metric.label}</div>
				<div class="metric-trend" data-status={metric.status}>{metric.trend}</div>
			</div>
		{/each}
	</div>
</div>

<style>
	.metrics-panel {
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
		color: var(--continuum-text-primary);
	}

	.live-indicator {
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-accent-success);
		animation: pulse 2s infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	.metrics-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--continuum-space-md);
		padding: var(--continuum-space-md);
	}

	.metric-card {
		padding: var(--continuum-space-md);
		background: var(--continuum-bg-tertiary);
		border-radius: var(--continuum-radius-sm);
		text-align: center;
	}

	.metric-value {
		font-size: 28px;
		font-weight: 700;
		color: var(--continuum-text-primary);
	}

	.metric-card[data-status="warning"] .metric-value {
		color: var(--continuum-accent-warning);
	}

	.metric-card[data-status="danger"] .metric-value {
		color: var(--continuum-accent-danger);
	}

	.metric-label {
		font-size: var(--continuum-font-size-sm);
		color: var(--continuum-text-secondary);
		margin-top: var(--continuum-space-xs);
	}

	.metric-trend {
		font-size: var(--continuum-font-size-xs);
		margin-top: var(--continuum-space-xs);
	}

	.metric-trend[data-status="success"] {
		color: var(--continuum-accent-success);
	}

	.metric-trend[data-status="warning"] {
		color: var(--continuum-accent-warning);
	}

	.metric-trend[data-status="danger"] {
		color: var(--continuum-accent-danger);
	}
</style>

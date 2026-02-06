<svelte:options customElement="continuum-sample-signal-metrics" />

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
		<span class="live-indicator">Live</span>
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
		color: var(--continuum-text-primary, #e8e8e8);
	}

	.live-indicator {
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-accent-success, #3fb950);
		animation: pulse 2s infinite;
	}

	.live-indicator::before {
		content: '\u25cf ';
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	.metrics-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--continuum-space-md, 16px);
		padding: var(--continuum-space-md, 16px);
	}

	.metric-card {
		padding: var(--continuum-space-md, 16px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
		text-align: center;
	}

	.metric-value {
		font-size: 28px;
		font-weight: 700;
		color: var(--continuum-text-primary, #e8e8e8);
	}

	.metric-card[data-status="warning"] .metric-value {
		color: var(--continuum-accent-warning, #d29922);
	}

	.metric-card[data-status="danger"] .metric-value {
		color: var(--continuum-accent-danger, #f85149);
	}

	.metric-label {
		font-size: var(--continuum-font-size-sm, 12px);
		color: var(--continuum-text-secondary, #a0a0a0);
		margin-top: var(--continuum-space-xs, 4px);
	}

	.metric-trend {
		font-size: var(--continuum-font-size-xs, 11px);
		margin-top: var(--continuum-space-xs, 4px);
	}

	.metric-trend[data-status="success"] {
		color: var(--continuum-accent-success, #3fb950);
	}

	.metric-trend[data-status="warning"] {
		color: var(--continuum-accent-warning, #d29922);
	}

	.metric-trend[data-status="danger"] {
		color: var(--continuum-accent-danger, #f85149);
	}
</style>

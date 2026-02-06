<svelte:options customElement="continuum-sample-signal-alerts" />

<script lang="ts">
	let alerts = $state([
		{ severity: 'critical', service: 'api-gateway', message: 'Error rate > 5%', time: '2m' },
		{ severity: 'warning', service: 'worker-03', message: 'Memory > 85%', time: '5m' },
		{ severity: 'warning', service: 'redis-01', message: 'Latency spike', time: '8m' },
	]);

	function dismissAlert(index: number) {
		alerts = alerts.filter((_, i) => i !== index);
	}
</script>

<div class="alerts-panel">
	<header class="panel-header">
		<h3>Active Alerts</h3>
		<span class="alert-count">{alerts.length}</span>
	</header>
	<div class="alerts-list">
		{#each alerts as alert, i}
			<div class="alert-item" data-severity={alert.severity}>
				<div class="alert-indicator"></div>
				<div class="alert-content">
					<div class="alert-service">{alert.service}</div>
					<div class="alert-message">{alert.message}</div>
				</div>
				<div class="alert-meta">
					<span class="alert-time">{alert.time}</span>
					<button class="dismiss-btn" onclick={() => dismissAlert(i)}>\u00d7</button>
				</div>
			</div>
		{/each}
		{#if alerts.length === 0}
			<div class="no-alerts">
				<span>\u2713</span>
				<p>No active alerts</p>
			</div>
		{/if}
	</div>
</div>

<style>
	.alerts-panel {
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

	.alert-count {
		padding: 2px 8px;
		background: var(--continuum-accent-danger, #f85149);
		border-radius: 10px;
		font-size: var(--continuum-font-size-xs, 11px);
		font-weight: 600;
		color: white;
	}

	.alerts-list {
		padding: var(--continuum-space-sm, 8px);
	}

	.alert-item {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-sm, 8px);
		padding: var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
		margin-bottom: var(--continuum-space-sm, 8px);
	}

	.alert-indicator {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.alert-item[data-severity="critical"] .alert-indicator {
		background: var(--continuum-accent-danger, #f85149);
		animation: pulse 1s infinite;
	}

	.alert-item[data-severity="warning"] .alert-indicator {
		background: var(--continuum-accent-warning, #d29922);
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.4; }
	}

	.alert-content {
		flex: 1;
		min-width: 0;
	}

	.alert-service {
		font-size: var(--continuum-font-size-sm, 12px);
		font-weight: 600;
	}

	.alert-message {
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.alert-meta {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-xs, 4px);
	}

	.alert-time {
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-muted, #6e6e80);
	}

	.dismiss-btn {
		padding: 2px 6px;
		background: transparent;
		border: none;
		color: var(--continuum-text-muted, #6e6e80);
		font-size: 16px;
		cursor: pointer;
		border-radius: var(--continuum-radius-sm, 4px);
	}

	.dismiss-btn:hover {
		background: var(--continuum-bg-hover, #252538);
		color: var(--continuum-text-primary, #e8e8e8);
	}

	.no-alerts {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: var(--continuum-space-lg, 24px);
		color: var(--continuum-accent-success, #3fb950);
	}

	.no-alerts span {
		font-size: 24px;
	}

	.no-alerts p {
		margin: var(--continuum-space-sm, 8px) 0 0;
		font-size: var(--continuum-font-size-sm, 12px);
	}
</style>

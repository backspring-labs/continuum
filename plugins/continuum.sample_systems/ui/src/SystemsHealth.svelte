<svelte:options customElement="continuum-sample-systems-health" />

<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	let lifecycleState = $state('');
	let pluginCount = $state(0);
	let loadedCount = $state(0);
	let failedCount = $state(0);
	let commandCount = $state(0);
	let slotCount = $state(0);
	let fingerprint = $state('');
	let loading = $state(true);
	let startTime = $state<Date | null>(null);
	let uptime = $state('');
	let uptimeInterval: ReturnType<typeof setInterval>;

	onMount(async () => {
		startTime = new Date();
		updateUptime();
		uptimeInterval = setInterval(updateUptime, 1000);

		try {
			const [healthRes, registryRes] = await Promise.all([
				fetch('/health'),
				fetch('/api/registry'),
			]);

			const healthData = await healthRes.json();
			const registryData = await registryRes.json();

			lifecycleState = healthData.lifecycle_state;
			fingerprint = registryData.registry_fingerprint;
			pluginCount = registryData.plugins?.length || 0;
			loadedCount = registryData.plugins?.filter((p: any) => p.status === 'LOADED').length || 0;
			failedCount = registryData.plugins?.filter((p: any) => p.status === 'FAILED').length || 0;
			commandCount = registryData.commands?.length || 0;

			let slots = 0;
			for (const contributions of Object.values(registryData.regions || {})) {
				slots += (contributions as any[]).length;
			}
			slotCount = slots;
		} catch (e) {
			console.error('Failed to fetch health data:', e);
		} finally {
			loading = false;
		}
	});

	onDestroy(() => {
		if (uptimeInterval) clearInterval(uptimeInterval);
	});

	function updateUptime() {
		if (!startTime) return;
		const now = new Date();
		const diff = Math.floor((now.getTime() - startTime.getTime()) / 1000);
		const hours = Math.floor(diff / 3600);
		const minutes = Math.floor((diff % 3600) / 60);
		const seconds = diff % 60;
		uptime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
	}

	const stateConfig: Record<string, { color: string; icon: string; label: string }> = {
		ready: {
			color: 'var(--continuum-accent-success, #3fb950)',
			icon: '✓',
			label: 'All Systems Operational',
		},
		degraded: {
			color: 'var(--continuum-accent-warning, #d29922)',
			icon: '!',
			label: 'Degraded Mode',
		},
		booting: {
			color: 'var(--continuum-accent-primary, #58a6ff)',
			icon: '⟳',
			label: 'Starting Up',
		},
	};

	const currentState = $derived(stateConfig[lifecycleState] || stateConfig.booting);
</script>

<div class="health-panel">
	<header class="panel-header">
		<h3>System Health</h3>
	</header>

	{#if loading}
		<div class="loading">Loading health data...</div>
	{:else}
		<div class="health-content">
			<!-- Status Hero -->
			<div class="status-hero" style="--status-color: {currentState.color}">
				<div class="status-icon">{currentState.icon}</div>
				<div class="status-info">
					<div class="status-state">{lifecycleState.toUpperCase()}</div>
					<div class="status-label">{currentState.label}</div>
				</div>
			</div>

			<!-- Metrics Grid -->
			<div class="metrics-grid">
				<div class="metric-card">
					<div class="metric-value">{pluginCount}</div>
					<div class="metric-label">Plugins</div>
					<div class="metric-detail">
						<span class="loaded">{loadedCount} loaded</span>
						{#if failedCount > 0}
							<span class="failed">{failedCount} failed</span>
						{/if}
					</div>
				</div>

				<div class="metric-card">
					<div class="metric-value">{commandCount}</div>
					<div class="metric-label">Commands</div>
					<div class="metric-detail">registered</div>
				</div>

				<div class="metric-card">
					<div class="metric-value">{slotCount}</div>
					<div class="metric-label">Contributions</div>
					<div class="metric-detail">active</div>
				</div>

				<div class="metric-card">
					<div class="metric-value uptime">{uptime}</div>
					<div class="metric-label">Uptime</div>
					<div class="metric-detail">session</div>
				</div>
			</div>

			<!-- Fingerprint -->
			<div class="fingerprint-row">
				<span class="fingerprint-label">Registry Fingerprint</span>
				<code class="fingerprint-value">{fingerprint}</code>
			</div>
		</div>
	{/if}
</div>

<style>
	.health-panel {
		background: var(--continuum-bg-secondary, #1a1a2e);
		border: 1px solid var(--continuum-border, #2d2d44);
		border-radius: var(--continuum-radius-md, 8px);
		overflow: hidden;
		font-family: var(--continuum-font-sans, system-ui, sans-serif);
		color: var(--continuum-text-primary, #e8e8e8);
	}

	.panel-header {
		padding: var(--continuum-space-sm, 8px) var(--continuum-space-md, 16px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-bottom: 1px solid var(--continuum-border, #2d2d44);
	}

	.panel-header h3 {
		margin: 0;
		font-size: var(--continuum-font-size-md, 14px);
		font-weight: 600;
	}

	.loading {
		padding: var(--continuum-space-lg, 24px);
		text-align: center;
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.health-content {
		padding: var(--continuum-space-md, 16px);
	}

	.status-hero {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-md, 16px);
		padding: var(--continuum-space-md, 16px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-md, 8px);
		border-left: 4px solid var(--status-color);
		margin-bottom: var(--continuum-space-md, 16px);
	}

	.status-icon {
		width: 48px;
		height: 48px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--status-color);
		border-radius: 50%;
		font-size: 24px;
		color: white;
	}

	.status-info {
		flex: 1;
	}

	.status-state {
		font-size: var(--continuum-font-size-lg, 16px);
		font-weight: 700;
		color: var(--status-color);
	}

	.status-label {
		font-size: var(--continuum-font-size-sm, 12px);
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.metrics-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--continuum-space-sm, 8px);
		margin-bottom: var(--continuum-space-md, 16px);
	}

	.metric-card {
		padding: var(--continuum-space-md, 16px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
		text-align: center;
	}

	.metric-value {
		font-size: var(--continuum-font-size-xl, 24px);
		font-weight: 700;
		color: var(--continuum-accent-primary, #58a6ff);
	}

	.metric-value.uptime {
		font-family: var(--continuum-font-mono, monospace);
		font-size: var(--continuum-font-size-lg, 16px);
	}

	.metric-label {
		font-size: var(--continuum-font-size-sm, 12px);
		font-weight: 600;
		color: var(--continuum-text-primary, #e8e8e8);
		margin-top: var(--continuum-space-xs, 4px);
	}

	.metric-detail {
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-muted, #6e6e80);
		margin-top: 2px;
	}

	.metric-detail .loaded {
		color: var(--continuum-accent-success, #3fb950);
	}

	.metric-detail .failed {
		color: var(--continuum-accent-danger, #f85149);
		margin-left: var(--continuum-space-xs, 4px);
	}

	.fingerprint-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
	}

	.fingerprint-label {
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-muted, #6e6e80);
	}

	.fingerprint-value {
		font-size: var(--continuum-font-size-xs, 11px);
		padding: 2px 6px;
		background: var(--continuum-bg-hover, #252538);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-text-secondary, #a0a0a0);
	}
</style>

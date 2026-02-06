<svelte:options customElement="continuum-sample-signal-timeline" />

<script lang="ts">
	let events = $state([
		{ time: '2 min ago', type: 'info', message: 'Deployment completed: api-gateway v2.3.1' },
		{ time: '5 min ago', type: 'warning', message: 'High memory usage detected on worker-03' },
		{ time: '12 min ago', type: 'success', message: 'Auto-scaling triggered: +2 instances' },
		{ time: '18 min ago', type: 'error', message: 'Connection timeout to redis-cluster-01' },
		{ time: '24 min ago', type: 'info', message: 'Config reload: rate-limits updated' },
		{ time: '31 min ago', type: 'success', message: 'Health check passed: all services green' },
	]);

	const typeIcons: Record<string, string> = {
		info: 'i',
		warning: '!',
		success: '\u2713',
		error: '\u2717',
	};
</script>

<div class="timeline-panel">
	<header class="panel-header">
		<h3>Event Timeline</h3>
		<button class="filter-btn">Filter</button>
	</header>
	<div class="timeline">
		{#each events as event}
			<div class="timeline-event" data-type={event.type}>
				<span class="event-icon" data-type={event.type}>{typeIcons[event.type]}</span>
				<div class="event-content">
					<span class="event-message">{event.message}</span>
					<span class="event-time">{event.time}</span>
				</div>
			</div>
		{/each}
	</div>
</div>

<style>
	.timeline-panel {
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

	.filter-btn {
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-hover, #252538);
		border: 1px solid var(--continuum-border, #2d2d44);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-text-secondary, #a0a0a0);
		font-size: var(--continuum-font-size-xs, 11px);
		cursor: pointer;
	}

	.filter-btn:hover {
		background: var(--continuum-bg-active, #303048);
		color: var(--continuum-text-primary, #e8e8e8);
	}

	.timeline {
		padding: var(--continuum-space-sm, 8px);
	}

	.timeline-event {
		display: flex;
		gap: var(--continuum-space-sm, 8px);
		padding: var(--continuum-space-sm, 8px);
		border-radius: var(--continuum-radius-sm, 4px);
		transition: background 150ms ease;
	}

	.timeline-event:hover {
		background: var(--continuum-bg-tertiary, #12121f);
	}

	.event-icon {
		flex-shrink: 0;
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		font-size: 11px;
		font-weight: bold;
	}

	.event-icon[data-type="info"] {
		background: rgba(88, 166, 255, 0.2);
		color: #58a6ff;
	}

	.event-icon[data-type="warning"] {
		background: rgba(210, 153, 34, 0.2);
		color: #d29922;
	}

	.event-icon[data-type="success"] {
		background: rgba(63, 185, 80, 0.2);
		color: #3fb950;
	}

	.event-icon[data-type="error"] {
		background: rgba(248, 81, 73, 0.2);
		color: #f85149;
	}

	.event-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.event-message {
		font-size: var(--continuum-font-size-sm, 12px);
	}

	.event-time {
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-muted, #6e6e80);
	}

	.timeline-event[data-type="error"] {
		border-left: 2px solid var(--continuum-accent-danger, #f85149);
	}

	.timeline-event[data-type="warning"] {
		border-left: 2px solid var(--continuum-accent-warning, #d29922);
	}
</style>

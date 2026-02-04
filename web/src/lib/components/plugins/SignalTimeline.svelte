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
		info: 'ℹ️',
		warning: '⚠️',
		success: '✅',
		error: '❌',
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
				<span class="event-icon">{typeIcons[event.type]}</span>
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

	.filter-btn {
		padding: var(--continuum-space-xs) var(--continuum-space-sm);
		background: var(--continuum-bg-hover);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-sm);
		color: var(--continuum-text-secondary);
		font-size: var(--continuum-font-size-xs);
		cursor: pointer;
	}

	.filter-btn:hover {
		background: var(--continuum-bg-active);
		color: var(--continuum-text-primary);
	}

	.timeline {
		padding: var(--continuum-space-sm);
	}

	.timeline-event {
		display: flex;
		gap: var(--continuum-space-sm);
		padding: var(--continuum-space-sm);
		border-radius: var(--continuum-radius-sm);
		transition: background 150ms ease;
	}

	.timeline-event:hover {
		background: var(--continuum-bg-tertiary);
	}

	.event-icon {
		flex-shrink: 0;
		width: 20px;
		text-align: center;
	}

	.event-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.event-message {
		font-size: var(--continuum-font-size-sm);
	}

	.event-time {
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
	}

	.timeline-event[data-type="error"] {
		border-left: 2px solid var(--continuum-accent-danger);
	}

	.timeline-event[data-type="warning"] {
		border-left: 2px solid var(--continuum-accent-warning);
	}
</style>

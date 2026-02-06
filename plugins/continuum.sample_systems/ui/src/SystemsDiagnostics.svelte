<svelte:options customElement="continuum-sample-systems-diagnostics" />

<script lang="ts">
	import { onMount } from 'svelte';

	interface LifecycleTransition {
		from: string;
		to: string;
		timestamp: string;
		reason?: string;
	}

	interface RegistryBuildReport {
		pluginsTotal: number;
		pluginsLoaded: number;
		pluginsFailed: number;
		commandsRegistered: number;
		contributionsTotal: number;
		conflicts: Array<{ slot_id: string; count: number }>;
		missingRequired: string[];
		buildDuration?: number;
	}

	let lifecycleState = $state('');
	let warnings = $state<string[]>([]);
	let errors = $state<string[]>([]);
	let loading = $state(true);
	let transitions = $state<LifecycleTransition[]>([]);
	let buildReport = $state<RegistryBuildReport | null>(null);

	onMount(async () => {
		try {
			const [diagRes, registryRes] = await Promise.all([
				fetch('/diagnostics'),
				fetch('/api/registry'),
			]);

			const diagData = await diagRes.json();
			const registryData = await registryRes.json();

			lifecycleState = diagData.lifecycle_state;
			warnings = diagData.warnings || [];
			errors = diagData.errors || [];
			transitions = diagData.lifecycle_transitions || [];

			// Build registry report from registry data
			const plugins = registryData.plugins || [];
			const commands = registryData.commands || [];
			const regions = registryData.regions || {};
			const diagnostics = registryData.diagnostics || {};

			let contributionCount = 0;
			for (const contributions of Object.values(regions)) {
				contributionCount += (contributions as any[]).length;
			}

			const conflicts = (diagnostics.conflicts || []).map((c: any) => ({
				slot_id: c.slot_id,
				count: 1 + (c.losers?.length || 0),
			}));

			buildReport = {
				pluginsTotal: plugins.length,
				pluginsLoaded: plugins.filter((p: any) => p.status === 'LOADED').length,
				pluginsFailed: plugins.filter((p: any) => p.status === 'FAILED').length,
				commandsRegistered: commands.length,
				contributionsTotal: contributionCount,
				conflicts,
				missingRequired: diagnostics.missing_required || [],
				buildDuration: registryData.build_duration_ms,
			};
		} catch (e) {
			console.error('Failed to fetch diagnostics:', e);
			errors = ['Failed to fetch diagnostics'];
		} finally {
			loading = false;
		}
	});

	const stateColors: Record<string, string> = {
		'ready': 'var(--continuum-accent-success, #3fb950)',
		'degraded': 'var(--continuum-accent-warning, #d29922)',
		'booting': 'var(--continuum-accent-primary, #58a6ff)',
	};

	function formatTimestamp(ts: string): string {
		const date = new Date(ts);
		return date.toLocaleTimeString();
	}
</script>

<div class="diagnostics-panel">
	<header class="panel-header">
		<h3>Diagnostics</h3>
	</header>
	<div class="diagnostics-content">
		{#if loading}
			<div class="loading">Loading diagnostics...</div>
		{:else}
			<!-- Current State -->
			<div class="state-row">
				<span class="state-label">Lifecycle State</span>
				<span
					class="state-value"
					style="color: {stateColors[lifecycleState] || 'inherit'}"
				>
					{lifecycleState.toUpperCase()}
				</span>
			</div>

			<!-- Registry Build Report -->
			{#if buildReport}
				<div class="build-report">
					<h4 class="section-title">Registry Build Report</h4>
					<div class="report-grid">
						<div class="report-item">
							<span class="report-value">{buildReport.pluginsTotal}</span>
							<span class="report-label">Plugins</span>
							<span class="report-detail">
								<span class="loaded">{buildReport.pluginsLoaded} loaded</span>
								{#if buildReport.pluginsFailed > 0}
									<span class="failed">{buildReport.pluginsFailed} failed</span>
								{/if}
							</span>
						</div>
						<div class="report-item">
							<span class="report-value">{buildReport.commandsRegistered}</span>
							<span class="report-label">Commands</span>
						</div>
						<div class="report-item">
							<span class="report-value">{buildReport.contributionsTotal}</span>
							<span class="report-label">Contributions</span>
						</div>
						{#if buildReport.buildDuration}
							<div class="report-item">
								<span class="report-value">{buildReport.buildDuration.toFixed(1)}ms</span>
								<span class="report-label">Build Time</span>
							</div>
						{/if}
					</div>

					{#if buildReport.conflicts.length > 0}
						<div class="report-section warning">
							<h5>Conflicts ({buildReport.conflicts.length})</h5>
							{#each buildReport.conflicts as conflict}
								<div class="conflict-row">
									<code>{conflict.slot_id}</code>
									<span>{conflict.count} contributions</span>
								</div>
							{/each}
						</div>
					{/if}

					{#if buildReport.missingRequired.length > 0}
						<div class="report-section error">
							<h5>Missing Required ({buildReport.missingRequired.length})</h5>
							{#each buildReport.missingRequired as slot}
								<div class="missing-row">
									<code>{slot}</code>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/if}

			<!-- Recent Lifecycle Transitions -->
			{#if transitions.length > 0}
				<div class="transitions-section">
					<h4 class="section-title">Recent Lifecycle Transitions</h4>
					<div class="transitions-list">
						{#each transitions as transition}
							<div class="transition-row">
								<span class="transition-time">{formatTimestamp(transition.timestamp)}</span>
								<span class="transition-states">
									<span style="color: {stateColors[transition.from] || 'inherit'}">{transition.from}</span>
									<span class="transition-arrow">→</span>
									<span style="color: {stateColors[transition.to] || 'inherit'}">{transition.to}</span>
								</span>
								{#if transition.reason}
									<span class="transition-reason">{transition.reason}</span>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Errors -->
			{#if errors.length > 0}
				<div class="issue-section">
					<h4 class="issue-title error">Errors ({errors.length})</h4>
					{#each errors as error}
						<div class="issue-item error">{error}</div>
					{/each}
				</div>
			{/if}

			<!-- Warnings -->
			{#if warnings.length > 0}
				<div class="issue-section">
					<h4 class="issue-title warning">Warnings ({warnings.length})</h4>
					{#each warnings as warning}
						<div class="issue-item warning">{warning}</div>
					{/each}
				</div>
			{/if}

			<!-- All Clear -->
			{#if errors.length === 0 && warnings.length === 0 && buildReport?.conflicts.length === 0 && buildReport?.missingRequired.length === 0}
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

	.diagnostics-content {
		padding: var(--continuum-space-md, 16px);
		max-height: 500px;
		overflow-y: auto;
	}

	.loading {
		text-align: center;
		color: var(--continuum-text-secondary, #a0a0a0);
		padding: var(--continuum-space-lg, 24px);
	}

	.state-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
		margin-bottom: var(--continuum-space-md, 16px);
	}

	.state-label {
		font-size: var(--continuum-font-size-sm, 12px);
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.state-value {
		font-size: var(--continuum-font-size-sm, 12px);
		font-weight: 600;
	}

	.section-title {
		margin: 0 0 var(--continuum-space-sm, 8px);
		font-size: var(--continuum-font-size-sm, 12px);
		font-weight: 600;
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	/* Build Report */
	.build-report {
		margin-bottom: var(--continuum-space-md, 16px);
		padding: var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
	}

	.report-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--continuum-space-sm, 8px);
		margin-bottom: var(--continuum-space-sm, 8px);
	}

	.report-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-secondary, #1a1a2e);
		border-radius: var(--continuum-radius-sm, 4px);
	}

	.report-value {
		font-size: var(--continuum-font-size-lg, 16px);
		font-weight: 700;
		color: var(--continuum-accent-primary, #58a6ff);
	}

	.report-label {
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-secondary, #a0a0a0);
		margin-top: 2px;
	}

	.report-detail {
		font-size: var(--continuum-font-size-xs, 11px);
		margin-top: 2px;
	}

	.report-detail .loaded {
		color: var(--continuum-accent-success, #3fb950);
	}

	.report-detail .failed {
		color: var(--continuum-accent-danger, #f85149);
		margin-left: var(--continuum-space-xs, 4px);
	}

	.report-section {
		padding: var(--continuum-space-sm, 8px);
		border-radius: var(--continuum-radius-sm, 4px);
		margin-top: var(--continuum-space-sm, 8px);
	}

	.report-section.warning {
		background: rgba(210, 153, 34, 0.1);
	}

	.report-section.error {
		background: rgba(248, 81, 73, 0.1);
	}

	.report-section h5 {
		margin: 0 0 var(--continuum-space-xs, 4px);
		font-size: var(--continuum-font-size-xs, 11px);
		font-weight: 600;
	}

	.report-section.warning h5 {
		color: var(--continuum-accent-warning, #d29922);
	}

	.report-section.error h5 {
		color: var(--continuum-accent-danger, #f85149);
	}

	.conflict-row, .missing-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 2px 0;
		font-size: var(--continuum-font-size-xs, 11px);
	}

	.conflict-row code, .missing-row code {
		font-family: var(--continuum-font-mono, monospace);
		color: var(--continuum-text-primary, #e8e8e8);
	}

	.conflict-row span {
		color: var(--continuum-text-muted, #6e6e80);
	}

	/* Transitions */
	.transitions-section {
		margin-bottom: var(--continuum-space-md, 16px);
	}

	.transitions-list {
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
		overflow: hidden;
	}

	.transition-row {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-sm, 8px);
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		font-size: var(--continuum-font-size-xs, 11px);
		border-bottom: 1px solid var(--continuum-border, #2d2d44);
	}

	.transition-row:last-child {
		border-bottom: none;
	}

	.transition-time {
		color: var(--continuum-text-muted, #6e6e80);
		min-width: 70px;
	}

	.transition-states {
		display: flex;
		align-items: center;
		gap: 4px;
		font-weight: 600;
	}

	.transition-arrow {
		color: var(--continuum-text-muted, #6e6e80);
	}

	.transition-reason {
		color: var(--continuum-text-secondary, #a0a0a0);
		font-style: italic;
	}

	/* Issues */
	.issue-section {
		margin-bottom: var(--continuum-space-md, 16px);
	}

	.issue-title {
		margin: 0 0 var(--continuum-space-sm, 8px);
		font-size: var(--continuum-font-size-sm, 12px);
		font-weight: 600;
	}

	.issue-title.error {
		color: var(--continuum-accent-danger, #f85149);
	}

	.issue-title.warning {
		color: var(--continuum-accent-warning, #d29922);
	}

	.issue-item {
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		font-size: var(--continuum-font-size-xs, 11px);
		border-radius: var(--continuum-radius-sm, 4px);
		margin-bottom: var(--continuum-space-xs, 4px);
	}

	.issue-item.error {
		background: rgba(248, 81, 73, 0.1);
		color: var(--continuum-accent-danger, #f85149);
	}

	.issue-item.warning {
		background: rgba(210, 153, 34, 0.1);
		color: var(--continuum-accent-warning, #d29922);
	}

	/* All Clear */
	.all-clear {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: var(--continuum-space-md, 16px);
		color: var(--continuum-accent-success, #3fb950);
	}

	.all-clear span {
		font-size: 20px;
	}

	.all-clear p {
		margin: var(--continuum-space-xs, 4px) 0 0;
		font-size: var(--continuum-font-size-sm, 12px);
	}
</style>

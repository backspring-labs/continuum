<svelte:options customElement="continuum-sample-systems-registry" />

<script lang="ts">
	import { onMount } from 'svelte';

	interface Contribution {
		type: string;
		plugin_id: string;
		priority?: number;
		component?: string;
		label?: string;
		id?: string;
		perspective?: string;
	}

	interface Conflict {
		slot_id: string;
		winner: { plugin_id: string; priority: number; discovery_index: number };
		losers: Array<{ plugin_id: string; priority: number; discovery_index: number }>;
	}

	interface Perspective {
		id: string;
		label: string;
	}

	let perspectives = $state<Perspective[]>([]);
	let regions = $state<Record<string, Contribution[]>>({});
	let conflicts = $state<Conflict[]>([]);
	let missingRequired = $state<string[]>([]);
	let fingerprint = $state('');
	let loading = $state(true);
	let expandedSlots = $state<Set<string>>(new Set());

	onMount(async () => {
		try {
			const res = await fetch('/api/registry');
			const data = await res.json();
			fingerprint = data.registry_fingerprint;
			perspectives = data.perspectives || [];
			regions = data.regions || {};
			conflicts = data.diagnostics?.conflicts || [];
			missingRequired = data.diagnostics?.missing_required || [];
		} catch (e) {
			console.error('Failed to fetch registry:', e);
		} finally {
			loading = false;
		}
	});

	function toggleSlot(slotId: string) {
		const newSet = new Set(expandedSlots);
		if (newSet.has(slotId)) {
			newSet.delete(slotId);
		} else {
			newSet.add(slotId);
		}
		expandedSlots = newSet;
	}

	function hasConflict(slotId: string): boolean {
		return conflicts.some(c => c.slot_id === slotId);
	}

	function getConflict(slotId: string): Conflict | undefined {
		return conflicts.find(c => c.slot_id === slotId);
	}

	function isMissing(slotId: string): boolean {
		return missingRequired.includes(slotId);
	}

	const slotsByPerspective = $derived(() => {
		const result: Record<string, string[]> = { global: [] };

		for (const perspective of perspectives) {
			result[perspective.id] = [];
		}

		for (const [slotId, contributions] of Object.entries(regions)) {
			const perspectiveScopes = contributions
				.map(c => c.perspective)
				.filter((p): p is string => p !== undefined);

			if (perspectiveScopes.length > 0) {
				for (const scope of new Set(perspectiveScopes)) {
					if (!result[scope]) result[scope] = [];
					if (!result[scope].includes(slotId)) {
						result[scope].push(slotId);
					}
				}
			} else {
				if (!result.global.includes(slotId)) {
					result.global.push(slotId);
				}
			}
		}

		return result;
	});
</script>

<div class="registry-panel">
	<header class="panel-header">
		<h3>Registry Inspector</h3>
		<code class="fingerprint" title="Registry fingerprint">{fingerprint}</code>
	</header>

	<div class="registry-content">
		{#if loading}
			<div class="loading">Loading registry...</div>
		{:else}
			{#if missingRequired.length > 0}
				<div class="missing-section">
					<h4 class="section-title error">Missing Required Slots</h4>
					{#each missingRequired as slotId}
						<div class="missing-slot">{slotId}</div>
					{/each}
				</div>
			{/if}

			{#if conflicts.length > 0}
				<div class="conflicts-section">
					<h4 class="section-title warning">Conflicts ({conflicts.length})</h4>
					{#each conflicts as conflict}
						<div class="conflict-item">
							<code class="conflict-slot">{conflict.slot_id}</code>
							<div class="conflict-detail">
								<span class="winner">Winner: {conflict.winner.plugin_id} (priority {conflict.winner.priority})</span>
								<span class="losers">Displaced: {conflict.losers.map(l => l.plugin_id).join(', ')}</span>
							</div>
						</div>
					{/each}
				</div>
			{/if}

			<div class="tree-view">
				<!-- Global slots -->
				<div class="tree-section">
					<h4 class="section-title">Global Slots</h4>
					{#each slotsByPerspective().global as slotId}
						{@const contributions = regions[slotId] || []}
						{@const isExpanded = expandedSlots.has(slotId)}
						<div class="slot-node" class:has-conflict={hasConflict(slotId)} class:missing={isMissing(slotId)}>
							<button class="slot-header" onclick={() => toggleSlot(slotId)}>
								<span class="expand-icon">{isExpanded ? '▼' : '▶'}</span>
								<code class="slot-id">{slotId}</code>
								<span class="slot-count">{contributions.length}</span>
								{#if hasConflict(slotId)}
									<span class="conflict-badge">conflict</span>
								{/if}
							</button>
							{#if isExpanded}
								<div class="contributions-list">
									{#each contributions as contrib, i}
										{@const conflict = getConflict(slotId)}
										{@const isWinner = conflict && i === 0}
										{@const isLoser = conflict && i > 0}
										<div class="contribution-item" class:winner={isWinner} class:loser={isLoser}>
											<div class="contrib-main">
												<span class="contrib-component">{contrib.component || contrib.label || contrib.id || 'unknown'}</span>
												<span class="contrib-plugin">{contrib.plugin_id}</span>
											</div>
											<div class="contrib-meta">
												<span class="contrib-priority">priority: {contrib.priority ?? 100}</span>
												<span class="contrib-type">{contrib.type}</span>
											</div>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{/each}
				</div>

				<!-- Perspective-scoped slots -->
				{#each perspectives as perspective}
					{@const slots = slotsByPerspective()[perspective.id] || []}
					{#if slots.length > 0}
						<div class="tree-section">
							<h4 class="section-title">{perspective.label} Perspective</h4>
							{#each slots as slotId}
								{@const contributions = (regions[slotId] || []).filter(c => c.perspective === perspective.id)}
								{@const isExpanded = expandedSlots.has(`${perspective.id}:${slotId}`)}
								<div class="slot-node">
									<button class="slot-header" onclick={() => toggleSlot(`${perspective.id}:${slotId}`)}>
										<span class="expand-icon">{isExpanded ? '▼' : '▶'}</span>
										<code class="slot-id">{slotId}</code>
										<span class="slot-count">{contributions.length}</span>
									</button>
									{#if isExpanded}
										<div class="contributions-list">
											{#each contributions as contrib}
												<div class="contribution-item">
													<div class="contrib-main">
														<span class="contrib-component">{contrib.component || contrib.label || 'unknown'}</span>
														<span class="contrib-plugin">{contrib.plugin_id}</span>
													</div>
													<div class="contrib-meta">
														<span class="contrib-priority">priority: {contrib.priority ?? 100}</span>
													</div>
												</div>
											{/each}
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.registry-panel {
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

	.fingerprint {
		font-size: var(--continuum-font-size-xs, 11px);
		padding: 2px 6px;
		background: var(--continuum-bg-hover, #252538);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.registry-content {
		padding: var(--continuum-space-md, 16px);
		max-height: 500px;
		overflow-y: auto;
	}

	.loading {
		text-align: center;
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.missing-section, .conflicts-section {
		margin-bottom: var(--continuum-space-md, 16px);
		padding: var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
	}

	.section-title {
		margin: 0 0 var(--continuum-space-sm, 8px);
		font-size: var(--continuum-font-size-sm, 12px);
		font-weight: 600;
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.section-title.error {
		color: var(--continuum-accent-danger, #f85149);
	}

	.section-title.warning {
		color: var(--continuum-accent-warning, #d29922);
	}

	.missing-slot {
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		font-size: var(--continuum-font-size-xs, 11px);
		font-family: var(--continuum-font-mono, monospace);
		background: rgba(248, 81, 73, 0.1);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-accent-danger, #f85149);
		margin-bottom: var(--continuum-space-xs, 4px);
	}

	.conflict-item {
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		background: rgba(210, 153, 34, 0.1);
		border-radius: var(--continuum-radius-sm, 4px);
		margin-bottom: var(--continuum-space-xs, 4px);
	}

	.conflict-slot {
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-accent-warning, #d29922);
	}

	.conflict-detail {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-top: 4px;
		font-size: var(--continuum-font-size-xs, 11px);
	}

	.winner {
		color: var(--continuum-accent-success, #3fb950);
	}

	.losers {
		color: var(--continuum-text-muted, #6e6e80);
	}

	.tree-view {
		margin-top: var(--continuum-space-sm, 8px);
	}

	.tree-section {
		margin-bottom: var(--continuum-space-md, 16px);
	}

	.slot-node {
		margin-bottom: var(--continuum-space-xs, 4px);
	}

	.slot-node.has-conflict {
		border-left: 2px solid var(--continuum-accent-warning, #d29922);
	}

	.slot-node.missing {
		border-left: 2px solid var(--continuum-accent-danger, #f85149);
	}

	.slot-header {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-sm, 8px);
		width: 100%;
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-tertiary, #12121f);
		border: none;
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-text-primary, #e8e8e8);
		cursor: pointer;
		text-align: left;
	}

	.slot-header:hover {
		background: var(--continuum-bg-hover, #252538);
	}

	.expand-icon {
		width: 12px;
		font-size: 10px;
		color: var(--continuum-text-muted, #6e6e80);
	}

	.slot-id {
		flex: 1;
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-accent-primary, #58a6ff);
	}

	.slot-count {
		padding: 1px 6px;
		background: var(--continuum-bg-hover, #252538);
		border-radius: 8px;
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.conflict-badge {
		padding: 1px 6px;
		background: var(--continuum-accent-warning, #d29922);
		border-radius: 8px;
		font-size: var(--continuum-font-size-xs, 11px);
		color: black;
		text-transform: uppercase;
	}

	.contributions-list {
		margin-left: 20px;
		padding: var(--continuum-space-xs, 4px) 0;
	}

	.contribution-item {
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		margin-bottom: 2px;
		background: var(--continuum-bg-secondary, #1a1a2e);
		border-radius: var(--continuum-radius-sm, 4px);
		border-left: 2px solid transparent;
	}

	.contribution-item.winner {
		border-left-color: var(--continuum-accent-success, #3fb950);
	}

	.contribution-item.loser {
		opacity: 0.5;
		border-left-color: var(--continuum-accent-danger, #f85149);
	}

	.contrib-main {
		display: flex;
		justify-content: space-between;
		font-size: var(--continuum-font-size-xs, 11px);
	}

	.contrib-component {
		font-family: var(--continuum-font-mono, monospace);
		color: var(--continuum-text-primary, #e8e8e8);
	}

	.contrib-plugin {
		color: var(--continuum-text-muted, #6e6e80);
	}

	.contrib-meta {
		display: flex;
		gap: var(--continuum-space-sm, 8px);
		font-size: 10px;
		color: var(--continuum-text-muted, #6e6e80);
		margin-top: 2px;
	}

	.contrib-priority {
		color: var(--continuum-accent-primary, #58a6ff);
	}
</style>

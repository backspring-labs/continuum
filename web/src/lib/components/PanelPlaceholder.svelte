<script lang="ts">
	import type { Contribution } from '$stores/registry';

	interface Props {
		contribution: Contribution;
	}

	let { contribution }: Props = $props();
</script>

<div class="panel-placeholder">
	<div class="placeholder-header">
		<span class="component-tag">&lt;{contribution.component ?? 'unknown'}&gt;</span>
		<span class="plugin-id">{contribution.plugin_id}</span>
	</div>
	<div class="placeholder-body">
		<p>Web Component not loaded</p>
		<p class="hint">Component will render here once plugin UI is built</p>
	</div>
	<div class="placeholder-meta">
		<span>Priority: {contribution.priority ?? 100}</span>
		{#if contribution.perspective}
			<span>Perspective: {contribution.perspective}</span>
		{/if}
	</div>
</div>

<style>
	.panel-placeholder {
		background: var(--continuum-bg-secondary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		overflow: hidden;
	}

	.placeholder-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-bg-tertiary);
		border-bottom: 1px solid var(--continuum-border);
	}

	.component-tag {
		font-family: var(--continuum-font-mono);
		font-size: var(--continuum-font-size-sm);
		color: var(--continuum-accent-primary);
	}

	.plugin-id {
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
	}

	.placeholder-body {
		padding: var(--continuum-space-lg);
		text-align: center;
	}

	.placeholder-body p {
		margin: 0;
		color: var(--continuum-text-secondary);
	}

	.hint {
		font-size: var(--continuum-font-size-sm);
		color: var(--continuum-text-muted);
		margin-top: var(--continuum-space-sm) !important;
	}

	.placeholder-meta {
		display: flex;
		gap: var(--continuum-space-md);
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-bg-tertiary);
		border-top: 1px solid var(--continuum-border);
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
	}
</style>

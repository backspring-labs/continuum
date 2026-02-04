<script lang="ts">
	import type { Contribution } from '$stores/registry';
	import { getComponent } from './plugins';
	import PanelPlaceholder from './PanelPlaceholder.svelte';

	interface Props {
		slotId: string;
		contributions: Contribution[];
	}

	let { slotId, contributions }: Props = $props();
</script>

<div class="region-slot" data-slot={slotId}>
	{#each contributions as contribution (contribution.plugin_id + '-' + (contribution.component ?? contribution.id))}
		{@const Component = contribution.component ? getComponent(contribution.component) : undefined}
		{#if Component}
			<div class="contribution" data-plugin={contribution.plugin_id}>
				<Component />
			</div>
		{:else}
			<PanelPlaceholder {contribution} />
		{/if}
	{/each}

	{#if contributions.length === 0}
		<div class="empty-slot">
			<span class="empty-label">No contributions for {slotId}</span>
		</div>
	{/if}
</div>

<style>
	.region-slot {
		display: flex;
		flex-direction: column;
		gap: var(--continuum-space-md);
	}

	.contribution {
		display: block;
	}

	.empty-slot {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--continuum-space-xl);
		background: var(--continuum-bg-secondary);
		border: 1px dashed var(--continuum-border);
		border-radius: var(--continuum-radius-md);
	}

	.empty-label {
		color: var(--continuum-text-muted);
		font-size: var(--continuum-font-size-sm);
	}
</style>

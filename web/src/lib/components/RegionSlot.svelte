<script lang="ts">
	import type { Contribution } from '$stores/registry';
	import ComponentLoader from './ComponentLoader.svelte';
	import { preloadBundles } from '$lib/services/pluginLoader';

	interface Props {
		slotId: string;
		contributions: Contribution[];
	}

	let { slotId, contributions }: Props = $props();

	// Preload all bundles for this slot when contributions change
	$effect(() => {
		const bundleUrls = new Set<string>();
		for (const contribution of contributions) {
			if (contribution.bundle_url) {
				bundleUrls.add(contribution.bundle_url);
			}
		}
		if (bundleUrls.size > 0) {
			preloadBundles(bundleUrls);
		}
	});
</script>

<div class="region-slot" data-slot={slotId}>
	{#each contributions as contribution (contribution.plugin_id + '-' + (contribution.component ?? contribution.id))}
		<ComponentLoader {contribution} />
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

	.empty-slot {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--continuum-space-xl);
		background: var(--continuum-bg-tertiary);
		border: 1px dashed var(--continuum-border);
		border-radius: var(--continuum-radius-md);
	}

	.empty-label {
		color: var(--continuum-text-muted);
		font-size: var(--continuum-font-size-sm);
	}
</style>

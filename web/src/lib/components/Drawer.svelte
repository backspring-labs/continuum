<script lang="ts">
	import type { Contribution } from '$stores/registry';
	import ComponentLoader from './ComponentLoader.svelte';
	import { loadBundle } from '$lib/services/pluginLoader';

	interface Props {
		contribution: Contribution;
		onClose: () => void;
	}

	let { contribution, onClose }: Props = $props();

	let width = $derived(contribution.width ?? '400px');

	// Preload bundle when drawer opens
	$effect(() => {
		if (contribution.bundle_url) {
			loadBundle(contribution.bundle_url).catch(() => {
				// Error handled by ComponentLoader
			});
		}
	});

	function handleOverlayClick() {
		onClose();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="drawer-overlay" role="button" tabindex="-1" onclick={handleOverlayClick} onkeydown={(e) => e.key === 'Enter' && handleOverlayClick()}>
	<div
		class="drawer"
		style="width: {width}"
		onclick={(e) => e.stopPropagation()}
		onkeydown={(e) => e.stopPropagation()}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<header class="drawer-header">
			<h2>{contribution.title ?? contribution.id}</h2>
			<button class="close-btn" onclick={onClose}>\u00d7</button>
		</header>
		<div class="drawer-content">
			<ComponentLoader {contribution} />
		</div>
	</div>
</div>

<style>
	.drawer-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.3);
		z-index: 900;
	}

	.drawer {
		position: fixed;
		top: 0;
		right: 0;
		height: 100vh;
		background: var(--continuum-bg-secondary);
		border-left: 1px solid var(--continuum-border);
		box-shadow: var(--continuum-shadow-lg);
		display: flex;
		flex-direction: column;
		animation: slideIn 200ms ease;
	}

	@keyframes slideIn {
		from {
			transform: translateX(100%);
		}
		to {
			transform: translateX(0);
		}
	}

	.drawer-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--continuum-space-md);
		border-bottom: 1px solid var(--continuum-border);
	}

	.drawer-header h2 {
		margin: 0;
		font-size: var(--continuum-font-size-lg);
		font-weight: 600;
	}

	.close-btn {
		padding: var(--continuum-space-xs) var(--continuum-space-sm);
		background: transparent;
		border: none;
		color: var(--continuum-text-secondary);
		font-size: var(--continuum-font-size-xl);
		cursor: pointer;
	}

	.close-btn:hover {
		color: var(--continuum-text-primary);
	}

	.drawer-content {
		flex: 1;
		overflow-y: auto;
	}
</style>

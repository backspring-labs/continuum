<script lang="ts">
	import type { Contribution } from '$stores/registry';
	import { getComponent } from './plugins';

	interface Props {
		contribution: Contribution;
		onClose: () => void;
	}

	let { contribution, onClose }: Props = $props();

	const width = contribution.width ?? '400px';
	const Component = contribution.component ? getComponent(contribution.component) : undefined;

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

<div class="drawer-overlay" onclick={handleOverlayClick}>
	<aside
		class="drawer"
		style="width: {width}"
		onclick={(e) => e.stopPropagation()}
	>
		<header class="drawer-header">
			<h2>{contribution.title ?? contribution.id}</h2>
			<button class="close-btn" onclick={onClose}>×</button>
		</header>
		<div class="drawer-content">
			{#if Component}
				<Component />
			{:else}
				<div class="placeholder">
					<p class="tag">&lt;{contribution.component}&gt;</p>
					<p>Drawer component not loaded</p>
					<p class="meta">Plugin: {contribution.plugin_id}</p>
				</div>
			{/if}
		</div>
	</aside>
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

	.placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 200px;
		text-align: center;
		color: var(--continuum-text-secondary);
	}

	.placeholder .tag {
		font-family: var(--continuum-font-mono);
		color: var(--continuum-accent-primary);
	}

	.placeholder .meta {
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
	}
</style>

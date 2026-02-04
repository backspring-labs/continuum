<script lang="ts">
	import type { Contribution } from '$stores/registry';

	interface Props {
		item: Contribution;
		active?: boolean;
		onAction: () => void;
	}

	let { item, active = false, onAction }: Props = $props();

	// SVG icon paths for each icon name
	const iconPaths: Record<string, string> = {
		'activity': 'M22 12h-4l-3 9L9 3l-3 9H2',
		'search': 'M11 11m-8 0a8 8 0 1 0 16 0a8 8 0 1 0-16 0M21 21l-4.35-4.35',
		'clock': 'M12 12m-10 0a10 10 0 1 0 20 0a10 10 0 1 0-20 0M12 6v6l4 2',
		'compass': 'M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21L12 17.77L5.82 21L7 14.14l-5-4.87l6.91-1.01L12 2',
		'settings': 'M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z',
		'terminal': 'M4 17l6-6-6-6M12 19h8',
		'message-circle': 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
	};

	function getIconPath(iconName?: string): string {
		return iconName ? (iconPaths[iconName] ?? '') : '';
	}
</script>

<button
	class="nav-item"
	class:active
	onclick={onAction}
>
	{#if item.icon && iconPaths[item.icon]}
		<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<path d={getIconPath(item.icon)}/>
		</svg>
	{:else}
		<span class="icon-fallback">•</span>
	{/if}
	<span class="nav-tooltip">{item.label}</span>
</button>

<style>
	.nav-item {
		width: 44px;
		height: 44px;
		border-radius: var(--continuum-radius-md);
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.15s;
		color: var(--continuum-text-secondary);
		background: transparent;
		border: none;
		position: relative;
	}

	.nav-item:hover {
		background: var(--continuum-bg-hover);
		color: var(--continuum-text-primary);
	}

	.nav-item.active {
		background: var(--continuum-accent-primary);
		color: var(--continuum-bg-primary);
	}

	.nav-item.active::before {
		content: '';
		position: absolute;
		left: -10px;
		top: 50%;
		transform: translateY(-50%);
		width: 3px;
		height: 20px;
		background: var(--continuum-accent-primary);
		border-radius: 0 2px 2px 0;
	}

	.nav-item svg {
		width: 22px;
		height: 22px;
	}

	.icon-fallback {
		font-size: 20px;
	}

	.nav-tooltip {
		position: absolute;
		left: 100%;
		top: 50%;
		transform: translateY(-50%);
		background: var(--continuum-bg-tertiary);
		border: 1px solid var(--continuum-border);
		padding: 6px 10px;
		border-radius: var(--continuum-radius-sm);
		font-size: 12px;
		white-space: nowrap;
		opacity: 0;
		pointer-events: none;
		transition: opacity 0.15s;
		margin-left: 8px;
		z-index: 100;
		color: var(--continuum-text-primary);
	}

	.nav-item:hover .nav-tooltip {
		opacity: 1;
	}
</style>

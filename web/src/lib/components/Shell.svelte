<script lang="ts">
	import { onMount } from 'svelte';
	import {
		fetchRegistry,
		registryLoading,
		registryError,
		registry,
		activePerspective,
		perspectives,
		leftNav,
		mainPanels,
		rightRailPanels,
		drawerContributions,
		commands,
		setPerspective,
		type Contribution
	} from '$stores/registry';
	import RegionSlot from './RegionSlot.svelte';
	import NavItem from './NavItem.svelte';
	import CommandPalette from './CommandPalette.svelte';
	import Drawer from './Drawer.svelte';
	import ConfirmDialog from './ConfirmDialog.svelte';

	let showCommandPalette = false;
	let showLogoutDialog = false;
	let showDecorators = false;
	let activeDrawer: Contribution | null = null;

	onMount(() => {
		fetchRegistry();

		// Keyboard shortcuts
		function handleKeydown(e: KeyboardEvent) {
			if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
				e.preventDefault();
				showCommandPalette = !showCommandPalette;
			}
			if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
				e.preventDefault();
				showDecorators = true;
			}
			if (e.key === 'Escape') {
				showCommandPalette = false;
				activeDrawer = null;
			}
		}
		function handleKeyup(e: KeyboardEvent) {
			if (e.key === 'd' || e.key === 'Meta' || e.key === 'Control') {
				showDecorators = false;
			}
		}
		window.addEventListener('keydown', handleKeydown);
		window.addEventListener('keyup', handleKeyup);
		return () => {
			window.removeEventListener('keydown', handleKeydown);
			window.removeEventListener('keyup', handleKeyup);
		};
	});

	function handleNavAction(target: Contribution['target']) {
		if (!target) return;

		switch (target.type) {
			case 'panel':
				if (target.panel_id) {
					setPerspective(target.panel_id);
				}
				break;
			case 'command':
				if (target.command_id === 'open_command_palette') {
					showCommandPalette = true;
				}
				break;
			case 'drawer':
				const drawer = $drawerContributions.find(d => d.id === target.drawer_id);
				if (drawer) {
					activeDrawer = activeDrawer?.id === drawer.id ? null : drawer;
				}
				break;
		}
	}

	function toggleDrawer() {
		// Toggle the first available drawer (settings drawer in V1)
		const settingsDrawer = $drawerContributions.find(d => d.id === 'settings_drawer');
		if (settingsDrawer) {
			activeDrawer = activeDrawer?.id === settingsDrawer.id ? null : settingsDrawer;
		}
	}
</script>

{#if $registryLoading}
	<div class="loading">
		<div class="spinner"></div>
		<p>Loading Continuum...</p>
	</div>
{:else if $registryError}
	<div class="error">
		<h2>Failed to load</h2>
		<p>{$registryError}</p>
		<button onclick={() => fetchRegistry()}>Retry</button>
	</div>
{:else}
	<div class="shell" class:decorators={showDecorators}>
		<!-- Main layout -->
		<div class="layout">
			<!-- Left Nav -->
			<nav class="left-nav">
				<div class="nav-logo">
					<span class="logo-text">C</span>
				</div>
				<div class="nav-section">
		{#each $leftNav.filter(n => n.target?.type === 'panel') as item}
						<NavItem
							{item}
							active={item.target?.panel_id === $activePerspective}
							onAction={() => handleNavAction(item.target)}
						/>
					{/each}
				</div>
				<div class="nav-spacer"></div>
				<div class="nav-section">
					{#each $leftNav.filter(n => n.target?.type !== 'panel') as item}
						<NavItem
							{item}
							active={item.target?.type === 'drawer' && activeDrawer?.id === item.target?.drawer_id}
							onAction={() => handleNavAction(item.target)}
						/>
					{/each}
				</div>
				<button
					class="logout-btn"
					onclick={() => showLogoutDialog = true}
				>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
					</svg>
					<span class="logout-tooltip">Log Out</span>
				</button>
			</nav>

			<!-- Main content -->
			<main class="main">
				<RegionSlot slotId="ui.slot.main" contributions={$mainPanels} />
			</main>

			<!-- Right rail -->
			{#if $rightRailPanels.length > 0}
				<aside class="right-rail">
					<RegionSlot slotId="ui.slot.right_rail" contributions={$rightRailPanels} />
				</aside>
			{/if}
		</div>

		<!-- Footer -->
		<footer class="footer">
			<div class="footer-left">
				<span>Plugins: {$registry?.plugins.length ?? 0}</span>
				<span>Fingerprint: {$registry?.registry_fingerprint ?? ''}</span>
			</div>
			<div class="footer-right">
				<span class="system-status" class:ready={$registry?.lifecycle_state === 'ready'} class:degraded={$registry?.lifecycle_state === 'degraded'}>
					<span class="status-dot"></span>
					System Status
				</span>
			</div>
		</footer>

		<!-- Overlays -->
		{#if showCommandPalette}
			<CommandPalette
				commands={$commands}
				onClose={() => showCommandPalette = false}
				onToggleDrawer={toggleDrawer}
			/>
		{/if}

		{#if activeDrawer}
			<Drawer
				contribution={activeDrawer}
				onClose={() => activeDrawer = null}
			/>
		{/if}

		{#if showLogoutDialog}
			<ConfirmDialog
				title="Log Out"
				message="Are you sure you want to log out?"
				dangerLevel="confirm"
				confirmLabel="Log Out"
				onConfirm={() => showLogoutDialog = false}
				onCancel={() => showLogoutDialog = false}
			/>
		{/if}
	</div>
{/if}

<style>
	.loading, .error {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100vh;
		gap: var(--continuum-space-md);
	}

	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid var(--continuum-border);
		border-top-color: var(--continuum-accent-primary);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error button {
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-accent-primary);
		color: white;
		border: none;
		border-radius: var(--continuum-radius-md);
	}

	.shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow: hidden;
	}

	.nav-logo {
		width: 40px;
		height: 40px;
		background: linear-gradient(135deg, var(--continuum-accent-primary) 0%, #a855f7 100%);
		border-radius: var(--continuum-radius-md);
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: var(--continuum-space-md);
	}

	.logo-text {
		color: white;
		font-weight: 700;
		font-size: var(--continuum-font-size-lg);
	}

	.system-status {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
	}

	.status-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--continuum-text-muted);
	}

	.system-status.ready .status-dot {
		background: var(--continuum-accent-success);
	}

	.system-status.degraded .status-dot {
		background: var(--continuum-accent-warning, #f59e0b);
	}

	.layout {
		display: flex;
		flex: 1;
		overflow: hidden;
		padding: var(--continuum-space-sm);
		gap: var(--continuum-space-sm);
	}

	.left-nav {
		width: var(--continuum-nav-width);
		background: var(--continuum-bg-secondary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-lg);
		overflow-x: hidden;
		overflow-y: auto;
		padding: var(--continuum-space-sm);
		display: flex;
		flex-direction: column;
		align-items: center;
	}


	.nav-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--continuum-space-xs);
	}

	.nav-section-label {
		font-size: 9px;
		color: var(--continuum-text-muted);
		text-transform: uppercase;
		letter-spacing: 1px;
		margin-bottom: var(--continuum-space-xs);
	}

	.nav-spacer {
		flex: 1;
		min-height: var(--continuum-space-lg);
	}

	.logout-btn {
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
		margin-top: var(--continuum-space-sm);
	}

	.logout-btn:hover {
		background: var(--continuum-bg-hover);
		color: var(--continuum-text-primary);
	}

	.logout-btn svg {
		width: 22px;
		height: 22px;
	}

	.logout-tooltip {
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

	.logout-btn:hover .logout-tooltip {
		opacity: 1;
	}

	.main {
		flex: 1;
		overflow-y: auto;
		padding: 0 var(--continuum-space-sm) var(--continuum-space-sm);
	}

	.right-rail {
		width: var(--continuum-rail-width);
		overflow-y: auto;
		padding: 0 var(--continuum-space-sm) var(--continuum-space-sm);
	}

	.footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: var(--continuum-footer-height);
		padding: 0 var(--continuum-space-md);
		background: var(--continuum-bg-secondary);
		border-top: 1px solid var(--continuum-border);
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
	}

	.footer-left {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-md);
	}

	.footer-right {
		display: flex;
		align-items: center;
	}

	/* Design decorators (Cmd+D) */
	.shell.decorators .left-nav,
	.shell.decorators .main,
	.shell.decorators .right-rail,
	.shell.decorators .footer {
		position: relative;
		outline: 1px solid var(--continuum-accent-primary);
		outline-offset: -1px;
	}

	.shell.decorators .left-nav::after,
	.shell.decorators .main::after,
	.shell.decorators .right-rail::after,
	.shell.decorators .footer::after {
		position: absolute;
		top: 4px;
		left: 4px;
		padding: 2px 6px;
		background: var(--continuum-accent-primary);
		color: white;
		font-size: 10px;
		font-family: var(--continuum-font-mono);
		border-radius: var(--continuum-radius-sm);
		z-index: 1000;
		pointer-events: none;
		opacity: 0.9;
	}

	.shell.decorators .left-nav::after { content: 'ui.slot.left_nav'; }
	.shell.decorators .main::after { content: 'ui.slot.main'; }
	.shell.decorators .right-rail::after { content: 'ui.slot.right_rail'; }
	.shell.decorators .footer::after { content: 'ui.slot.footer'; }

	.shell.decorators :global([data-slot]) {
		position: relative;
	}

	.shell.decorators :global([data-slot] > *) {
		outline: 1px dashed var(--continuum-accent-warning, #f59e0b);
		outline-offset: -1px;
		position: relative;
	}
</style>

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

	let showCommandPalette = false;
	let activeDrawer: Contribution | null = null;

	onMount(() => {
		fetchRegistry();

		// Keyboard shortcuts
		function handleKeydown(e: KeyboardEvent) {
			if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
				e.preventDefault();
				showCommandPalette = !showCommandPalette;
			}
			if (e.key === 'Escape') {
				showCommandPalette = false;
				activeDrawer = null;
			}
		}
		window.addEventListener('keydown', handleKeydown);
		return () => window.removeEventListener('keydown', handleKeydown);
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
	<div class="shell">
		<!-- Header -->
		<header class="header">
			<div class="header-left">
				<span class="logo">Continuum</span>
				<span class="perspective-label">{$perspectives.find(p => p.id === $activePerspective)?.label ?? ''}</span>
			</div>
			<div class="header-center">
				<button class="search-trigger" onclick={() => showCommandPalette = true}>
					<span class="search-icon">⌘</span>
					<span>Search or run command...</span>
					<kbd>⌘K</kbd>
				</button>
			</div>
			<div class="header-right">
				<span class="status" class:ready={$registry?.lifecycle_state === 'ready'}>
					{$registry?.lifecycle_state}
				</span>
			</div>
		</header>

		<!-- Main layout -->
		<div class="layout">
			<!-- Left Nav -->
			<nav class="left-nav">
				<div class="nav-logo">
					<span class="logo-text">C</span>
				</div>
				<div class="nav-section">
					<div class="nav-section-label">Views</div>
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
					<div class="nav-section-label">Actions</div>
					{#each $leftNav.filter(n => n.target?.type !== 'panel') as item}
						<NavItem
							{item}
							active={item.target?.type === 'drawer' && activeDrawer?.id === item.target?.drawer_id}
							onAction={() => handleNavAction(item.target)}
						/>
					{/each}
				</div>
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
			<span>Plugins: {$registry?.plugins.length ?? 0}</span>
			<span>Fingerprint: {$registry?.registry_fingerprint ?? ''}</span>
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

	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: var(--continuum-header-height);
		padding: 0 var(--continuum-space-md);
		background: var(--continuum-bg-secondary);
		border-bottom: 1px solid var(--continuum-border);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-md);
	}

	.logo {
		font-weight: 600;
		font-size: var(--continuum-font-size-lg);
	}

	.perspective-label {
		color: var(--continuum-text-secondary);
		font-size: var(--continuum-font-size-sm);
	}

	.header-center {
		flex: 1;
		display: flex;
		justify-content: center;
	}

	.search-trigger {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-sm);
		padding: var(--continuum-space-xs) var(--continuum-space-md);
		background: var(--continuum-bg-tertiary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		color: var(--continuum-text-secondary);
		min-width: 300px;
	}

	.search-trigger:hover {
		border-color: var(--continuum-text-muted);
	}

	.search-trigger kbd {
		margin-left: auto;
		padding: 2px 6px;
		background: var(--continuum-bg-hover);
		border-radius: var(--continuum-radius-sm);
		font-size: var(--continuum-font-size-xs);
	}

	.header-right {
		display: flex;
		align-items: center;
	}

	.status {
		padding: 2px 8px;
		background: var(--continuum-bg-tertiary);
		border-radius: var(--continuum-radius-sm);
		font-size: var(--continuum-font-size-xs);
		text-transform: uppercase;
	}

	.status.ready {
		background: var(--continuum-accent-success);
		color: white;
	}

	.layout {
		display: flex;
		flex: 1;
		overflow: hidden;
	}

	.left-nav {
		width: var(--continuum-nav-width);
		background: var(--continuum-bg-secondary);
		border-right: 1px solid var(--continuum-border);
		overflow-y: auto;
		padding: var(--continuum-space-sm);
		display: flex;
		flex-direction: column;
		align-items: center;
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

	.main {
		flex: 1;
		overflow-y: auto;
		padding: var(--continuum-space-md);
	}

	.right-rail {
		width: var(--continuum-rail-width);
		background: var(--continuum-bg-secondary);
		border-left: 1px solid var(--continuum-border);
		overflow-y: auto;
		padding: var(--continuum-space-md);
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
</style>

<script lang="ts">
	import {
		applyTheme,
		savePreference,
		getStoredPreference,
		type ThemeDefinition,
		type ThemePreference
	} from '$lib/services/themeEngine';

	interface Props {
		themes: ThemeDefinition[];
		activeThemeId: string;
		onThemeChange: (themeId: string, preference: ThemePreference) => void;
	}

	let { themes, activeThemeId, onThemeChange }: Props = $props();

	let open = $state(false);

	function currentLabel(): string {
		const pref = getStoredPreference();
		if (pref?.mode === 'system') return 'System';
		const theme = themes.find((t) => t.id === activeThemeId);
		return theme?.name ?? 'Default Dark';
	}

	function handleSelect(themeId: string | 'system') {
		if (themeId === 'system') {
			// Switch to system mode
			const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
			const targetId = prefersLight ? 'light' : 'default-dark';
			const theme = themes.find((t) => t.id === targetId) ?? themes[0];
			if (theme) {
				applyTheme(theme);
				const pref: ThemePreference = { mode: 'system', themeId: theme.id };
				savePreference(pref);
				onThemeChange(theme.id, pref);
			}
		} else {
			const theme = themes.find((t) => t.id === themeId);
			if (theme) {
				applyTheme(theme);
				const pref: ThemePreference = { mode: 'explicit', themeId: theme.id };
				savePreference(pref);
				onThemeChange(theme.id, pref);
			}
		}
		open = false;
	}

	function handleClickOutside(e: MouseEvent) {
		const target = e.target as HTMLElement;
		if (!target.closest('.theme-selector')) {
			open = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			open = false;
		}
	}
</script>

<svelte:window onclick={handleClickOutside} onkeydown={handleKeydown} />

<div class="theme-selector">
	<button class="theme-trigger" onclick={() => (open = !open)} aria-haspopup="listbox" aria-expanded={open}>
		Theme: {currentLabel()}
		<svg class="chevron" class:open viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
			<path d="M3 5l3 3 3-3" />
		</svg>
	</button>

	{#if open}
		<div class="theme-dropdown" role="listbox" aria-label="Theme selection">
			<!-- System option -->
			<button
				class="theme-option"
				class:active={getStoredPreference()?.mode === 'system'}
				role="option"
				aria-selected={getStoredPreference()?.mode === 'system'}
				onclick={() => handleSelect('system')}
			>
				<span class="theme-option-indicator system-indicator">
					<svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
						<circle cx="6" cy="6" r="3" />
						<path d="M6 1v1M6 10v1M1 6h1M10 6h1" />
					</svg>
				</span>
				<span class="theme-option-name">System</span>
				{#if getStoredPreference()?.mode === 'system'}
					<span class="theme-check">&#10003;</span>
				{/if}
			</button>

			<div class="theme-separator"></div>

			<!-- Built-in themes -->
			{#each themes.filter((t) => t.builtin) as theme (theme.id)}
				<button
					class="theme-option"
					class:active={activeThemeId === theme.id && getStoredPreference()?.mode === 'explicit'}
					role="option"
					aria-selected={activeThemeId === theme.id && getStoredPreference()?.mode === 'explicit'}
					onclick={() => handleSelect(theme.id)}
				>
					<span class="theme-option-indicator" class:dark={theme.category === 'dark'} class:light={theme.category === 'light'}></span>
					<span class="theme-option-name">{theme.name}</span>
					{#if theme.tags?.includes('accessibility')}
						<span class="theme-tag">a11y</span>
					{/if}
					{#if activeThemeId === theme.id && getStoredPreference()?.mode === 'explicit'}
						<span class="theme-check">&#10003;</span>
					{/if}
				</button>
			{/each}

			<!-- Plugin-contributed themes -->
			{#if themes.some((t) => !t.builtin)}
				<div class="theme-separator"></div>
				{#each themes.filter((t) => !t.builtin) as theme (theme.id)}
					<button
						class="theme-option"
						class:active={activeThemeId === theme.id && getStoredPreference()?.mode === 'explicit'}
						role="option"
						aria-selected={activeThemeId === theme.id && getStoredPreference()?.mode === 'explicit'}
						onclick={() => handleSelect(theme.id)}
					>
						<span class="theme-option-indicator" class:dark={theme.category === 'dark'} class:light={theme.category === 'light'}></span>
						<span class="theme-option-name">{theme.name}</span>
						{#if activeThemeId === theme.id && getStoredPreference()?.mode === 'explicit'}
							<span class="theme-check">&#10003;</span>
						{/if}
					</button>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<style>
	.theme-selector {
		position: relative;
	}

	.theme-trigger {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 0 8px;
		height: 100%;
		background: none;
		border: none;
		color: var(--continuum-text-muted);
		font-size: var(--continuum-font-size-xs);
		cursor: pointer;
		white-space: nowrap;
	}

	.theme-trigger:hover {
		color: var(--continuum-text-secondary);
	}

	.chevron {
		width: 10px;
		height: 10px;
		transition: transform var(--continuum-transition-fast);
	}

	.chevron.open {
		transform: rotate(180deg);
	}

	.theme-dropdown {
		position: absolute;
		bottom: 100%;
		right: 0;
		margin-bottom: 4px;
		min-width: 180px;
		background: var(--continuum-bg-secondary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		box-shadow: var(--continuum-shadow-md);
		padding: 4px;
		z-index: 1000;
	}

	.theme-option {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 6px 8px;
		background: none;
		border: none;
		color: var(--continuum-text-secondary);
		font-size: var(--continuum-font-size-sm);
		cursor: pointer;
		border-radius: var(--continuum-radius-sm);
		text-align: left;
	}

	.theme-option:hover {
		background: var(--continuum-bg-hover);
		color: var(--continuum-text-primary);
	}

	.theme-option.active {
		color: var(--continuum-text-primary);
	}

	.theme-option-indicator {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.theme-option-indicator.dark {
		background: #6e7681;
		border: 1px solid #8b949e;
	}

	.theme-option-indicator.light {
		background: #e6edf3;
		border: 1px solid #d0d7de;
	}

	.system-indicator {
		width: 12px;
		height: 12px;
		background: none;
		border: none;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--continuum-text-muted);
	}

	.system-indicator svg {
		width: 12px;
		height: 12px;
	}

	.theme-option-name {
		flex: 1;
	}

	.theme-tag {
		font-size: 9px;
		padding: 1px 4px;
		background: var(--continuum-bg-tertiary);
		border-radius: 3px;
		color: var(--continuum-text-muted);
	}

	.theme-check {
		color: var(--continuum-accent-primary);
		font-size: 11px;
	}

	.theme-separator {
		height: 1px;
		background: var(--continuum-border-muted);
		margin: 4px 0;
	}
</style>

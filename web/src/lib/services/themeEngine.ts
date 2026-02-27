/**
 * Theme engine — applies, persists, and restores theme token overrides.
 *
 * Design decisions (incorporated from plan review):
 * 1. Every theme is explicit — no null/implicit "default dark". default-dark is
 *    a real theme with a real ID.
 * 2. Preference is either "system" (follows OS prefers-color-scheme) or an
 *    explicit theme ID. This distinguishes "user chose Light" from "OS chose Light".
 * 3. FOUC prevention: the inline boot script in app.html caches the full token
 *    map in localStorage and restores it before first paint.
 * 4. The continuum:theme-apply custom event is a v1 integration contract for
 *    plugin-initiated theme changes. The footer selector calls applyTheme() directly.
 */

const PREF_KEY = 'continuum-theme-pref';
const TOKENS_CACHE_KEY = 'continuum-theme-tokens';
const STYLE_ID = 'continuum-theme-overrides';

export interface ThemeDefinition {
	id: string;
	name: string;
	description: string;
	category: 'dark' | 'light';
	preview_colors: string[];
	tokens: Record<string, string>;
	tags?: string[];
	plugin_id?: string;
	builtin?: boolean;
}

/**
 * Persisted preference: either "system" (follow OS) or an explicit theme ID.
 */
export interface ThemePreference {
	mode: 'system' | 'explicit';
	themeId: string; // The resolved theme ID (even in system mode, for cache)
}

/**
 * Apply a theme by injecting its token overrides into the document.
 * Also caches the token map in localStorage for FOUC prevention on next load.
 */
export function applyTheme(theme: ThemeDefinition): void {
	const root = document.documentElement;

	// Remove existing overrides
	const existing = document.getElementById(STYLE_ID);
	if (existing) existing.remove();

	// Inject <style> with token overrides
	const style = document.createElement('style');
	style.id = STYLE_ID;
	const rules = Object.entries(theme.tokens)
		.map(([key, value]) => `  ${key}: ${value};`)
		.join('\n');
	style.textContent = `:root {\n${rules}\n}`;
	document.head.appendChild(style);

	root.setAttribute('data-theme', theme.id);

	// Cache tokens for FOUC prevention on next page load
	try {
		localStorage.setItem(TOKENS_CACHE_KEY, JSON.stringify(theme.tokens));
	} catch {
		// localStorage full or unavailable — non-critical
	}
}

/**
 * Save the user's theme preference.
 */
export function savePreference(pref: ThemePreference): void {
	try {
		localStorage.setItem(PREF_KEY, JSON.stringify(pref));
	} catch {
		// non-critical
	}
}

/**
 * Read the stored preference from localStorage.
 */
export function getStoredPreference(): ThemePreference | null {
	try {
		const raw = localStorage.getItem(PREF_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		if (parsed && (parsed.mode === 'system' || parsed.mode === 'explicit') && parsed.themeId) {
			return parsed as ThemePreference;
		}
	} catch {
		// corrupt data
	}
	return null;
}

/**
 * Resolve which theme to apply based on OS preference.
 * Maps: OS light → "light", OS dark → "default-dark".
 */
function resolveSystemTheme(themes: ThemeDefinition[]): ThemeDefinition | undefined {
	const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
	const targetId = prefersLight ? 'light' : 'default-dark';
	return themes.find((t) => t.id === targetId);
}

/**
 * Restore the theme once after registry loads.
 *
 * Called exactly once per page load (gated by caller).
 * - If preference is "system", applies based on OS and registers matchMedia listener.
 * - If preference is explicit, applies that theme.
 * - If no preference stored, defaults to "system" mode.
 *
 * Returns a cleanup function to remove the matchMedia listener.
 */
export function restoreTheme(themes: ThemeDefinition[]): {
	appliedId: string;
	preference: ThemePreference;
	cleanup: () => void;
} {
	const stored = getStoredPreference();
	let cleanup = () => {};

	if (stored?.mode === 'explicit') {
		// Explicit preference — apply it, or fall back to default-dark if stale
		const theme = themes.find((t) => t.id === stored.themeId);
		if (theme) {
			applyTheme(theme);
			return { appliedId: theme.id, preference: stored, cleanup };
		}
		// Stale ID (plugin removed) — fall through to system mode
	}

	// System mode (or no preference, or stale explicit)
	const resolved = resolveSystemTheme(themes);
	const fallback = themes.find((t) => t.id === 'default-dark') ?? themes[0];
	const theme = resolved ?? fallback;

	if (theme) {
		applyTheme(theme);
	}

	const pref: ThemePreference = { mode: 'system', themeId: theme?.id ?? 'default-dark' };
	savePreference(pref);

	// Register matchMedia listener for live OS changes while in system mode
	const mql = window.matchMedia('(prefers-color-scheme: light)');
	const handler = () => {
		const current = getStoredPreference();
		if (current?.mode !== 'system') return; // User switched to explicit, ignore
		const newTheme = resolveSystemTheme(themes);
		if (newTheme) {
			applyTheme(newTheme);
			savePreference({ mode: 'system', themeId: newTheme.id });
		}
	};
	mql.addEventListener('change', handler);
	cleanup = () => mql.removeEventListener('change', handler);

	return { appliedId: theme?.id ?? 'default-dark', preference: pref, cleanup };
}

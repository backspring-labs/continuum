/**
 * Plugin bundle loader service.
 *
 * Handles dynamic loading of plugin UI bundles as ES modules.
 * Each bundle is loaded only once, and its custom elements are
 * automatically registered via the browser's customElements API.
 */

import { writable, derived, get, type Readable } from 'svelte/store';

// Load states for bundles
export type LoadState = 'pending' | 'loading' | 'ready' | 'failed';

interface BundleState {
	state: LoadState;
	error?: string;
}

// Internal stores
const bundleStates = writable<Map<string, BundleState>>(new Map());
const loadedBundles = new Set<string>();

/**
 * Get the current load state for a bundle URL.
 */
export function getBundleState(url: string): LoadState {
	const states = get(bundleStates);
	return states.get(url)?.state ?? 'pending';
}

/**
 * Get the error message for a failed bundle, if any.
 */
export function getBundleError(url: string): string | undefined {
	const states = get(bundleStates);
	return states.get(url)?.error;
}

/**
 * Reactive store for bundle state.
 */
export function bundleState(url: string): Readable<LoadState> {
	return derived(bundleStates, ($states) => $states.get(url)?.state ?? 'pending');
}

/**
 * Reactive store for bundle error.
 */
export function bundleError(url: string): Readable<string | undefined> {
	return derived(bundleStates, ($states) => $states.get(url)?.error);
}

/**
 * Load a plugin bundle from the given URL.
 *
 * The bundle is loaded as an ES module via a dynamic script tag.
 * Each bundle is loaded only once; subsequent calls resolve immediately.
 *
 * @param url - The URL of the plugin bundle
 * @returns Promise that resolves when the bundle is loaded
 */
export async function loadBundle(url: string): Promise<void> {
	// Already loaded
	if (loadedBundles.has(url)) {
		return;
	}

	// Already loading (or failed) - wait for existing load
	const currentState = getBundleState(url);
	if (currentState === 'loading') {
		// Wait for the bundle to finish loading
		return new Promise((resolve, reject) => {
			const unsubscribe = bundleStates.subscribe((states) => {
				const state = states.get(url);
				if (state?.state === 'ready') {
					unsubscribe();
					resolve();
				} else if (state?.state === 'failed') {
					unsubscribe();
					reject(new Error(state.error ?? 'Bundle load failed'));
				}
			});
		});
	}

	if (currentState === 'failed') {
		throw new Error(getBundleError(url) ?? 'Bundle load previously failed');
	}

	// Start loading
	bundleStates.update((states) => {
		const newStates = new Map(states);
		newStates.set(url, { state: 'loading' });
		return newStates;
	});

	return new Promise((resolve, reject) => {
		const script = document.createElement('script');
		script.type = 'module';
		script.src = url;

		script.onload = () => {
			loadedBundles.add(url);
			bundleStates.update((states) => {
				const newStates = new Map(states);
				newStates.set(url, { state: 'ready' });
				return newStates;
			});
			resolve();
		};

		script.onerror = () => {
			const errorMsg = `Failed to load bundle: ${url}`;
			bundleStates.update((states) => {
				const newStates = new Map(states);
				newStates.set(url, { state: 'failed', error: errorMsg });
				return newStates;
			});
			reject(new Error(errorMsg));
		};

		document.head.appendChild(script);
	});
}

/**
 * Preload bundles for a set of contributions.
 *
 * This is a convenience method to load all bundles needed for a set of
 * contributions. Errors are caught and logged, not thrown.
 *
 * @param bundleUrls - Set of bundle URLs to load
 */
export async function preloadBundles(bundleUrls: Set<string>): Promise<void> {
	const loadPromises = Array.from(bundleUrls).map(async (url) => {
		try {
			await loadBundle(url);
		} catch (error) {
			// Error is already captured in bundleStates
			console.error(`Failed to preload bundle: ${url}`, error);
		}
	});

	await Promise.all(loadPromises);
}

/**
 * Check if a custom element is defined.
 */
export function isElementDefined(tagName: string): boolean {
	return customElements.get(tagName) !== undefined;
}

/**
 * Wait for a custom element to be defined.
 *
 * @param tagName - The custom element tag name
 * @param timeout - Optional timeout in milliseconds (default: 5000)
 * @returns Promise that resolves when the element is defined
 */
export async function waitForElement(tagName: string, timeout = 5000): Promise<void> {
	if (isElementDefined(tagName)) {
		return;
	}

	return Promise.race([
		customElements.whenDefined(tagName),
		new Promise<void>((_, reject) => {
			setTimeout(() => {
				reject(new Error(`Timeout waiting for custom element: ${tagName}`));
			}, timeout);
		}),
	]) as Promise<void>;
}

<script lang="ts">
	import type { Contribution } from '$stores/registry';
	import {
		loadBundle,
		bundleState,
		bundleError,
		waitForElement,
		type LoadState,
	} from '$lib/services/pluginLoader';

	interface Props {
		contribution: Contribution;
	}

	let { contribution }: Props = $props();

	// Reactive bundle state
	let state = $state<LoadState>('pending');
	let error = $state<string | undefined>(undefined);
	let elementReady = $state(false);

	// Track the current bundle URL to detect changes
	let currentBundleUrl = $state<string | null>(null);

	// Load bundle when contribution changes
	$effect(() => {
		const bundleUrl = contribution.bundle_url;
		const component = contribution.component;

		// Reset state if bundle URL changed
		if (bundleUrl !== currentBundleUrl) {
			currentBundleUrl = bundleUrl ?? null;
			elementReady = false;
			state = 'pending';
			error = undefined;
		}

		if (!bundleUrl || !component) {
			return;
		}

		// Subscribe to bundle state
		const stateStore = bundleState(bundleUrl);
		const errorStore = bundleError(bundleUrl);

		const unsubState = stateStore.subscribe((s) => {
			state = s;
		});
		const unsubError = errorStore.subscribe((e) => {
			error = e;
		});

		// Start loading the bundle
		loadBundle(bundleUrl).catch(() => {
			// Error is already captured in state
		});

		return () => {
			unsubState();
			unsubError();
		};
	});

	// Wait for custom element to be defined once bundle is ready
	$effect(() => {
		if (state !== 'ready' || !contribution.component) {
			return;
		}

		waitForElement(contribution.component)
			.then(() => {
				elementReady = true;
			})
			.catch((err) => {
				error = err.message;
			});
	});
</script>

{#if !contribution.bundle_url}
	<!-- No bundle URL - show placeholder -->
	<div class="component-placeholder">
		<div class="placeholder-header">
			<span class="component-tag">&lt;{contribution.component ?? 'unknown'}&gt;</span>
			<span class="plugin-id">{contribution.plugin_id}</span>
		</div>
		<div class="placeholder-body">
			<p>No bundle configured</p>
			<p class="hint">Plugin does not have a UI bundle defined</p>
		</div>
	</div>
{:else if state === 'loading'}
	<div class="component-loading">
		<div class="loading-spinner"></div>
		<span>Loading {contribution.component}...</span>
	</div>
{:else if state === 'failed'}
	<div class="component-error">
		<div class="error-header">Failed to load plugin component</div>
		<dl class="error-details">
			<dt>Plugin</dt>
			<dd>{contribution.plugin_id}</dd>
			<dt>Component</dt>
			<dd><code>{contribution.component}</code></dd>
			<dt>Bundle</dt>
			<dd><code>{contribution.bundle_url}</code></dd>
			<dt>Error</dt>
			<dd class="error-message">{error}</dd>
		</dl>
	</div>
{:else if elementReady && contribution.component}
	<div class="component-wrapper" data-plugin={contribution.plugin_id}>
		<svelte:element this={contribution.component} />
	</div>
{:else}
	<div class="component-loading">
		<div class="loading-spinner"></div>
		<span>Initializing {contribution.component}...</span>
	</div>
{/if}

<style>
	.component-wrapper {
		display: contents;
	}

	.component-placeholder {
		background: var(--continuum-bg-tertiary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		overflow: hidden;
	}

	.placeholder-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-bg-tertiary);
		border-bottom: 1px solid var(--continuum-border);
	}

	.component-tag {
		font-family: var(--continuum-font-mono);
		font-size: var(--continuum-font-size-sm);
		color: var(--continuum-accent-primary);
	}

	.plugin-id {
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
	}

	.placeholder-body {
		padding: var(--continuum-space-lg);
		text-align: center;
	}

	.placeholder-body p {
		margin: 0;
		color: var(--continuum-text-secondary);
	}

	.hint {
		font-size: var(--continuum-font-size-sm);
		color: var(--continuum-text-muted);
		margin-top: var(--continuum-space-sm) !important;
	}

	.component-loading {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--continuum-space-sm);
		padding: var(--continuum-space-lg);
		background: var(--continuum-bg-tertiary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		color: var(--continuum-text-secondary);
		font-size: var(--continuum-font-size-sm);
	}

	.loading-spinner {
		width: 16px;
		height: 16px;
		border: 2px solid var(--continuum-border);
		border-top-color: var(--continuum-accent-primary);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.component-error {
		background: var(--continuum-bg-tertiary);
		border: 1px solid var(--continuum-accent-danger);
		border-radius: var(--continuum-radius-md);
		overflow: hidden;
	}

	.error-header {
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: rgba(248, 81, 73, 0.1);
		color: var(--continuum-accent-danger);
		font-weight: 600;
		font-size: var(--continuum-font-size-sm);
	}

	.error-details {
		padding: var(--continuum-space-md);
		margin: 0;
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--continuum-space-xs) var(--continuum-space-md);
		font-size: var(--continuum-font-size-xs);
	}

	.error-details dt {
		color: var(--continuum-text-muted);
		font-weight: 600;
	}

	.error-details dd {
		margin: 0;
		color: var(--continuum-text-secondary);
		word-break: break-all;
	}

	.error-details code {
		font-family: var(--continuum-font-mono);
		font-size: inherit;
	}

	.error-message {
		color: var(--continuum-accent-danger) !important;
	}
</style>

<script lang="ts">
	interface Props {
		title: string;
		message: string;
		dangerLevel: 'confirm' | 'danger';
		confirmLabel?: string;
		cancelLabel?: string;
		onConfirm: () => void;
		onCancel: () => void;
	}

	let {
		title,
		message,
		dangerLevel,
		confirmLabel = 'Confirm',
		cancelLabel = 'Cancel',
		onConfirm,
		onCancel,
	}: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onCancel();
		} else if (e.key === 'Enter' && dangerLevel !== 'danger') {
			// Don't allow Enter to confirm danger-level commands
			onConfirm();
		}
	}

	function handleOverlayClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			onCancel();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	class="dialog-overlay"
	onclick={handleOverlayClick}
	role="presentation"
>
	<div
		class="dialog"
		class:danger={dangerLevel === 'danger'}
		role="alertdialog"
		aria-modal="true"
		aria-labelledby="dialog-title"
		aria-describedby="dialog-message"
	>
		<header class="dialog-header">
			<div class="dialog-icon" class:danger={dangerLevel === 'danger'}>
				{#if dangerLevel === 'danger'}
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				{:else}
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				{/if}
			</div>
			<h2 id="dialog-title">{title}</h2>
		</header>

		<div class="dialog-body">
			<p id="dialog-message">{message}</p>
			{#if dangerLevel === 'danger'}
				<p class="danger-warning">
					This action may have significant consequences and cannot be undone.
				</p>
			{/if}
		</div>

		<footer class="dialog-footer">
			<button class="btn-cancel" onclick={onCancel}>
				{cancelLabel}
			</button>
			<button
				class="btn-confirm"
				class:danger={dangerLevel === 'danger'}
				onclick={onConfirm}
			>
				{confirmLabel}
			</button>
		</footer>
	</div>
</div>

<style>
	.dialog-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		animation: fadeIn 150ms ease;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.dialog {
		background: var(--continuum-bg-secondary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-lg);
		box-shadow: var(--continuum-shadow-lg);
		max-width: 400px;
		width: 90%;
		animation: slideIn 150ms ease;
	}

	.dialog.danger {
		border-color: var(--continuum-accent-danger);
	}

	@keyframes slideIn {
		from {
			opacity: 0;
			transform: scale(0.95) translateY(-10px);
		}
		to {
			opacity: 1;
			transform: scale(1) translateY(0);
		}
	}

	.dialog-header {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-md);
		padding: var(--continuum-space-md);
		border-bottom: 1px solid var(--continuum-border);
	}

	.dialog-icon {
		width: 32px;
		height: 32px;
		color: var(--continuum-accent-warning);
	}

	.dialog-icon.danger {
		color: var(--continuum-accent-danger);
	}

	.dialog-icon svg {
		width: 100%;
		height: 100%;
	}

	.dialog-header h2 {
		margin: 0;
		font-size: var(--continuum-font-size-lg);
		font-weight: 600;
	}

	.dialog-body {
		padding: var(--continuum-space-md);
	}

	.dialog-body p {
		margin: 0;
		color: var(--continuum-text-secondary);
		font-size: var(--continuum-font-size-sm);
		line-height: 1.5;
	}

	.danger-warning {
		margin-top: var(--continuum-space-md) !important;
		padding: var(--continuum-space-sm);
		background: rgba(248, 81, 73, 0.1);
		border-radius: var(--continuum-radius-sm);
		color: var(--continuum-accent-danger) !important;
		font-weight: 500;
	}

	.dialog-footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--continuum-space-sm);
		padding: var(--continuum-space-md);
		border-top: 1px solid var(--continuum-border);
	}

	.btn-cancel,
	.btn-confirm {
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		border-radius: var(--continuum-radius-md);
		font-size: var(--continuum-font-size-sm);
		font-weight: 500;
		cursor: pointer;
		transition: all 150ms ease;
	}

	.btn-cancel {
		background: transparent;
		border: 1px solid var(--continuum-border);
		color: var(--continuum-text-secondary);
	}

	.btn-cancel:hover {
		background: var(--continuum-bg-hover);
		color: var(--continuum-text-primary);
	}

	.btn-confirm {
		background: var(--continuum-accent-primary);
		border: none;
		color: white;
	}

	.btn-confirm:hover {
		opacity: 0.9;
	}

	.btn-confirm.danger {
		background: var(--continuum-accent-danger);
	}
</style>

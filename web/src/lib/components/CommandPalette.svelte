<script lang="ts">
	import type { Contribution } from '$lib/stores/registry';
	import {
		executeCommand as apiExecuteCommand,
		executeCommandConfirmed,
		executeCommandDryRun,
		isClientSideCommand,
		type CommandExecuteResult
	} from '$lib/services/commandService';
	import ConfirmDialog from './ConfirmDialog.svelte';

	interface Props {
		commands: Contribution[];
		onClose: () => void;
		onToggleDrawer?: () => void;
	}

	let { commands, onClose, onToggleDrawer }: Props = $props();

	let search = $state('');
	let selectedIndex = $state(0);
	let executing = $state(false);
	let error = $state<string | null>(null);

	// Confirmation dialog state
	let showConfirmDialog = $state(false);
	let pendingCommand = $state<Contribution | null>(null);
	let confirmResult = $state<CommandExecuteResult | null>(null);

	// Dry run preview state
	let dryRunPreview = $state<Record<string, unknown> | null>(null);
	let dryRunCommand = $state<Contribution | null>(null);

	const filteredCommands = $derived(
		commands.filter(cmd =>
			cmd.label?.toLowerCase().includes(search.toLowerCase()) ||
			cmd.id?.toLowerCase().includes(search.toLowerCase())
		)
	);

	function handleKeydown(e: KeyboardEvent) {
		if (showConfirmDialog) return; // Let dialog handle keys

		if (e.key === 'ArrowDown') {
			e.preventDefault();
			selectedIndex = Math.min(selectedIndex + 1, filteredCommands.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			selectedIndex = Math.max(selectedIndex - 1, 0);
		} else if (e.key === 'Enter' && filteredCommands[selectedIndex]) {
			executeCommand(filteredCommands[selectedIndex]);
		}
	}

	async function executeCommand(cmd: Contribution) {
		const commandId = cmd.id || cmd.action || '';
		if (!commandId) return;

		error = null;

		// Handle client-side commands locally
		if (isClientSideCommand(commandId)) {
			handleClientSideCommand(commandId);
			return;
		}

		// Execute server-side command
		executing = true;
		try {
			const result = await apiExecuteCommand({
				command_id: commandId,
				args: {}
			});

			if (result.requires_confirmation) {
				// Show confirmation dialog
				pendingCommand = cmd;
				confirmResult = result;
				showConfirmDialog = true;
				executing = false;
				return;
			}

			if (result.status === 'success') {
				onClose();
			} else if (result.status === 'denied' || result.status === 'failed') {
				error = result.error || 'Command failed';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Command execution failed';
		} finally {
			executing = false;
		}
	}

	function handleClientSideCommand(action: string) {
		switch (action) {
			case 'open_command_palette':
				// Already open, just close
				onClose();
				break;
			case 'toggle_drawer':
				onToggleDrawer?.();
				onClose();
				break;
			default:
				console.warn('Unknown client-side command:', action);
				onClose();
		}
	}

	async function handleConfirm() {
		if (!pendingCommand) return;

		const commandId = pendingCommand.id || pendingCommand.action || '';
		showConfirmDialog = false;
		executing = true;

		try {
			const result = await executeCommandConfirmed(commandId);

			if (result.status === 'success') {
				onClose();
			} else {
				error = result.error || 'Command failed';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Command execution failed';
		} finally {
			executing = false;
			pendingCommand = null;
			confirmResult = null;
		}
	}

	function handleCancelConfirm() {
		showConfirmDialog = false;
		pendingCommand = null;
		confirmResult = null;
	}

	async function executeDryRun(cmd: Contribution) {
		const commandId = cmd.id || cmd.action || '';
		if (!commandId) return;

		error = null;
		dryRunPreview = null;
		dryRunCommand = null;
		executing = true;

		try {
			const result = await executeCommandDryRun(commandId);

			if (result.status === 'success' && result.dry_run_preview) {
				dryRunPreview = result.dry_run_preview;
				dryRunCommand = cmd;
			} else if (result.status === 'failed') {
				error = result.error || 'Dry run failed';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Dry run failed';
		} finally {
			executing = false;
		}
	}

	function clearDryRunPreview() {
		dryRunPreview = null;
		dryRunCommand = null;
	}
</script>

{#if showConfirmDialog && pendingCommand}
	<ConfirmDialog
		title="Confirm Action"
		message="Are you sure you want to execute '{pendingCommand.label || pendingCommand.id}'?"
		dangerLevel={confirmResult?.danger_level === 'danger' ? 'danger' : 'confirm'}
		confirmLabel="Execute"
		onConfirm={handleConfirm}
		onCancel={handleCancelConfirm}
	/>
{:else}
	<div class="overlay" onclick={onClose} role="presentation">
		<div class="palette" onclick={(e) => e.stopPropagation()} role="dialog">
			<div class="search-container">
				<input
					type="text"
					placeholder="Type a command..."
					bind:value={search}
					onkeydown={handleKeydown}
					disabled={executing}
					autofocus
				/>
				{#if executing}
					<div class="executing-indicator">Executing...</div>
				{/if}
			</div>
			{#if error}
				<div class="error-message">
					{error}
					<button class="error-dismiss" onclick={() => error = null}>Dismiss</button>
				</div>
			{/if}
			{#if dryRunPreview && dryRunCommand}
				<div class="dry-run-preview">
					<div class="dry-run-header">
						<span class="dry-run-title">Dry Run Preview: {dryRunCommand.label}</span>
						<button class="dry-run-close" onclick={clearDryRunPreview}>×</button>
					</div>
					<pre class="dry-run-content">{JSON.stringify(dryRunPreview, null, 2)}</pre>
					<div class="dry-run-actions">
						<button class="btn-cancel" onclick={clearDryRunPreview}>Cancel</button>
						<button class="btn-execute" onclick={() => executeCommand(dryRunCommand!)}>
							Execute
						</button>
					</div>
				</div>
			{:else}
				<div class="commands-list">
					{#each filteredCommands as cmd, i}
						<div
							class="command-row"
							class:selected={i === selectedIndex}
							class:danger={cmd.danger_level === 'danger'}
							class:confirm={cmd.danger_level === 'confirm'}
						>
							<button
								class="command-item"
								onclick={() => executeCommand(cmd)}
								disabled={executing}
							>
								<span class="command-label">
									{#if cmd.danger_level === 'danger'}
										<span class="danger-icon">⚠</span>
									{/if}
									{cmd.label}
								</span>
								<span class="command-meta">
									{#if cmd.danger_level && cmd.danger_level !== 'safe'}
										<span class="danger-badge" class:danger={cmd.danger_level === 'danger'}>
											{cmd.danger_level}
										</span>
									{/if}
									{#if cmd.shortcut}
										<kbd>{cmd.shortcut}</kbd>
									{/if}
								</span>
							</button>
							{#if cmd.dry_run_supported}
								<button
									class="dry-run-btn"
									onclick={() => executeDryRun(cmd)}
									disabled={executing}
									title="Preview without executing"
								>
									Preview
								</button>
							{/if}
						</div>
					{/each}
					{#if filteredCommands.length === 0}
						<div class="no-results">No commands found</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding-top: 15vh;
		z-index: 1000;
	}

	.palette {
		width: 500px;
		max-height: 400px;
		background: var(--continuum-bg-secondary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-lg);
		box-shadow: var(--continuum-shadow-lg);
		overflow: hidden;
	}

	.search-container {
		position: relative;
		padding: var(--continuum-space-md);
		border-bottom: 1px solid var(--continuum-border);
	}

	.search-container input {
		width: 100%;
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-bg-tertiary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		color: var(--continuum-text-primary);
		font-size: var(--continuum-font-size-md);
		outline: none;
	}

	.search-container input:focus {
		border-color: var(--continuum-accent-primary);
	}

	.commands-list {
		max-height: 300px;
		overflow-y: auto;
	}

	.command-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: transparent;
		border: none;
		color: var(--continuum-text-primary);
		text-align: left;
		cursor: pointer;
	}

	.command-item:hover, .command-item.selected {
		background: var(--continuum-bg-hover);
	}

	.command-item kbd {
		padding: 2px 8px;
		background: var(--continuum-bg-tertiary);
		border-radius: var(--continuum-radius-sm);
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-secondary);
	}

	.no-results {
		padding: var(--continuum-space-lg);
		text-align: center;
		color: var(--continuum-text-muted);
	}

	.executing-indicator {
		position: absolute;
		right: var(--continuum-space-md);
		top: 50%;
		transform: translateY(-50%);
		color: var(--continuum-text-muted);
		font-size: var(--continuum-font-size-sm);
	}

	.error-message {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: rgba(248, 81, 73, 0.1);
		border-bottom: 1px solid var(--continuum-accent-danger);
		color: var(--continuum-accent-danger);
		font-size: var(--continuum-font-size-sm);
	}

	.error-dismiss {
		background: transparent;
		border: 1px solid var(--continuum-accent-danger);
		border-radius: var(--continuum-radius-sm);
		color: var(--continuum-accent-danger);
		padding: 2px 8px;
		font-size: var(--continuum-font-size-xs);
		cursor: pointer;
	}

	.error-dismiss:hover {
		background: var(--continuum-accent-danger);
		color: white;
	}

	.command-meta {
		display: flex;
		align-items: center;
		gap: var(--continuum-space-sm);
	}

	.danger-badge {
		padding: 2px 6px;
		background: var(--continuum-accent-warning);
		border-radius: var(--continuum-radius-sm);
		font-size: var(--continuum-font-size-xs);
		color: black;
		text-transform: uppercase;
	}

	.danger-badge.danger {
		background: var(--continuum-accent-danger);
		color: white;
	}

	.command-item.danger {
		border-left: 2px solid var(--continuum-accent-danger);
	}

	.command-item.confirm {
		border-left: 2px solid var(--continuum-accent-warning);
	}

	.danger-icon {
		color: var(--continuum-accent-danger);
		margin-right: 4px;
	}

	.command-item:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.command-row {
		display: flex;
		align-items: center;
		border-left: 2px solid transparent;
	}

	.command-row.danger {
		border-left-color: var(--continuum-accent-danger);
	}

	.command-row.confirm {
		border-left-color: var(--continuum-accent-warning);
	}

	.command-row.selected {
		background: var(--continuum-bg-hover);
	}

	.command-row .command-item {
		flex: 1;
		border-left: none;
	}

	.command-row.danger .command-item,
	.command-row.confirm .command-item {
		border-left: none;
	}

	.dry-run-btn {
		padding: 4px 8px;
		margin-right: var(--continuum-space-sm);
		background: var(--continuum-bg-tertiary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-sm);
		color: var(--continuum-text-secondary);
		font-size: var(--continuum-font-size-xs);
		cursor: pointer;
		transition: all 150ms ease;
	}

	.dry-run-btn:hover:not(:disabled) {
		background: var(--continuum-accent-primary);
		border-color: var(--continuum-accent-primary);
		color: white;
	}

	.dry-run-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.dry-run-preview {
		padding: var(--continuum-space-md);
	}

	.dry-run-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--continuum-space-md);
	}

	.dry-run-title {
		font-weight: 600;
		color: var(--continuum-text-primary);
	}

	.dry-run-close {
		background: transparent;
		border: none;
		color: var(--continuum-text-muted);
		font-size: 20px;
		cursor: pointer;
		padding: 0 4px;
	}

	.dry-run-close:hover {
		color: var(--continuum-text-primary);
	}

	.dry-run-content {
		background: var(--continuum-bg-tertiary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		padding: var(--continuum-space-md);
		margin-bottom: var(--continuum-space-md);
		font-size: var(--continuum-font-size-sm);
		color: var(--continuum-text-secondary);
		overflow-x: auto;
		max-height: 200px;
		overflow-y: auto;
	}

	.dry-run-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--continuum-space-sm);
	}

	.btn-cancel {
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: transparent;
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		color: var(--continuum-text-secondary);
		cursor: pointer;
	}

	.btn-cancel:hover {
		background: var(--continuum-bg-hover);
	}

	.btn-execute {
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-accent-primary);
		border: none;
		border-radius: var(--continuum-radius-md);
		color: white;
		cursor: pointer;
	}

	.btn-execute:hover {
		opacity: 0.9;
	}
</style>

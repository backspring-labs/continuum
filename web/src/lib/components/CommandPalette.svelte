<script lang="ts">
	import type { Contribution } from '$stores/registry';

	interface Props {
		commands: Contribution[];
		onClose: () => void;
	}

	let { commands, onClose }: Props = $props();

	let search = $state('');
	let selectedIndex = $state(0);

	const filteredCommands = $derived(
		commands.filter(cmd =>
			cmd.label?.toLowerCase().includes(search.toLowerCase()) ||
			cmd.id?.toLowerCase().includes(search.toLowerCase())
		)
	);

	function handleKeydown(e: KeyboardEvent) {
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

	function executeCommand(cmd: Contribution) {
		console.log('Execute command:', cmd.action);
		onClose();
	}
</script>

<div class="overlay" onclick={onClose} role="presentation">
	<div class="palette" onclick={(e) => e.stopPropagation()} role="dialog">
		<div class="search-container">
			<input
				type="text"
				placeholder="Type a command..."
				bind:value={search}
				onkeydown={handleKeydown}
				autofocus
			/>
		</div>
		<div class="commands-list">
			{#each filteredCommands as cmd, i}
				<button
					class="command-item"
					class:selected={i === selectedIndex}
					onclick={() => executeCommand(cmd)}
				>
					<span class="command-label">{cmd.label}</span>
					{#if cmd.shortcut}
						<kbd>{cmd.shortcut}</kbd>
					{/if}
				</button>
			{/each}
			{#if filteredCommands.length === 0}
				<div class="no-results">No commands found</div>
			{/if}
		</div>
	</div>
</div>

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
</style>

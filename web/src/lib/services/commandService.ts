/**
 * Command execution service.
 *
 * Provides functions for executing commands via the API and managing
 * command execution state.
 */

import { writable, get } from 'svelte/store';

// Types matching the API
export interface CommandExecuteRequest {
	command_id: string;
	args?: Record<string, unknown>;
	dry_run?: boolean;
	confirmed?: boolean;
}

export interface CommandExecuteResult {
	command_id: string;
	status: 'pending' | 'authorized' | 'denied' | 'executing' | 'success' | 'failed' | 'timeout';
	audit_id: string;
	duration_ms: number;
	result: Record<string, unknown>;
	error: string | null;
	dry_run_preview: Record<string, unknown> | null;
	requires_confirmation: boolean;
	danger_level: 'safe' | 'confirm' | 'danger';
}

export interface AuditEntry {
	audit_id: string;
	command_id: string;
	user_id: string;
	timestamp: string;
	status: string;
	duration_ms: number;
	args_redacted: Record<string, unknown>;
	error: string | null;
	context: Record<string, unknown>;
}

// Execution state
export type ExecutionState = 'idle' | 'executing' | 'confirming' | 'success' | 'error';

interface ExecutionContext {
	state: ExecutionState;
	command_id: string | null;
	result: CommandExecuteResult | null;
	error: string | null;
}

// Store for tracking current execution state
export const executionState = writable<ExecutionContext>({
	state: 'idle',
	command_id: null,
	result: null,
	error: null,
});

/**
 * Execute a command.
 *
 * @param request - The command execution request
 * @returns The execution result
 */
export async function executeCommand(
	request: CommandExecuteRequest
): Promise<CommandExecuteResult> {
	executionState.set({
		state: 'executing',
		command_id: request.command_id,
		result: null,
		error: null,
	});

	try {
		const response = await fetch('/api/commands/execute', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(request),
		});

		if (!response.ok) {
			const errorText = await response.text();
			throw new Error(`HTTP ${response.status}: ${errorText}`);
		}

		const result: CommandExecuteResult = await response.json();

		// Handle confirmation required
		if (result.requires_confirmation) {
			executionState.set({
				state: 'confirming',
				command_id: request.command_id,
				result,
				error: null,
			});
			return result;
		}

		// Handle success or failure
		if (result.status === 'success') {
			executionState.set({
				state: 'success',
				command_id: request.command_id,
				result,
				error: null,
			});
		} else if (result.status === 'denied' || result.status === 'failed') {
			executionState.set({
				state: 'error',
				command_id: request.command_id,
				result,
				error: result.error,
			});
		}

		return result;
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error';
		executionState.set({
			state: 'error',
			command_id: request.command_id,
			result: null,
			error: errorMessage,
		});
		throw error;
	}
}

/**
 * Execute a command with confirmation.
 *
 * Use this after the user confirms a CONFIRM/DANGER level command.
 */
export async function executeCommandConfirmed(
	command_id: string,
	args: Record<string, unknown> = {}
): Promise<CommandExecuteResult> {
	return executeCommand({
		command_id,
		args,
		confirmed: true,
	});
}

/**
 * Execute a dry run of a command.
 *
 * Returns a preview of what the command would do without executing.
 */
export async function executeCommandDryRun(
	command_id: string,
	args: Record<string, unknown> = {}
): Promise<CommandExecuteResult> {
	return executeCommand({
		command_id,
		args,
		dry_run: true,
	});
}

/**
 * Cancel a pending confirmation.
 */
export function cancelConfirmation(): void {
	executionState.set({
		state: 'idle',
		command_id: null,
		result: null,
		error: null,
	});
}

/**
 * Reset execution state to idle.
 */
export function resetExecutionState(): void {
	executionState.set({
		state: 'idle',
		command_id: null,
		result: null,
		error: null,
	});
}

/**
 * Get command audit log.
 *
 * @param limit - Maximum number of entries to return
 * @returns Array of audit entries
 */
export async function getAuditLog(limit = 100): Promise<AuditEntry[]> {
	const response = await fetch(`/api/commands/audit?limit=${limit}`);

	if (!response.ok) {
		throw new Error(`Failed to fetch audit log: ${response.statusText}`);
	}

	const data = await response.json();
	return data.entries;
}

/**
 * Check if a command is client-side only.
 *
 * Client-side commands are handled by the UI without API calls.
 */
export function isClientSideCommand(commandId: string): boolean {
	const clientSideCommands = ['open_command_palette', 'toggle_drawer'];
	return clientSideCommands.includes(commandId);
}

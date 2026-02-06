<svelte:options customElement="continuum-sample-systems-audit" />

<script lang="ts">
	import { onMount } from 'svelte';

	interface AuditEntry {
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

	let entries = $state<AuditEntry[]>([]);
	let loading = $state(true);
	let expandedId = $state<string | null>(null);
	let statusFilter = $state<string>('all');
	let commandFilter = $state<string>('');
	let userFilter = $state<string>('');

	onMount(async () => {
		await fetchAuditLog();
	});

	async function fetchAuditLog() {
		loading = true;
		try {
			const res = await fetch('/api/commands/audit?limit=50');
			const data = await res.json();
			entries = data.entries || [];
		} catch (e) {
			console.error('Failed to fetch audit log:', e);
		} finally {
			loading = false;
		}
	}

	const filteredEntries = $derived(
		entries.filter(e => {
			if (statusFilter !== 'all' && e.status !== statusFilter) return false;
			if (commandFilter && !e.command_id.toLowerCase().includes(commandFilter.toLowerCase())) return false;
			if (userFilter && !e.user_id.toLowerCase().includes(userFilter.toLowerCase())) return false;
			return true;
		})
	);

	const statusCounts = $derived({
		all: entries.length,
		success: entries.filter(e => e.status === 'success').length,
		failed: entries.filter(e => e.status === 'failed').length,
		denied: entries.filter(e => e.status === 'denied').length,
	});

	function toggleExpand(id: string) {
		expandedId = expandedId === id ? null : id;
	}

	function formatTimestamp(ts: string): string {
		const date = new Date(ts);
		return date.toLocaleTimeString();
	}

	function formatDuration(ms: number): string {
		if (ms < 1) return '<1ms';
		if (ms < 1000) return `${Math.round(ms)}ms`;
		return `${(ms / 1000).toFixed(2)}s`;
	}

	const statusColors: Record<string, string> = {
		success: 'var(--continuum-accent-success, #3fb950)',
		failed: 'var(--continuum-accent-danger, #f85149)',
		denied: 'var(--continuum-accent-warning, #d29922)',
		pending: 'var(--continuum-text-muted, #6e6e80)',
		timeout: 'var(--continuum-accent-danger, #f85149)',
	};
</script>

<div class="audit-panel">
	<header class="panel-header">
		<h3>Command Audit Log</h3>
		<button class="refresh-btn" onclick={fetchAuditLog} disabled={loading}>
			{loading ? '...' : '↻'}
		</button>
	</header>

	<div class="filter-bar">
		<div class="text-filters">
			<input
				type="text"
				placeholder="Filter by command..."
				bind:value={commandFilter}
				class="text-filter"
			/>
			<input
				type="text"
				placeholder="Filter by user..."
				bind:value={userFilter}
				class="text-filter"
			/>
		</div>
		<div class="status-filters">
			<button
				class="filter-btn"
				class:active={statusFilter === 'all'}
				onclick={() => statusFilter = 'all'}
			>
				All ({statusCounts.all})
			</button>
			<button
				class="filter-btn success"
				class:active={statusFilter === 'success'}
				onclick={() => statusFilter = 'success'}
			>
				Success ({statusCounts.success})
			</button>
			<button
				class="filter-btn failed"
				class:active={statusFilter === 'failed'}
				onclick={() => statusFilter = 'failed'}
			>
				Failed ({statusCounts.failed})
			</button>
			<button
				class="filter-btn denied"
				class:active={statusFilter === 'denied'}
				onclick={() => statusFilter = 'denied'}
			>
				Denied ({statusCounts.denied})
			</button>
		</div>
	</div>

	<div class="audit-list">
		{#if loading}
			<div class="loading">Loading audit log...</div>
		{:else if filteredEntries.length === 0}
			<div class="empty">No audit entries found</div>
		{:else}
			<div class="table-header">
				<span class="col-time">Time</span>
				<span class="col-command">Command</span>
				<span class="col-user">User</span>
				<span class="col-status">Status</span>
				<span class="col-duration">Duration</span>
			</div>
			{#each filteredEntries as entry}
				<div
					class="audit-row"
					class:expanded={expandedId === entry.audit_id}
					class:failed={entry.status === 'failed' || entry.status === 'timeout'}
					class:denied={entry.status === 'denied'}
				>
					<button class="audit-main" onclick={() => toggleExpand(entry.audit_id)}>
						<span class="col-time">{formatTimestamp(entry.timestamp)}</span>
						<span class="col-command">
							<code>{entry.command_id}</code>
						</span>
						<span class="col-user">{entry.user_id}</span>
						<span class="col-status">
							<span class="status-badge" style="background: {statusColors[entry.status]}">{entry.status}</span>
						</span>
						<span class="col-duration">{formatDuration(entry.duration_ms)}</span>
						<span class="expand-icon">{expandedId === entry.audit_id ? '−' : '+'}</span>
					</button>

					{#if expandedId === entry.audit_id}
						<div class="audit-details">
							<div class="detail-row">
								<span class="detail-label">Audit ID</span>
								<code class="detail-value">{entry.audit_id}</code>
							</div>
							<div class="detail-row">
								<span class="detail-label">Timestamp</span>
								<span class="detail-value">{entry.timestamp}</span>
							</div>
							<div class="detail-row">
								<span class="detail-label">Duration</span>
								<span class="detail-value">{entry.duration_ms.toFixed(2)}ms</span>
							</div>

							{#if Object.keys(entry.args_redacted).length > 0}
								<div class="detail-section">
									<span class="detail-label">Arguments (redacted)</span>
									<pre class="detail-json">{JSON.stringify(entry.args_redacted, null, 2)}</pre>
								</div>
							{/if}

							{#if entry.error}
								<div class="detail-error">
									<span class="detail-label">Error</span>
									<pre class="error-text">{entry.error}</pre>
								</div>
							{/if}

							{#if Object.keys(entry.context).length > 0}
								<div class="detail-section">
									<span class="detail-label">Context</span>
									<pre class="detail-json">{JSON.stringify(entry.context, null, 2)}</pre>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		{/if}
	</div>
</div>

<style>
	.audit-panel {
		background: var(--continuum-bg-secondary, #1a1a2e);
		border: 1px solid var(--continuum-border, #2d2d44);
		border-radius: var(--continuum-radius-md, 8px);
		overflow: hidden;
		font-family: var(--continuum-font-sans, system-ui, sans-serif);
		color: var(--continuum-text-primary, #e8e8e8);
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--continuum-space-sm, 8px) var(--continuum-space-md, 16px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-bottom: 1px solid var(--continuum-border, #2d2d44);
	}

	.panel-header h3 {
		margin: 0;
		font-size: var(--continuum-font-size-md, 14px);
		font-weight: 600;
	}

	.refresh-btn {
		padding: 4px 8px;
		background: var(--continuum-bg-hover, #252538);
		border: 1px solid var(--continuum-border, #2d2d44);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-text-secondary, #a0a0a0);
		cursor: pointer;
	}

	.refresh-btn:hover:not(:disabled) {
		background: var(--continuum-accent-primary, #58a6ff);
		color: white;
	}

	.filter-bar {
		padding: var(--continuum-space-sm, 8px) var(--continuum-space-md, 16px);
		border-bottom: 1px solid var(--continuum-border, #2d2d44);
		display: flex;
		flex-direction: column;
		gap: var(--continuum-space-sm, 8px);
	}

	.text-filters {
		display: flex;
		gap: var(--continuum-space-sm, 8px);
	}

	.text-filter {
		flex: 1;
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-tertiary, #12121f);
		border: 1px solid var(--continuum-border, #2d2d44);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-text-primary, #e8e8e8);
		font-size: var(--continuum-font-size-sm, 12px);
	}

	.text-filter:focus {
		outline: none;
		border-color: var(--continuum-accent-primary, #58a6ff);
	}

	.status-filters {
		display: flex;
		gap: var(--continuum-space-xs, 4px);
	}

	.filter-btn {
		padding: 3px 8px;
		background: var(--continuum-bg-tertiary, #12121f);
		border: 1px solid var(--continuum-border, #2d2d44);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-text-secondary, #a0a0a0);
		font-size: var(--continuum-font-size-xs, 11px);
		cursor: pointer;
	}

	.filter-btn:hover {
		background: var(--continuum-bg-hover, #252538);
	}

	.filter-btn.active {
		background: var(--continuum-accent-primary, #58a6ff);
		border-color: var(--continuum-accent-primary, #58a6ff);
		color: white;
	}

	.filter-btn.success.active {
		background: var(--continuum-accent-success, #3fb950);
		border-color: var(--continuum-accent-success, #3fb950);
	}

	.filter-btn.failed.active {
		background: var(--continuum-accent-danger, #f85149);
		border-color: var(--continuum-accent-danger, #f85149);
	}

	.filter-btn.denied.active {
		background: var(--continuum-accent-warning, #d29922);
		border-color: var(--continuum-accent-warning, #d29922);
	}

	.audit-list {
		padding: var(--continuum-space-sm, 8px);
		max-height: 400px;
		overflow-y: auto;
	}

	.loading, .empty {
		padding: var(--continuum-space-lg, 24px);
		text-align: center;
		color: var(--continuum-text-secondary, #a0a0a0);
	}

	.table-header {
		display: flex;
		align-items: center;
		padding: var(--continuum-space-xs, 4px) var(--continuum-space-sm, 8px);
		font-size: var(--continuum-font-size-xs, 11px);
		color: var(--continuum-text-muted, #6e6e80);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.col-time { width: 70px; }
	.col-command { flex: 1; }
	.col-user { width: 80px; }
	.col-status { width: 70px; }
	.col-duration { width: 60px; text-align: right; }

	.audit-row {
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
		margin-bottom: var(--continuum-space-xs, 4px);
		overflow: hidden;
	}

	.audit-row.failed {
		border-left: 3px solid var(--continuum-accent-danger, #f85149);
	}

	.audit-row.denied {
		border-left: 3px solid var(--continuum-accent-warning, #d29922);
	}

	.audit-main {
		display: flex;
		align-items: center;
		width: 100%;
		padding: var(--continuum-space-sm, 8px);
		background: transparent;
		border: none;
		color: var(--continuum-text-primary, #e8e8e8);
		cursor: pointer;
		text-align: left;
		font-size: var(--continuum-font-size-xs, 11px);
	}

	.audit-main:hover {
		background: var(--continuum-bg-hover, #252538);
	}

	.audit-main code {
		font-family: var(--continuum-font-mono, monospace);
		color: var(--continuum-accent-primary, #58a6ff);
	}

	.status-badge {
		display: inline-block;
		padding: 1px 6px;
		border-radius: 8px;
		font-size: 10px;
		color: white;
		text-transform: uppercase;
	}

	.expand-icon {
		width: 20px;
		text-align: center;
		color: var(--continuum-text-muted, #6e6e80);
	}

	.audit-details {
		padding: var(--continuum-space-sm, 8px) var(--continuum-space-md, 16px);
		border-top: 1px solid var(--continuum-border, #2d2d44);
		background: var(--continuum-bg-secondary, #1a1a2e);
	}

	.detail-row {
		display: flex;
		justify-content: space-between;
		padding: var(--continuum-space-xs, 4px) 0;
		font-size: var(--continuum-font-size-xs, 11px);
	}

	.detail-label {
		color: var(--continuum-text-muted, #6e6e80);
	}

	.detail-value {
		font-weight: 500;
	}

	.detail-value code {
		font-family: var(--continuum-font-mono, monospace);
	}

	.detail-section {
		margin-top: var(--continuum-space-sm, 8px);
	}

	.detail-json {
		margin: var(--continuum-space-xs, 4px) 0 0;
		padding: var(--continuum-space-sm, 8px);
		background: var(--continuum-bg-tertiary, #12121f);
		border-radius: var(--continuum-radius-sm, 4px);
		font-size: 10px;
		font-family: var(--continuum-font-mono, monospace);
		color: var(--continuum-text-secondary, #a0a0a0);
		overflow-x: auto;
	}

	.detail-error {
		margin-top: var(--continuum-space-sm, 8px);
	}

	.error-text {
		margin: var(--continuum-space-xs, 4px) 0 0;
		padding: var(--continuum-space-sm, 8px);
		background: rgba(248, 81, 73, 0.1);
		border-radius: var(--continuum-radius-sm, 4px);
		color: var(--continuum-accent-danger, #f85149);
		font-size: 10px;
		font-family: var(--continuum-font-mono, monospace);
		white-space: pre-wrap;
	}
</style>

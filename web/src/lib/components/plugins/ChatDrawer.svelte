<script lang="ts">
	interface Message {
		role: 'user' | 'assistant';
		content: string;
		time: string;
	}

	let messages = $state<Message[]>([
		{ role: 'assistant', content: 'Hello! I\'m your Continuum assistant. How can I help you today?', time: '10:00' },
	]);
	let input = $state('');
	let sending = $state(false);

	function formatTime(): string {
		const now = new Date();
		return `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;
	}

	async function sendMessage() {
		if (!input.trim() || sending) return;

		const userMessage = input.trim();
		input = '';
		sending = true;

		messages = [...messages, {
			role: 'user',
			content: userMessage,
			time: formatTime(),
		}];

		// Simulate assistant response
		await new Promise(resolve => setTimeout(resolve, 1000));

		const responses = [
			'I can help you with that! Let me check the system status.',
			'That\'s a great question. Based on the current registry state...',
			'I\'ve analyzed the request. Here\'s what I found...',
			'Sure! I\'ll look into that for you.',
		];

		messages = [...messages, {
			role: 'assistant',
			content: responses[Math.floor(Math.random() * responses.length)],
			time: formatTime(),
		}];

		sending = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}
</script>

<div class="chat-container">
	<div class="messages">
		{#each messages as message}
			<div class="message" data-role={message.role}>
				<div class="message-bubble">
					{message.content}
				</div>
				<span class="message-time">{message.time}</span>
			</div>
		{/each}
		{#if sending}
			<div class="message" data-role="assistant">
				<div class="message-bubble typing">
					<span class="dot"></span>
					<span class="dot"></span>
					<span class="dot"></span>
				</div>
			</div>
		{/if}
	</div>
	<div class="input-area">
		<textarea
			bind:value={input}
			onkeydown={handleKeydown}
			placeholder="Type a message..."
			rows="2"
		></textarea>
		<button onclick={sendMessage} disabled={!input.trim() || sending}>
			Send
		</button>
	</div>
</div>

<style>
	.chat-container {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 400px;
	}

	.messages {
		flex: 1;
		overflow-y: auto;
		padding: var(--continuum-space-md);
		display: flex;
		flex-direction: column;
		gap: var(--continuum-space-md);
	}

	.message {
		display: flex;
		flex-direction: column;
		max-width: 85%;
	}

	.message[data-role="user"] {
		align-self: flex-end;
		align-items: flex-end;
	}

	.message[data-role="assistant"] {
		align-self: flex-start;
		align-items: flex-start;
	}

	.message-bubble {
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		border-radius: var(--continuum-radius-lg);
		font-size: var(--continuum-font-size-sm);
		line-height: 1.5;
	}

	.message[data-role="user"] .message-bubble {
		background: var(--continuum-accent-primary);
		color: white;
		border-bottom-right-radius: var(--continuum-radius-sm);
	}

	.message[data-role="assistant"] .message-bubble {
		background: var(--continuum-bg-tertiary);
		border-bottom-left-radius: var(--continuum-radius-sm);
	}

	.message-time {
		font-size: var(--continuum-font-size-xs);
		color: var(--continuum-text-muted);
		margin-top: 2px;
	}

	.typing {
		display: flex;
		gap: 4px;
		padding: var(--continuum-space-sm) var(--continuum-space-md);
	}

	.dot {
		width: 6px;
		height: 6px;
		background: var(--continuum-text-muted);
		border-radius: 50%;
		animation: bounce 1.4s infinite ease-in-out;
	}

	.dot:nth-child(1) { animation-delay: -0.32s; }
	.dot:nth-child(2) { animation-delay: -0.16s; }

	@keyframes bounce {
		0%, 80%, 100% { transform: scale(0.8); }
		40% { transform: scale(1.2); }
	}

	.input-area {
		display: flex;
		gap: var(--continuum-space-sm);
		padding: var(--continuum-space-md);
		border-top: 1px solid var(--continuum-border);
		background: var(--continuum-bg-tertiary);
	}

	.input-area textarea {
		flex: 1;
		padding: var(--continuum-space-sm);
		background: var(--continuum-bg-secondary);
		border: 1px solid var(--continuum-border);
		border-radius: var(--continuum-radius-md);
		color: var(--continuum-text-primary);
		font-family: inherit;
		font-size: var(--continuum-font-size-sm);
		resize: none;
		outline: none;
	}

	.input-area textarea:focus {
		border-color: var(--continuum-accent-primary);
	}

	.input-area button {
		padding: var(--continuum-space-sm) var(--continuum-space-md);
		background: var(--continuum-accent-primary);
		border: none;
		border-radius: var(--continuum-radius-md);
		color: white;
		font-weight: 600;
		cursor: pointer;
		transition: opacity 150ms ease;
	}

	.input-area button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.input-area button:not(:disabled):hover {
		opacity: 0.9;
	}
</style>

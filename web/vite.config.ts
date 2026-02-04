import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173,
		proxy: {
			'/api': 'http://localhost:4040',
			'/health': 'http://localhost:4040',
			'/diagnostics': 'http://localhost:4040'
		}
	}
});

import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173,
		proxy: {
			'/api': 'http://localhost:4041',
			'/health': 'http://localhost:4041',
			'/diagnostics': 'http://localhost:4041',
			'/plugins': 'http://localhost:4041'
		}
	}
});

import { writable, derived, type Readable } from 'svelte/store';

// Types matching the API response
export interface Perspective {
	id: string;
	label: string;
	route_prefix: string;
	description: string;
}

export interface NavTarget {
	type: 'panel' | 'drawer' | 'command' | 'route';
	panel_id?: string;
	drawer_id?: string;
	command_id?: string;
	route?: string;
}

export interface Contribution {
	type: string;
	plugin_id: string;
	discovery_index: number;
	priority?: number;
	slot?: string;
	perspective?: string;
	component?: string;
	label?: string;
	icon?: string;
	target?: NavTarget;
	id?: string;
	title?: string;
	width?: string;
	shortcut?: string;
	action?: string;
}

export interface PluginStatus {
	id: string;
	name: string;
	version: string;
	status: string;
	discovery_index: number;
	required: boolean;
	error: string | null;
	contribution_count: number;
}

export interface Registry {
	lifecycle_state: string;
	registry_fingerprint: string;
	perspectives: Perspective[];
	regions: Record<string, Contribution[]>;
	commands: Contribution[];
	plugins: PluginStatus[];
	diagnostics: {
		conflicts: any[];
		missing_required: string[];
		warnings: string[];
	};
}

// Stores
export const registry = writable<Registry | null>(null);
export const registryLoading = writable(true);
export const registryError = writable<string | null>(null);
export const activePerspective = writable<string>('signal');

// Derived stores
export const perspectives: Readable<Perspective[]> = derived(
	registry,
	$registry => $registry?.perspectives ?? []
);

export const leftNav: Readable<Contribution[]> = derived(
	registry,
	$registry => $registry?.regions['ui.slot.left_nav'] ?? []
);

export const mainPanels: Readable<Contribution[]> = derived(
	[registry, activePerspective],
	([$registry, $perspective]) => {
		const panels = $registry?.regions['ui.slot.main'] ?? [];
		// Filter by active perspective or show global panels (no perspective set)
		return panels.filter(p => !p.perspective || p.perspective === $perspective);
	}
);

export const rightRailPanels: Readable<Contribution[]> = derived(
	[registry, activePerspective],
	([$registry, $perspective]) => {
		const panels = $registry?.regions['ui.slot.right_rail'] ?? [];
		return panels.filter(p => !p.perspective || p.perspective === $perspective);
	}
);

export const drawerContributions: Readable<Contribution[]> = derived(
	registry,
	$registry => $registry?.regions['ui.slot.drawer'] ?? []
);

export const commands: Readable<Contribution[]> = derived(
	registry,
	$registry => $registry?.commands ?? []
);

export const plugins: Readable<PluginStatus[]> = derived(
	registry,
	$registry => $registry?.plugins ?? []
);

// Actions
export async function fetchRegistry(): Promise<void> {
	registryLoading.set(true);
	registryError.set(null);

	try {
		const response = await fetch('/api/registry');
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		}
		const data = await response.json();
		registry.set(data);
	} catch (error) {
		registryError.set(error instanceof Error ? error.message : 'Failed to fetch registry');
	} finally {
		registryLoading.set(false);
	}
}

export function setPerspective(perspectiveId: string): void {
	activePerspective.set(perspectiveId);
}

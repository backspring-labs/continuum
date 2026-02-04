// Plugin component registry - maps component tag names to Svelte components
import SignalMetrics from './SignalMetrics.svelte';
import SignalTimeline from './SignalTimeline.svelte';
import SignalAlerts from './SignalAlerts.svelte';
import SystemsPlugins from './SystemsPlugins.svelte';
import SystemsRegistry from './SystemsRegistry.svelte';
import SystemsDiagnostics from './SystemsDiagnostics.svelte';
import ChatDrawer from './ChatDrawer.svelte';
import type { Component } from 'svelte';

// Registry mapping component tags to Svelte components
export const componentRegistry: Record<string, Component> = {
	'continuum-sample-signal-metrics': SignalMetrics,
	'continuum-sample-signal-timeline': SignalTimeline,
	'continuum-sample-signal-alerts': SignalAlerts,
	'continuum-sample-systems-plugins': SystemsPlugins,
	'continuum-sample-systems-registry': SystemsRegistry,
	'continuum-sample-systems-diagnostics': SystemsDiagnostics,
	'continuum-sample-chat-drawer': ChatDrawer,
};

export function getComponent(tag: string): Component | undefined {
	return componentRegistry[tag];
}

export {
	SignalMetrics,
	SignalTimeline,
	SignalAlerts,
	SystemsPlugins,
	SystemsRegistry,
	SystemsDiagnostics,
	ChatDrawer,
};

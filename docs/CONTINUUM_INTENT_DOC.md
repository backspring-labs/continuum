# Continuum Intent and Background

**Date:** 2026-02-02  
**Status:** Draft (v0.1)  
**Scope:** Intent + posture (not an architecture spec)

---

## Why Continuum exists

As soon as you have more than one serious system (SquadOps, Nebulus, SparkNode, internal tools, etc.), you tend to accumulate:

- scattered dashboards (Grafana here, CLI there, admin panels everywhere)
- inconsistent navigation and “where do I do *that* thing again?” friction
- different auth stories per tool
- duplicated UI components and ad-hoc “portal” glue
- a growing gap between what the system *can* do and what’s *discoverable* to the operator

Continuum exists to stop that drift early by providing a **single, extensible control-plane surface** that can host many “apps” and tools without each one becoming its own bespoke web product.

The goal isn’t “a dashboard.” The goal is **a coherent operator experience** that stays stable even as the underlying ecosystem evolves quickly.

---

## The design intent in one line

Continuum is a **plugin-driven control-plane UI shell** that hosts multiple operational “surfaces” (dashboards, consoles, and workflows) behind a consistent navigation, auth, and extensibility model — with strong introspection into what is installed, active, and wired.

---

## What “control-plane UI” means

Continuum is the **human-facing control plane** for your ecosystem:

- *Observe* what is happening (status, health, telemetry, alerts)
- *Navigate* to the right surface (tools, apps, views) without memorizing URLs
- *Operate* safely (run workflows, trigger tasks, execute admin actions)
- *Explain itself* (what plugins are active, what regions they contribute to, what commands exist)

It’s meant to be the “desktop” for the operator, not another app fighting for attention.

---

## The philosophy: perspectives + regions, not pages + one-off screens

Continuum aims to feel like a **web desktop OS**:

- **Perspectives** are coherent work modes (e.g., *Signal*, *Research*, *Time*, *Discovery*, *Systems*).
- Each perspective is composed of **regions** (fixed-but-responsive UI anchors).
- Plugins contribute **UI panels**, **navigation items**, and **commands** into declared regions.

This posture matters because it encourages a stable mental model:
> “Where does this belong?” is answered by perspective/region contracts, not by ad-hoc routes.

---

## The core problem Continuum solves

There are four problems a control plane inevitably must solve:

1) **Composition** — assemble many tools into one coherent UI without hard-coding them into the shell.  
2) **Consistency** — shared navigation, layout, auth, theming, and UX posture across surfaces.  
3) **Introspection** — always be able to answer: “what is installed, active, and contributing where?”  
4) **Safe operation** — provide well-defined command surfaces with guardrails, auditing hooks, and clear failure reporting.

Continuum is the *shell* that solves these once, so every new “app” doesn’t re-solve them poorly.

---

## Extensibility posture: host-owned seams

Continuum is intentionally **host-owned**:

- Continuum defines the **perspectives**, **regions**, and **UI contribution contracts**.
- Plugins contribute to those contracts; they don’t invent new core navigation rules.
- The default stance is “extend by contribution,” not “patch by side-effect.”

This is the same philosophical posture captured in Switchboard: extensibility is powerful only when the host controls the seams.

---

## How Switchboard fits (and why it matters)

Continuum uses Switchboard as its underlying extension substrate:

- **Switchboard (PatchPanel)** provides deterministic registration + resolution.
- Continuum declares **region contracts** and **command surfaces** as Switchboard extension points.
- Plugins contribute UI + behavior through those points with strong introspection.

The practical outcome: Continuum stays small and stable, while plugin surfaces can evolve fast.

---

## Boundary discipline: Continuum is a UI shell, not a domain layer

Continuum should not become the place where business logic lives.

- Domain logic remains in the underlying systems (SquadOps, Nebulus, etc.).
- Continuum integrates via **ports/adapters** (HTTP APIs, CLIs, message buses, etc.).
- UI plugins should call host-provided ports/services rather than reaching into internals.

The intent is to preserve a clean Hex posture: Continuum is an adapter surface, not a god-app.

---

## Security posture and “unauth vs auth” surfaces

Continuum benefits from a clear split:

- **Unauth surface (public)**: product info, docs, read-only marketing/overview.
- **Auth surface (control plane)**: operator dashboard, command execution, sensitive telemetry.

Continuum should assume:
- least privilege by default
- explicit enablement for dangerous commands
- a first-class story for auditability (even if implemented later)

---

## What Continuum is *not*

Continuum should stay small and boring in v1:

- Not a full monitoring product (it can embed/bridge to Grafana, etc.)
- Not a workflow engine (it can trigger workflows, but doesn’t *own* orchestration)
- Not a CMS
- Not an identity provider (it integrates with one)
- Not a replacement for product UIs (it hosts operational surfaces)

---

## The long-term intent (without baking it into v1)

Continuum should remain compatible with future additions like:

- richer plugin packaging and discovery
- multi-tenancy and per-tenant surface composition
- granular permissioning per command/region/perspective
- deep-linkable “workspaces” with shareable state
- portable dashboards (export/import) as artifacts
- standardized “control-plane contracts” for ecosystem services

---

## Success criteria

Continuum is “working” when:

- A new surface can be added as a plugin without changing Continuum core.
- The operator can reliably find tools by perspective and region.
- The shell can explain its wiring (installed plugins, active contributions, commands).
- Navigation and layout feel stable as the ecosystem grows.
- The control plane remains safer than ad-hoc scripts and one-off admin panels.

---

## Why this matters for your ecosystem

You’re building a multi-product universe that will evolve at different speeds.

Continuum is how you avoid:

- each subsystem becoming its own portal
- UI extensibility becoming a fragile special-case
- operational actions being scattered across CLIs and tribal knowledge
- losing trust in “what’s actually deployed and active”

Continuum is the stable operator surface that keeps the ecosystem legible.

---

## Glossary (V1)

- **Perspective**: a curated work mode / dashboard category (Signal, Research, Time, Discovery, Systems).
- **Region**: a fixed-but-responsive layout anchor that accepts contributions.
- **Panel**: a UI contribution rendered inside a region.
- **Command**: an operator action surfaced via UI (may map to an API call/workflow).
- **Plugin**: an add-on package that contributes panels/commands/nav via Switchboard contracts.

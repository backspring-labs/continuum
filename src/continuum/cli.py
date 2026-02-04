"""
Continuum CLI entry point.
"""

import argparse
import os
import sys


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="continuum",
        description="Plugin-driven control-plane UI shell",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Start the Continuum server")
    run_parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("CONTINUUM_PORT", "4040")),
        help="Port to listen on (default: 4040)",
    )
    run_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    run_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # Dev command (API only, for use with Vite dev server)
    dev_parser = subparsers.add_parser("dev", help="Start in development mode (API only)")
    dev_parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("CONTINUUM_PORT", "4040")),
        help="Port to listen on (default: 4040)",
    )

    # Inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect plugins and registry")
    inspect_parser.add_argument(
        "--plugins-dir",
        default="./plugins",
        help="Plugins directory (default: ./plugins)",
    )
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    if args.command == "run":
        run_server(host=args.host, port=args.port, reload=args.reload)
    elif args.command == "dev":
        run_server(host="127.0.0.1", port=args.port, reload=True)
    elif args.command == "inspect":
        run_inspect(plugins_dir=args.plugins_dir, as_json=args.json)
    else:
        parser.print_help()
        sys.exit(1)


def run_server(host: str, port: int, reload: bool = False) -> None:
    """Start the uvicorn server."""
    import uvicorn

    uvicorn.run(
        "continuum.main:app",
        host=host,
        port=port,
        reload=reload,
    )


def run_inspect(plugins_dir: str, as_json: bool = False) -> None:
    """Inspect plugins and registry without starting the server."""
    import asyncio
    import json

    from continuum.app.discovery import discover_plugins
    from continuum.app.loader import load_plugins
    from continuum.app.registry import build_registry

    # Discover plugins
    discovery = discover_plugins(plugins_dir)

    # Load plugins
    load_result = load_plugins(discovery.plugins)

    # Collect contributions
    all_contributions = []
    for loaded in load_result.plugins:
        all_contributions.extend(loaded.contributions)

    # Build registry
    registry = build_registry(all_contributions)

    if as_json:
        output = {
            "plugins": [
                {
                    "id": p.plugin_id,
                    "status": p.status,
                    "discovery_index": p.discovery_index,
                    "contribution_count": len(p.contributions),
                    "error": p.error,
                }
                for p in load_result.plugins
            ],
            "slots": {
                slot_id: len(contribs)
                for slot_id, contribs in registry.slots.items()
            },
            "commands": len(registry.commands),
            "fingerprint": registry.fingerprint,
            "conflicts": [
                {
                    "slot_id": c.slot_id,
                    "winner": c.winner.get("plugin_id"),
                    "losers": [l.get("plugin_id") for l in c.losers],
                }
                for c in registry.report.conflicts
            ],
            "warnings": discovery.warnings + load_result.warnings + registry.report.warnings,
            "errors": discovery.errors + load_result.errors + registry.report.errors,
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print("=" * 60)
        print("CONTINUUM INSPECT")
        print("=" * 60)
        print()

        # Plugins section
        print("PLUGINS")
        print("-" * 40)
        if load_result.plugins:
            for p in load_result.plugins:
                status_icon = "[OK]" if p.status == "LOADED" else "[FAIL]"
                print(f"  {status_icon} {p.plugin_id}")
                print(f"       index={p.discovery_index}, contributions={len(p.contributions)}")
                if p.error:
                    print(f"       error: {p.error}")
        else:
            print("  (no plugins found)")
        print()

        # Slots section
        print("SLOTS")
        print("-" * 40)
        for slot_id, contribs in sorted(registry.slots.items()):
            count = len(contribs)
            print(f"  {slot_id}: {count} contribution(s)")
            for c in contribs:
                print(f"       - {c.get('plugin_id')} (priority={c.get('priority', 100)})")
        print()

        # Commands section
        print("COMMANDS")
        print("-" * 40)
        if registry.commands:
            for cmd in registry.commands:
                print(f"  {cmd.get('id')}: {cmd.get('label')} [{cmd.get('shortcut', 'no shortcut')}]")
        else:
            print("  (no commands)")
        print()

        # Conflicts section
        if registry.report.conflicts:
            print("CONFLICTS")
            print("-" * 40)
            for c in registry.report.conflicts:
                print(f"  {c.slot_id}:")
                print(f"       winner: {c.winner.get('plugin_id')}")
                print(f"       losers: {[l.get('plugin_id') for l in c.losers]}")
            print()

        # Warnings/Errors
        all_warnings = discovery.warnings + load_result.warnings + registry.report.warnings
        all_errors = discovery.errors + load_result.errors + registry.report.errors

        if all_warnings:
            print("WARNINGS")
            print("-" * 40)
            for w in all_warnings:
                print(f"  - {w}")
            print()

        if all_errors:
            print("ERRORS")
            print("-" * 40)
            for e in all_errors:
                print(f"  - {e}")
            print()

        # Summary
        print("SUMMARY")
        print("-" * 40)
        print(f"  Plugins: {len(load_result.plugins)}")
        print(f"  Total contributions: {len(all_contributions)}")
        print(f"  Fingerprint: {registry.fingerprint}")


if __name__ == "__main__":
    main()

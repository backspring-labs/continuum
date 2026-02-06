"""
Target adapters for command execution.

Adapters handle the actual execution of commands against external systems.
The command bus uses adapters to route commands to their targets.
"""

import asyncio
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class AdapterResult:
    """Result from a target adapter execution."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    status_code: int | None = None  # For HTTP adapter
    exit_code: int | None = None  # For CLI adapter


class TargetAdapter(ABC):
    """
    Abstract base class for target adapters.

    Target adapters handle the execution of commands against external systems.
    """

    @abstractmethod
    async def execute(
        self,
        config: dict[str, Any],
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> AdapterResult:
        """
        Execute a command against the target.

        Args:
            config: Adapter-specific configuration from the command definition
            args: Command arguments from the request
            context: Execution context (user info, request ID, etc.)

        Returns:
            AdapterResult with execution outcome
        """
        ...

    @abstractmethod
    def supports_dry_run(self) -> bool:
        """Whether this adapter supports dry run preview."""
        ...

    async def dry_run(
        self,
        config: dict[str, Any],
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> AdapterResult:
        """
        Generate a dry run preview without executing.

        Default implementation returns a preview of what would be executed.
        """
        return AdapterResult(
            success=True,
            data={
                "preview": True,
                "adapter": self.__class__.__name__,
                "config": config,
                "args": args,
            },
        )


class HTTPAdapter(TargetAdapter):
    """
    HTTP adapter for REST API targets.

    Config schema:
        {
            "url": "https://api.example.com/endpoint",
            "method": "POST",  # GET, POST, PUT, DELETE, PATCH
            "headers": {"Authorization": "Bearer ${token}"},
            "timeout_seconds": 30,
            "body_template": {"action": "${action}", "params": "${args}"}
        }
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def supports_dry_run(self) -> bool:
        return True

    async def execute(
        self,
        config: dict[str, Any],
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> AdapterResult:
        """
        Execute an HTTP request to the target.

        Args:
            config: HTTP adapter configuration
            args: Command arguments
            context: Execution context

        Returns:
            AdapterResult with response data
        """
        url = config.get("url", "")
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        timeout = config.get("timeout_seconds", 30)
        body_template = config.get("body_template")

        if not url:
            return AdapterResult(
                success=False,
                error="HTTP adapter requires 'url' in config",
            )

        # Substitute variables in URL and headers
        url = self._substitute_vars(url, args, context)
        headers = {
            k: self._substitute_vars(str(v), args, context)
            for k, v in headers.items()
        }

        # Build request body
        body = None
        if body_template:
            body = self._substitute_template(body_template, args, context)
        elif method in ("POST", "PUT", "PATCH"):
            body = args

        try:
            client = await self._get_client()
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=timeout,
            )

            # Parse response
            try:
                data = response.json()
            except Exception:
                data = {"text": response.text}

            if response.is_success:
                return AdapterResult(
                    success=True,
                    data=data,
                    status_code=response.status_code,
                )
            else:
                return AdapterResult(
                    success=False,
                    data=data,
                    error=f"HTTP {response.status_code}: {response.reason_phrase}",
                    status_code=response.status_code,
                )

        except httpx.TimeoutException:
            return AdapterResult(
                success=False,
                error=f"Request timed out after {timeout} seconds",
            )
        except httpx.RequestError as e:
            return AdapterResult(
                success=False,
                error=f"Request failed: {str(e)}",
            )

    async def dry_run(
        self,
        config: dict[str, Any],
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> AdapterResult:
        """Preview the HTTP request that would be made."""
        url = config.get("url", "")
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        body_template = config.get("body_template")

        url = self._substitute_vars(url, args, context)
        headers = {
            k: self._substitute_vars(str(v), args, context)
            for k, v in headers.items()
        }

        body = None
        if body_template:
            body = self._substitute_template(body_template, args, context)
        elif method in ("POST", "PUT", "PATCH"):
            body = args

        return AdapterResult(
            success=True,
            data={
                "preview": True,
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
            },
        )

    def _substitute_vars(
        self, template: str, args: dict[str, Any], context: dict[str, Any]
    ) -> str:
        """Substitute ${var} patterns in a string."""
        result = template
        for key, value in args.items():
            result = result.replace(f"${{{key}}}", str(value))
        for key, value in context.items():
            result = result.replace(f"${{{key}}}", str(value))
        return result

    def _substitute_template(
        self, template: Any, args: dict[str, Any], context: dict[str, Any]
    ) -> Any:
        """Recursively substitute variables in a template."""
        if isinstance(template, str):
            if template == "${args}":
                return args
            return self._substitute_vars(template, args, context)
        elif isinstance(template, dict):
            return {
                k: self._substitute_template(v, args, context)
                for k, v in template.items()
            }
        elif isinstance(template, list):
            return [self._substitute_template(v, args, context) for v in template]
        return template


class CLIAdapter(TargetAdapter):
    """
    CLI adapter for command-line targets.

    Config schema:
        {
            "command": "kubectl",
            "args_template": ["get", "pods", "-n", "${namespace}"],
            "timeout_seconds": 60,
            "working_dir": "/path/to/dir",
            "env": {"KUBECONFIG": "/path/to/config"}
        }
    """

    def supports_dry_run(self) -> bool:
        return True

    async def execute(
        self,
        config: dict[str, Any],
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> AdapterResult:
        """
        Execute a CLI command.

        Args:
            config: CLI adapter configuration
            args: Command arguments
            context: Execution context

        Returns:
            AdapterResult with command output
        """
        command = config.get("command", "")
        args_template = config.get("args_template", [])
        timeout = config.get("timeout_seconds", 60)
        working_dir = config.get("working_dir")
        env = config.get("env", {})

        if not command:
            return AdapterResult(
                success=False,
                error="CLI adapter requires 'command' in config",
            )

        # Build command arguments
        cmd_args = [command]
        for arg in args_template:
            cmd_args.append(self._substitute_vars(str(arg), args, context))

        # Substitute env vars
        env = {
            k: self._substitute_vars(str(v), args, context)
            for k, v in env.items()
        }

        try:
            # Run command
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env if env else None,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return AdapterResult(
                    success=False,
                    error=f"Command timed out after {timeout} seconds",
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                return AdapterResult(
                    success=True,
                    data={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                    },
                    exit_code=process.returncode,
                )
            else:
                return AdapterResult(
                    success=False,
                    data={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                    },
                    error=f"Command exited with code {process.returncode}",
                    exit_code=process.returncode,
                )

        except FileNotFoundError:
            return AdapterResult(
                success=False,
                error=f"Command not found: {command}",
            )
        except Exception as e:
            return AdapterResult(
                success=False,
                error=f"Failed to execute command: {str(e)}",
            )

    async def dry_run(
        self,
        config: dict[str, Any],
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> AdapterResult:
        """Preview the CLI command that would be executed."""
        command = config.get("command", "")
        args_template = config.get("args_template", [])
        working_dir = config.get("working_dir")
        env = config.get("env", {})

        cmd_args = [command]
        for arg in args_template:
            cmd_args.append(self._substitute_vars(str(arg), args, context))

        return AdapterResult(
            success=True,
            data={
                "preview": True,
                "command": " ".join(cmd_args),
                "working_dir": working_dir,
                "env": env,
            },
        )

    def _substitute_vars(
        self, template: str, args: dict[str, Any], context: dict[str, Any]
    ) -> str:
        """Substitute ${var} patterns in a string."""
        result = template
        for key, value in args.items():
            result = result.replace(f"${{{key}}}", str(value))
        for key, value in context.items():
            result = result.replace(f"${{{key}}}", str(value))
        return result


# Adapter registry
_adapters: dict[str, TargetAdapter] = {}


def register_adapter(adapter_type: str, adapter: TargetAdapter) -> None:
    """Register a target adapter."""
    _adapters[adapter_type] = adapter


def get_adapter(adapter_type: str) -> TargetAdapter | None:
    """Get a registered adapter by type."""
    return _adapters.get(adapter_type)


def init_default_adapters() -> None:
    """Initialize the default adapters."""
    register_adapter("http", HTTPAdapter())
    register_adapter("cli", CLIAdapter())


# Initialize defaults on import
init_default_adapters()

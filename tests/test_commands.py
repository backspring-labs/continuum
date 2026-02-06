"""
M3 Command execution tests.

Tests for the command execution pipeline including:
- Authorization (allow/deny)
- Audit logging with redaction
- Input validation
- Danger level confirmations
"""

import pytest


class TestCommandExecution:
    """Test command execution through the API."""

    def test_execute_authorized_command_succeeds(self, client):
        """Executing an authorized command should succeed."""
        response = client.post(
            "/api/commands/execute",
            json={
                "command_id": "sample_action",
                "args": {"test_arg": "value"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "audit_id" in data
        assert data["result"] is not None

    def test_execute_command_creates_audit_entry(self, client):
        """Executing a command should create an audit entry."""
        # Execute a command
        exec_response = client.post(
            "/api/commands/execute",
            json={
                "command_id": "echo",
                "args": {"message": "hello"},
            },
        )
        assert exec_response.status_code == 200
        audit_id = exec_response.json()["audit_id"]

        # Check audit log
        audit_response = client.get("/api/commands/audit?limit=10")
        assert audit_response.status_code == 200
        entries = audit_response.json()["entries"]

        # Find our audit entry
        matching = [e for e in entries if e["audit_id"] == audit_id]
        assert len(matching) == 1
        assert matching[0]["command_id"] == "echo"
        assert matching[0]["status"] == "success"

    def test_execute_nonexistent_command_fails(self, client):
        """Executing a nonexistent command should fail."""
        response = client.post(
            "/api/commands/execute",
            json={
                "command_id": "nonexistent_command",
                "args": {},
            },
        )
        assert response.status_code == 200  # API returns 200 with error status
        data = response.json()
        assert data["status"] == "failed"
        assert "Unknown command" in data["error"]

    def test_execute_command_denied_without_capability(self, client_with_limited_user):
        """Command requiring capabilities should be denied for unauthorized user."""
        # Uses client_with_limited_user fixture which has no deploy.production capability
        response = client_with_limited_user.post(
            "/api/commands/execute",
            json={
                "command_id": "deploy_production",
                "args": {},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "denied"
        assert "audit_id" in data
        assert data["error"] is not None
        assert "deploy.production" in data["error"]

    def test_denied_command_creates_audit_entry(self, client_with_limited_user):
        """Denied command should still create an audit entry."""
        # Uses client_with_limited_user fixture which has no deploy.production capability
        exec_response = client_with_limited_user.post(
            "/api/commands/execute",
            json={
                "command_id": "deploy_production",
                "args": {},
            },
        )
        assert exec_response.status_code == 200
        assert exec_response.json()["status"] == "denied"
        audit_id = exec_response.json()["audit_id"]

        # Check audit log (use same client to ensure same app instance)
        audit_response = client_with_limited_user.get("/api/commands/audit?limit=10")
        entries = audit_response.json()["entries"]

        # Find our audit entry
        matching = [e for e in entries if e["audit_id"] == audit_id]
        assert len(matching) == 1
        assert matching[0]["status"] == "denied"

    def test_dangerous_command_requires_confirmation(self, client):
        """Dangerous commands should require confirmation."""
        # Try without confirmation
        response = client.post(
            "/api/commands/execute",
            json={
                "command_id": "clear_cache",
                "args": {},
                "confirmed": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["requires_confirmation"] is True

        # Now with confirmation
        response = client.post(
            "/api/commands/execute",
            json={
                "command_id": "clear_cache",
                "args": {},
                "confirmed": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestAuditRedaction:
    """Test audit log redaction."""

    def test_sensitive_args_are_redacted(self, client):
        """Sensitive arguments should be redacted in audit log."""
        # Execute update_secret which has audit_redaction for ["secret_value", "password"]
        exec_response = client.post(
            "/api/commands/execute",
            json={
                "command_id": "update_secret",
                "args": {
                    "key": "api_key",
                    "secret_value": "super_secret_value_12345",
                },
                "confirmed": True,  # This is a confirm-level command
            },
        )
        assert exec_response.status_code == 200
        audit_id = exec_response.json()["audit_id"]

        # Check audit log
        audit_response = client.get("/api/commands/audit?limit=10")
        entries = audit_response.json()["entries"]

        # Find our audit entry
        matching = [e for e in entries if e["audit_id"] == audit_id]
        assert len(matching) == 1

        # The "secret_value" field should be redacted
        args_redacted = matching[0]["args_redacted"]
        assert args_redacted.get("key") == "api_key"  # Not redacted
        assert args_redacted.get("secret_value") == "[REDACTED]"  # Should be redacted


class TestInputValidation:
    """Test command input validation."""

    def test_missing_required_args_fails(self, client):
        """Commands with input_schema should validate required args."""
        # restart_service requires service_name per its input_schema
        response = client.post(
            "/api/commands/execute",
            json={
                "command_id": "restart_service",
                "args": {},  # Missing required service_name
                "confirmed": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "service_name" in data["error"]
        assert "audit_id" in data  # Failed commands still get audit entries


class TestAuditLogEndpoint:
    """Test the audit log API endpoint."""

    def test_audit_log_returns_entries(self, client):
        """Audit log endpoint should return entries."""
        # Execute a command first to ensure there's at least one entry
        client.post(
            "/api/commands/execute",
            json={"command_id": "echo", "args": {}},
        )

        response = client.get("/api/commands/audit?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert len(data["entries"]) >= 1

    def test_audit_log_respects_limit(self, client):
        """Audit log should respect the limit parameter."""
        # Execute multiple commands
        for i in range(5):
            client.post(
                "/api/commands/execute",
                json={"command_id": "echo", "args": {"i": i}},
            )

        response = client.get("/api/commands/audit?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) <= 2

    def test_audit_entries_have_required_fields(self, client):
        """Audit entries should have all required fields."""
        # Execute a command
        client.post(
            "/api/commands/execute",
            json={"command_id": "echo", "args": {"test": "value"}},
        )

        response = client.get("/api/commands/audit?limit=1")
        data = response.json()
        entry = data["entries"][0]

        assert "audit_id" in entry
        assert "command_id" in entry
        assert "user_id" in entry
        assert "timestamp" in entry
        assert "status" in entry
        assert "duration_ms" in entry
        assert "args_redacted" in entry

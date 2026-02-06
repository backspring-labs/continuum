"""
Authentication and authorization models for Continuum.

These models define the user context and policy decision structures
used throughout the command execution pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PolicyEffect(Enum):
    """The effect of a policy decision."""

    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class UserContext:
    """
    Context about the authenticated user.

    In V1, this is a simple model. Future versions may integrate
    with external identity providers.

    Attributes:
        user_id: Unique identifier for the user
        username: Display name
        roles: List of role identifiers
        capabilities: List of capability grants
        claims: Additional identity claims (from IdP)
    """

    user_id: str
    username: str = ""
    roles: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    claims: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def anonymous(cls) -> "UserContext":
        """Create an anonymous user context (for unauthenticated requests)."""
        return cls(user_id="anonymous", username="Anonymous")

    @classmethod
    def system(cls) -> "UserContext":
        """Create a system user context (for internal operations)."""
        return cls(
            user_id="system",
            username="System",
            roles=("system",),
            capabilities=("*",),  # System has all capabilities
        )

    def has_capability(self, capability: str) -> bool:
        """Check if user has a specific capability."""
        if "*" in self.capabilities:
            return True
        return capability in self.capabilities

    def has_all_capabilities(self, capabilities: list[str]) -> bool:
        """Check if user has all specified capabilities."""
        if "*" in self.capabilities:
            return True
        return all(cap in self.capabilities for cap in capabilities)


@dataclass(frozen=True)
class PolicyDecision:
    """
    Result of a policy evaluation.

    Attributes:
        effect: Whether the action is allowed or denied
        rationale: Human-readable explanation of the decision
        missing_capabilities: Capabilities the user lacks (if denied)
        evaluated_at: Timestamp of evaluation (ISO format)
    """

    effect: PolicyEffect
    rationale: str = ""
    missing_capabilities: tuple[str, ...] = ()
    evaluated_at: str = ""

    @classmethod
    def allow(cls, rationale: str = "Authorized") -> "PolicyDecision":
        """Create an allow decision."""
        from datetime import datetime

        return cls(
            effect=PolicyEffect.ALLOW,
            rationale=rationale,
            evaluated_at=datetime.utcnow().isoformat(),
        )

    @classmethod
    def deny(
        cls, rationale: str, missing_capabilities: list[str] | None = None
    ) -> "PolicyDecision":
        """Create a deny decision."""
        from datetime import datetime

        return cls(
            effect=PolicyEffect.DENY,
            rationale=rationale,
            missing_capabilities=tuple(missing_capabilities or []),
            evaluated_at=datetime.utcnow().isoformat(),
        )

    @property
    def is_allowed(self) -> bool:
        """Check if the decision allows the action."""
        return self.effect == PolicyEffect.ALLOW

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "effect": self.effect.value,
            "rationale": self.rationale,
            "missing_capabilities": list(self.missing_capabilities),
            "evaluated_at": self.evaluated_at,
        }


class PolicyEngine:
    """
    Simple policy engine for V1.

    Implements deny-by-default with capability-based authorization.
    Future versions may integrate with external policy engines (OPA, etc.).
    """

    def evaluate(
        self, user: UserContext, required_capabilities: list[str]
    ) -> PolicyDecision:
        """
        Evaluate whether a user can perform an action requiring capabilities.

        Args:
            user: The user context
            required_capabilities: Capabilities required for the action

        Returns:
            PolicyDecision indicating allow or deny
        """
        # No capabilities required = allow
        if not required_capabilities:
            return PolicyDecision.allow("No capabilities required")

        # Check if user has all required capabilities
        missing = [cap for cap in required_capabilities if not user.has_capability(cap)]

        if missing:
            return PolicyDecision.deny(
                f"Missing required capabilities: {', '.join(missing)}",
                missing_capabilities=missing,
            )

        return PolicyDecision.allow("User has required capabilities")

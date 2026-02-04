"""
Lifecycle state machine for Continuum runtime.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable


class LifecycleState(Enum):
    """Lifecycle states for the Continuum runtime."""

    BOOTING = "booting"
    DISCOVERING_PLUGINS = "discovering_plugins"
    LOADING_PLUGINS = "loading_plugins"
    RESOLVING_REGISTRY = "resolving_registry"
    READY = "ready"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class LifecycleEvent:
    """Event emitted on lifecycle state transitions."""

    event_type: str
    from_state: LifecycleState | None
    to_state: LifecycleState
    timestamp: datetime
    context: dict[str, str] = field(default_factory=dict)


# Valid state transitions
VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.BOOTING: {LifecycleState.DISCOVERING_PLUGINS},
    LifecycleState.DISCOVERING_PLUGINS: {LifecycleState.LOADING_PLUGINS},
    LifecycleState.LOADING_PLUGINS: {LifecycleState.RESOLVING_REGISTRY},
    LifecycleState.RESOLVING_REGISTRY: {LifecycleState.READY, LifecycleState.DEGRADED},
    LifecycleState.READY: {LifecycleState.DEGRADED, LifecycleState.STOPPING},
    LifecycleState.DEGRADED: {LifecycleState.STOPPING},
    LifecycleState.STOPPING: {LifecycleState.STOPPED},
    LifecycleState.STOPPED: set(),
}


class LifecycleManager:
    """
    Manages lifecycle state transitions for the Continuum runtime.

    Emits structured events on each transition.
    """

    def __init__(self) -> None:
        self._state = LifecycleState.BOOTING
        self._events: list[LifecycleEvent] = []
        self._listeners: list[Callable[[LifecycleEvent], None]] = []

        # Record initial state
        self._emit_event(None, LifecycleState.BOOTING)

    @property
    def state(self) -> LifecycleState:
        """Current lifecycle state."""
        return self._state

    @property
    def events(self) -> list[LifecycleEvent]:
        """List of lifecycle events."""
        return self._events.copy()

    def add_listener(self, listener: Callable[[LifecycleEvent], None]) -> None:
        """Add a listener for lifecycle events."""
        self._listeners.append(listener)

    def transition_to(self, new_state: LifecycleState, context: dict[str, str] | None = None) -> None:
        """
        Transition to a new state.

        Raises ValueError if the transition is invalid.
        """
        if new_state not in VALID_TRANSITIONS.get(self._state, set()):
            raise ValueError(
                f"Invalid lifecycle transition: {self._state.value} -> {new_state.value}"
            )

        old_state = self._state
        self._state = new_state
        self._emit_event(old_state, new_state, context)

    def _emit_event(
        self,
        from_state: LifecycleState | None,
        to_state: LifecycleState,
        context: dict[str, str] | None = None,
    ) -> None:
        """Emit a lifecycle event."""
        event = LifecycleEvent(
            event_type="continuum.lifecycle.transition",
            from_state=from_state,
            to_state=to_state,
            timestamp=datetime.now(timezone.utc),
            context=context or {},
        )
        self._events.append(event)

        for listener in self._listeners:
            listener(event)

"""
Event system for Continuum.

Provides a simple publish-subscribe event bus for structured events.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class Event:
    """Base event structure for all Continuum events."""

    event_type: str
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, event_type: str, data: dict[str, Any] | None = None) -> "Event":
        """Create an event with current timestamp."""
        return cls(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            data=data or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# Type alias for event listeners
EventListener = Callable[[Event], None]


class EventBus:
    """
    Simple event bus for publishing and subscribing to events.

    Events are identified by event_type strings (e.g., 'continuum.command.executed').
    Listeners can subscribe to specific event types or all events (*).
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[EventListener]] = {}
        self._recent_events: list[Event] = []
        self._max_recent_events = 1000

    def subscribe(self, event_type: str, listener: EventListener) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: The event type to listen for (or '*' for all events)
            listener: Callback function that receives the event
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: str, listener: EventListener) -> None:
        """
        Unsubscribe from events.

        Args:
            event_type: The event type to unsubscribe from
            listener: The listener to remove
        """
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(listener)
            except ValueError:
                pass  # Listener not found

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribed listeners.

        Args:
            event: The event to publish
        """
        # Store in recent events
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent_events:
            self._recent_events = self._recent_events[-self._max_recent_events:]

        # Notify type-specific listeners
        for listener in self._listeners.get(event.event_type, []):
            try:
                listener(event)
            except Exception:
                # Don't let listener errors break the event bus
                pass

        # Notify wildcard listeners
        for listener in self._listeners.get("*", []):
            try:
                listener(event)
            except Exception:
                pass

    def emit(self, event_type: str, data: dict[str, Any] | None = None) -> Event:
        """
        Convenience method to create and publish an event.

        Args:
            event_type: The event type
            data: Event data payload

        Returns:
            The created event
        """
        event = Event.create(event_type, data)
        self.publish(event)
        return event

    def get_recent_events(
        self, event_type: str | None = None, limit: int = 100
    ) -> list[Event]:
        """
        Get recent events, optionally filtered by type.

        Args:
            event_type: Filter by event type (None for all)
            limit: Maximum number of events to return

        Returns:
            List of recent events (newest first)
        """
        events = self._recent_events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return list(reversed(events[-limit:]))


# Global event bus instance
_global_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus() -> None:
    """Reset the global event bus (for testing)."""
    global _global_event_bus
    _global_event_bus = None

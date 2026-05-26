from collections.abc import Iterable

from backend.events import AgentEvent


class EventRecorder:
    """Captures run events for later persistence or WebSocket streaming."""

    def __init__(self) -> None:
        self._events: list[AgentEvent] = []

    def emit(self, event: AgentEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> tuple[AgentEvent, ...]:
        return tuple(self._events)

    def extend(self, events: Iterable[AgentEvent]) -> None:
        self._events.extend(events)


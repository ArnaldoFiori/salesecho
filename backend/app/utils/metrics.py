import time
from collections import deque


class PipelineMetrics:
    """Métricas do pipeline com janela deslizante de 30 min."""

    def __init__(self, window_seconds: int = 1800):
        self.window = window_seconds
        self._events: deque = deque()

    def record(self, success: bool):
        now = time.time()
        self._events.append((now, success))
        self._cleanup(now)

    def _cleanup(self, now: float):
        while self._events and self._events[0][0] < now - self.window:
            self._events.popleft()

    @property
    def error_rate(self) -> float:
        now = time.time()
        self._cleanup(now)
        if not self._events:
            return 0.0
        errors = sum(1 for _, ok in self._events if not ok)
        return errors / len(self._events)

    @property
    def total(self) -> int:
        self._cleanup(time.time())
        return len(self._events)


pipeline_metrics = PipelineMetrics()

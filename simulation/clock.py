"""Fixed-rate clock helpers."""


class FixedStepClock:
    """Convert elapsed wall-clock time into bounded fixed simulation steps."""

    def __init__(self, tick_rate: int = 60) -> None:
        """Create a clock with ``tick_rate`` fixed steps per second."""

        if tick_rate <= 0:
            raise ValueError("tick_rate must be positive")
        self.tick_rate = tick_rate
        self._accumulator = 0.0

    def consume(self, elapsed_seconds: float) -> int:
        """Return the number of due steps and retain fractional remainder."""

        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds cannot be negative")
        self._accumulator += elapsed_seconds
        step_seconds = 1.0 / self.tick_rate
        steps = int(self._accumulator / step_seconds)
        self._accumulator -= steps * step_seconds
        return steps

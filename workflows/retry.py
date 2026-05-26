from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0

    def should_retry(self, attempt: int, retryable: bool) -> bool:
        return retryable and attempt < self.max_attempts

    def delay_for_attempt(self, attempt: int) -> float:
        delay = self.base_delay_seconds * (2 ** max(attempt - 1, 0))
        return min(delay, self.max_delay_seconds)


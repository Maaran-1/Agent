from tools.base import ToolResult

from .contracts import ReflectionDecision, ReflectionResult


class ReflectionEngine:
    """Makes the next-step decision after each tool result."""

    def decide(
        self,
        result: ToolResult,
        attempt: int,
        max_attempts: int,
        has_more_steps: bool,
    ) -> ReflectionResult:
        if result.ok and has_more_steps:
            return ReflectionResult(
                decision=ReflectionDecision.CONTINUE,
                reason="Step succeeded and more steps remain.",
            )

        if result.ok:
            return ReflectionResult(
                decision=ReflectionDecision.COMPLETE,
                reason="Final step succeeded.",
            )

        if result.retryable and attempt < max_attempts:
            return ReflectionResult(
                decision=ReflectionDecision.RETRY,
                reason=result.error or "Step failed with a retryable error.",
            )

        return ReflectionResult(
            decision=ReflectionDecision.FAIL,
            reason=result.error or "Step failed and cannot continue.",
        )


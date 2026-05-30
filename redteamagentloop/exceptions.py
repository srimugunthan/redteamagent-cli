"""Sentinel exceptions for _run_target_loop termination conditions."""


class MaxIterationsReached(Exception):
    """Attacker hit the configured max_iterations limit — normal termination."""


class AttackerLLMFailed(Exception):
    """Attacker LLM could not produce a valid prompt after retries."""


class CircuitBreakerTripped(Exception):
    """Too many consecutive blocked/failed prompts — session terminated."""


class TargetUnreachable(Exception):
    """Target LLM circuit breaker exceeded its pause limit."""

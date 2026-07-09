"""
SignalResolutionPolicy — canonical signal provider priority order.

Encodes the rule: an externally injected provider always wins; if none is
supplied, fall back through RuntimeStubProvider → SyntheticProvider.

This is a structural invariant, not runtime branching logic. Callers that
construct a pipeline (M1Pipeline, SpatialRuntime) use this to pick the
correct provider when the user has not explicitly supplied one.
"""

from typing import Optional

from .base import BaseSignalProvider
from .runtime_stub import RuntimeStubProvider
from .synthetic import SyntheticProvider


class SignalResolutionPolicy:
    """
    Resolves which signal provider to use given optional injected candidates.

    Priority order (highest → lowest):
        1. external_provider  — explicitly injected by the caller
        2. runtime_stub       — RuntimeStubProvider (safe defaults)
        3. synthetic          — SyntheticProvider (ambiguous land fallback)

    Usage:
        policy = SignalResolutionPolicy()
        provider = policy.resolve(external_provider=user_supplied)
    """

    PRIORITY_ORDER = (
        "external_injected",   # 1. user-supplied at construction
        "runtime_stub",        # 2. RuntimeStubProvider
        "synthetic_fallback",  # 3. SyntheticProvider
    )

    def resolve(
        self,
        external_provider: Optional[BaseSignalProvider] = None,
        *,
        fallback: str = "synthetic",
    ) -> BaseSignalProvider:
        """
        Return the highest-priority provider available.

        Args:
            external_provider: explicitly injected provider, or None.
            fallback: "runtime_stub" or "synthetic" (default "synthetic").
                      Determines which built-in is used when no external
                      provider is supplied.

        Returns:
            A concrete BaseSignalProvider instance.
        """
        if external_provider is not None:
            return external_provider
        if fallback == "runtime_stub":
            return RuntimeStubProvider()
        return SyntheticProvider()

    def priority_label(self, provider: Optional[BaseSignalProvider]) -> str:
        """Return the priority tier label for a given provider instance."""
        if provider is None:
            return "synthetic_fallback"
        if isinstance(provider, RuntimeStubProvider):
            return "runtime_stub"
        if isinstance(provider, SyntheticProvider):
            return "synthetic_fallback"
        return "external_injected"

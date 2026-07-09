"""
Re-export shim — class definition has moved to core/signal/providers/runtime_stub.py.

RealSignalProvider is kept as a backward-compatible alias for RuntimeStubProvider.
New code should import RuntimeStubProvider directly.
"""
from .providers.runtime_stub import RuntimeStubProvider  # noqa: F401

# Backward-compatible alias — do not add new usages.
RealSignalProvider = RuntimeStubProvider

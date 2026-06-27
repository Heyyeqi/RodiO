"""
Re-export shim — class definition has moved to core/signal/providers/m1_bridge.py.

RealSignalProvider is kept as a backward-compatible alias for M1BridgeProvider.
New code should import M1BridgeProvider directly from core.signal.providers.
"""
from core.signal.providers.m1_bridge import M1BridgeProvider  # noqa: F401

# Backward-compatible alias — do not add new usages.
RealSignalProvider = M1BridgeProvider

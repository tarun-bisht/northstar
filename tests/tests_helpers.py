"""Shared helpers for tests that need the real net.get (conftest blocks the network)."""
import importlib


def real_get():
    import dsys.net as net
    mod = importlib.reload(net)
    mod._sleep = lambda s: None
    return mod.get

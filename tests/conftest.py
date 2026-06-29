"""Ensure project root is on sys.path and webviz resolves correctly (not tests/webviz/)."""
import importlib
import sys
from pathlib import Path

# Insert project root at position 0 so `webviz` resolves to webviz/ (not tests/webviz/).
_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Pre-load the real webviz package so sys.modules["webviz"] points to webviz/__init__.py.
# Without this, pytest (importlib mode) would register tests/webviz/ as the webviz package
# during test collection, shadowing the actual webviz/ package at the project root.
if "webviz" not in sys.modules or not getattr(sys.modules.get("webviz"), "__file__", "").endswith("webviz/__init__.py"):
    _spec = importlib.util.spec_from_file_location("webviz", _root + "/webviz/__init__.py",
        submodule_search_locations=[_root + "/webviz"])
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["webviz"] = _mod
    _spec.loader.exec_module(_mod)

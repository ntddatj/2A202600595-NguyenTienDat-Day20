import importlib

def test_package_imports():
    mod = importlib.import_module("webviz")
    assert mod is not None

def test_main_module_has_main_callable():
    main = importlib.import_module("webviz.__main__")
    assert callable(main.main)

def test_viz_optional_deps_declared():
    import tomllib
    from pathlib import Path
    data = tomllib.loads(Path("pyproject.toml").read_text())
    viz = data["project"]["optional-dependencies"]["viz"]
    joined = " ".join(viz)
    assert "fastapi" in joined and "uvicorn" in joined and "sse-starlette" in joined

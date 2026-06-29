"""Entrypoint: `python -m webviz [--host H] [--port P]` launches the FastAPI app via uvicorn."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m webviz", description="Run the webviz teaching GUI.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default 8000).")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("webviz.server:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

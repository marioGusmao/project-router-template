#!/usr/bin/env python3
"""Launch the Project Router Dashboard."""
import argparse
import socket
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def main():
    parser = argparse.ArgumentParser(description="Project Router Dashboard")
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if is_port_in_use(args.port):
        try:
            import urllib.request
            with urllib.request.urlopen(
                f"http://localhost:{args.port}/api/status", timeout=2
            ):
                print(
                    f"Dashboard already running at http://localhost:{args.port}"
                )
                if not args.no_browser:
                    webbrowser.open(f"http://localhost:{args.port}")
                return
        except Exception:
            print(
                f"Port {args.port} in use by another process.",
                file=sys.stderr,
            )
            sys.exit(1)

    static_dir = ROOT / "dashboard" / "frontend" / "dist"
    if not static_dir.exists():
        static_dir = None
        print(
            "Warning: frontend not built. API-only mode.", file=sys.stderr
        )

    from project_router.web.server import create_server

    server = create_server(port=args.port, static_dir=static_dir, dev=args.dev)
    print(f"Serving dashboard at http://localhost:{args.port}")
    if not args.no_browser:
        webbrowser.open(f"http://localhost:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()

"""
FastAPI Server Launcher for Swarm Website Builder (Stage 3).
Starts the HTTP REST API and Starlette WebSocket server on http://127.0.0.1:8000.
"""

import argparse
from pathlib import Path
import sys
import uvicorn

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main():
    parser = argparse.ArgumentParser(description="Run Swarm Website Builder API Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")
    args = parser.parse_args()

    print(f"Starting Swarm Website Builder API on http://{args.host}:{args.port}")
    print(f"Interactive API Docs : http://{args.host}:{args.port}/docs")
    print(f"WebSocket Endpoint   : ws://{args.host}:{args.port}/ws/runs/{{run_id}}")
    print(f"Sandbox Preview      : http://{args.host}:{args.port}/runs/{{run_id}}/preview/index.html")

    uvicorn.run("api.server:app", host=args.host, port=args.port, reload=args.reload, app_dir=str(REPO_ROOT))


if __name__ == "__main__":
    main()


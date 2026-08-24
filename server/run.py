"""Run the local web control plane; bind to loopback by default."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .api import ApiApplication, MaintenanceHTTPServer
from .database import MaintenanceStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Windows Clean Agent maintenance console")
    parser.add_argument("--host", default=os.getenv("WCA_CONSOLE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("WCA_CONSOLE_PORT", "8765")))
    parser.add_argument("--database", type=Path, default=Path(os.getenv("WCA_CONSOLE_DB", "maintenance.db")))
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("The built-in server only binds loopback; use an authenticated TLS reverse proxy for remote access")
    app = ApiApplication(MaintenanceStore(args.database), os.getenv("WCA_CONSOLE_TOKEN", ""), os.getenv("WCA_AGENT_TOKEN", ""))
    server = MaintenanceHTTPServer((args.host, args.port), app)
    print(f"Maintenance console: http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

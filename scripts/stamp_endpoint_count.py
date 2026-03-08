#!/usr/bin/env python3
"""Derive endpoint count from the actual FastAPI app and stamp it across all files.

Usage: python scripts/stamp_endpoint_count.py [--dry-run] [--verbose]

Counts real API routes from the app (excluding static pages, docs, catch-all),
then replaces stale "N endpoints" references in HTML, MD, YML, and SVG files.
The guide.py welcome message is already dynamic and doesn't need stamping.
"""

import os
import re
import sys

# Add src to path so we can import the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Minimal env so the app can be imported without a running node
os.environ.setdefault("RPC_USER", "x")
os.environ.setdefault("RPC_PASSWORD", "x")

# Routes that are NOT API endpoints (static pages, docs, infra)
_SKIP_ROUTES = {
    "/", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json",
    "/favicon.ico", "/robots.txt", "/sitemap.xml",
}
# Catch-all pattern routes (e.g., /{page} for SEO pages)
_SKIP_PATTERNS = {"/{page}"}


def count_endpoints(verbose: bool = False) -> int:
    """Count real API endpoints from the FastAPI app."""
    from bitcoin_api.main import app
    endpoints = []
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set())
        # WebSocket routes have no methods but are still endpoints
        is_ws = hasattr(route, "path") and not methods and "websocket" in type(route).__name__.lower()
        if not path:
            continue
        if not methods and not is_ws:
            continue
        if path in _SKIP_ROUTES or path in _SKIP_PATTERNS:
            continue
        endpoints.append((sorted(methods) if methods else ["WS"], path))

    if verbose:
        for methods, path in sorted(endpoints, key=lambda x: x[1]):
            print(f"  {methods} {path}")

    return len(endpoints)


def stamp_files(count: int, dry_run: bool = False) -> list[str]:
    """Replace 'N endpoints' with the actual count across all project files."""
    root = os.path.join(os.path.dirname(__file__), "..")
    root = os.path.abspath(root)

    pattern = re.compile(r"(?<!\w)(\d+)(\+?\s+endpoints)")

    extensions = {".md", ".html", ".yml", ".yaml", ".svg"}
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox"}

    updated = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            _, ext = os.path.splitext(fname)
            if ext not in extensions:
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError):
                continue

            new_content = pattern.sub(lambda m: f"{count}{m.group(2)}", content)
            if new_content != content:
                if not dry_run:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                rel = os.path.relpath(fpath, root)
                updated.append(rel)

    return updated


def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv
    count = count_endpoints(verbose=verbose)
    print(f"API endpoint count: {count}")

    updated = stamp_files(count, dry_run=dry_run)
    verb = "Would update" if dry_run else "Updated"
    if updated:
        print(f"\n{verb} {len(updated)} files:")
        for f in sorted(updated):
            print(f"  {f}")
    else:
        print("\nAll files already consistent.")


if __name__ == "__main__":
    main()

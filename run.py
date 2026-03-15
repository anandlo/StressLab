#!/usr/bin/env python3
"""Entry point for the Cognitive Stress Induction Tool.

Builds the frontend if needed, then starts the FastAPI server
and opens the browser.
"""

import os
import sys
import subprocess
import webbrowser
import time
import threading

HOST = "0.0.0.0"
PORT = 8000
ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")
FRONTEND_DIST = os.path.join(FRONTEND_DIR, "out")


def build_frontend():
    if not os.path.isdir(FRONTEND_DIR):
        print("Frontend directory not found. Skipping build.")
        return False
    if os.path.isdir(FRONTEND_DIST) and os.listdir(FRONTEND_DIST):
        print("Frontend already built.")
        return True
    print("Building frontend...")
    npm = "npm"
    try:
        subprocess.run([npm, "--version"], capture_output=True, check=True)
    except FileNotFoundError:
        print("npm not found. Please install Node.js and npm, then run:")
        print(f"  cd {FRONTEND_DIR} && npm install && npm run build")
        return False
    subprocess.run([npm, "install"], cwd=FRONTEND_DIR, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR, check=True)
    print("Frontend built successfully.")
    return True


def open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}")


def main():
    build_frontend()
    threading.Thread(target=open_browser, daemon=True).start()
    print(f"\nStarting StressLab at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.\n")
    import uvicorn
    uvicorn.run("backend.app:app", host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()

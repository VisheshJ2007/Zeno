"""Helper script to start the backend server with a robust import path.

Run this from the repo root (or anywhere) with:
    python run_backend.py

It ensures the repository root is on sys.path and then starts uvicorn
programmatically so you won't get import errors when running from the
`backend/` folder in some shells.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

def main():
    import uvicorn
    # Ensure backend package can be imported regardless of cwd
    repo_root = HERE
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Launch uvicorn programmatically
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()

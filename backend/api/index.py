# api/index.py
# Vercel Python Serverless entry for FastAPI

# Ensure "backend" is a Python package
# (backend/__init__.py must exist; see step 2)
from backend.main import app as app  # Vercel looks for "app"
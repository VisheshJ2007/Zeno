# api/index.py
# Vercel Python Serverless entry for FastAPI

# Ensure "backend" is a Python package
# (backend/_init_.py must exist; see step 2)
from backend.main import app as app  # Vercel looks for "app"
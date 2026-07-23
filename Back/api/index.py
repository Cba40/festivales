"""Vercel serverless entrypoint for FastAPI app."""
from app.main import app

# Vercel expects the ASGI app to be exported as 'app' or 'handler'
handler = app
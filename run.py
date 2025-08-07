#!/usr/bin/env python3
"""
Healthcare Provider Registration API - Startup Script
"""

import uvicorn
import os

# Set environment variable to use SQLite for development
os.environ["DATABASE_URL"] = "sqlite:///./healthcare_dev.db"
os.environ["TESTING"] = "false"

from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    ) 
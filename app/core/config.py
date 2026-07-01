"""
Configuration settings for the hiring agent application.
"""

import os

# Global development mode flag
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
PERSIST_EVALUATION_DATA = os.getenv("PERSIST_EVALUATION_DATA", "false").lower() == "true"

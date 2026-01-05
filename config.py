"""
Configuration file to load environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Binance API Configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# GitHub API Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER', '')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME', 'Risk-Management')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'start-web-project')

# Validate required variables
def validate_config():
    """Check if required environment variables are set"""
    missing = []

    if not BINANCE_API_KEY:
        missing.append('BINANCE_API_KEY')
    if not BINANCE_API_SECRET:
        missing.append('BINANCE_API_SECRET')

    if missing:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing)}")
        print("⚠️  Some features may not work. Please check your .env file.")
        return False

    print("✅ All required environment variables are set")
    return True

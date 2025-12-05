"""
Configuration settings for Sports Betting Analytics Platform
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# API KEYS - STORED IN .env FILE
# ============================================================================
ODDS_API_KEY = os.getenv('ODDS_API_KEY')
RAPID_API_KEY = os.getenv('RAPID_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./betting.db')

# ============================================================================
# API ENDPOINTS
# ============================================================================
ODDS_API_BASE = 'https://api.the-odds-api.com/v4'
RAPIDAPI_BASE = 'https://api-football-v3.p.rapidapi.com'

# ============================================================================
# POLLING CONFIGURATION
# ============================================================================
POLL_INTERVAL_MINUTES = 60  # Fetch odds every 60 minutes
LOOKBACK_HOURS = 24  # Only track games in next 24 hours

# ============================================================================
# BOOKMAKER CONFIGURATION
# ============================================================================
SHARP_BOOKS = ['pinnacle', 'betfair']  # Market-efficient books
SOFT_BOOKS = ['draftkings', 'fanduel', 'bet365', 'betmgm']  # Slower to adjust
ALL_BOOKS = SHARP_BOOKS + SOFT_BOOKS

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = './logs/betting_bot.log'

# ============================================================================
# BETTING CONFIGURATION
# ============================================================================
MIN_EDGE_PERCENT = 5.0  # Minimum edge % to flag as value bet
MIN_PROBABILITY = 0.35  # Minimum probability threshold
KELLY_FRACTION = 0.25  # Use quarter-kelly for safety
DEFAULT_BANKROLL = 1000.0  # Default bankroll for calculations
MAX_BET_PERCENT = 0.05  # Maximum 5% of bankroll per bet

# ============================================================================
# VALIDATION
# ============================================================================
if not ODDS_API_KEY:
    raise ValueError("❌ ODDS_API_KEY not found in .env file")

print("✅ Configuration loaded successfully")

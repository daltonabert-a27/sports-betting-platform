"""
SQLAlchemy database models for Sports Betting Analytics Platform
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from config.settings import DATABASE_URL

# ============================================================================
# DATABASE SETUP
# ============================================================================
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============================================================================
# DATABASE MODELS
# ============================================================================

class Game(Base):
    """Represents a matchup between two teams."""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    odds_api_id = Column(String, unique=True, index=True)  # External API ID
    league = Column(String, index=True)  # e.g., 'NFL', 'EPL', 'NHL'
    home_team = Column(String, index=True)
    away_team = Column(String, index=True)
    commence_time = Column(DateTime, index=True)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    result = Column(String, nullable=True)  # 'H', 'A', 'D' (home, away, draw)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OddsSnapshot(Base):
    """Stores historical odds for each game/bookmaker combo."""
    __tablename__ = "odds_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, index=True)
    bookmaker = Column(String, index=True)  # e.g., 'pinnacle', 'draftkings'
    home_odds = Column(Float)  # Decimal odds
    away_odds = Column(Float)
    draw_odds = Column(Float, nullable=True)  # For sports with draws
    home_implied_prob = Column(Float)  # Calculated: 1/odds
    away_implied_prob = Column(Float)
    draw_implied_prob = Column(Float, nullable=True)
    snapshot_time = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ValueBet(Base):
    """Tracks identified +EV (positive expected value) bets."""
    __tablename__ = "value_bets"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, index=True)
    home_team = Column(String)
    away_team = Column(String)
    betting_selection = Column(String)  # 'Home', 'Away', 'Draw'
    my_probability = Column(Float)  # My model's probability
    market_probability = Column(Float)  # Market's implied probability
    offered_odds = Column(Float)  # Bookmaker's decimal odds
    fair_odds = Column(Float)  # 1/my_probability
    edge_percent = Column(Float)  # (fair_odds / offered_odds - 1) * 100
    bookmaker = Column(String)
    kelly_fraction = Column(Float)  # Recommended bet size (Kelly Criterion)
    recommended_stake = Column(Float)  # Dollar amount to bet
    identified_at = Column(DateTime, default=datetime.utcnow)
    is_bet_placed = Column(Boolean, default=False)
    result = Column(String, nullable=True)  # 'Win', 'Loss', 'Void', 'Pending'


class BetResult(Base):
    """Tracks actual bets placed and their outcomes."""
    __tablename__ = "bet_results"
    
    id = Column(Integer, primary_key=True, index=True)
    value_bet_id = Column(Integer)  # Reference to ValueBet
    bookmaker = Column(String)
    selection = Column(String)
    odds_at_bet = Column(Float)
    stake = Column(Float)
    result = Column(String)  # 'Win', 'Loss', 'Void'
    pnl = Column(Float)  # Profit/Loss
    closing_line_value = Column(Float)  # Odds at game start vs odds at bet time
    placed_at = Column(DateTime, default=datetime.utcnow)
    settled_at = Column(DateTime, nullable=True)


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_db():
    """Dependency injection for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")

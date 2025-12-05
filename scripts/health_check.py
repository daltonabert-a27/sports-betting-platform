"""
Monitor data quality and ingestion health
"""
from models.database import SessionLocal, Game, OddsSnapshot
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthCheck:
    """Monitor data quality and ingestion health."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def check_data_freshness(self):
        """Ensure data is being collected regularly."""
        latest_snapshot = (
            self.db.query(OddsSnapshot)
            .order_by(OddsSnapshot.snapshot_time.desc())
            .first()
        )
        
        if not latest_snapshot:
            logger.error("❌ No odds snapshots in database!")
            return False
        
        age_minutes = (datetime.utcnow() - latest_snapshot.snapshot_time).total_seconds() / 60
        
        if age_minutes > 120:  # Alert if data older than 2 hours
            logger.warning(f"⚠️ Data is {age_minutes:.0f} minutes old")
            return False
        
        logger.info(f"✅ Data is fresh ({age_minutes:.0f} min old)")
        return True
    
    def check_game_count(self):
        """Verify we have games in the database."""
        count = self.db.query(Game).count()
        future_games = self.db.query(Game).filter(
            Game.commence_time > datetime.utcnow()
        ).count()
        
        logger.info(f"📊 Total games: {count}, Future games: {future_games}")
        return future_games > 0
    
    def check_bookmaker_coverage(self):
        """Ensure we're getting odds from multiple bookmakers."""
        bookmakers = (
            self.db.query(OddsSnapshot.bookmaker)
            .distinct()
            .all()
        )

        # Each item is a Row; extract the actual string value
        bookmaker_names = [row[0] for row in bookmakers]

        logger.info(f"📡 Covered bookmakers: {', '.join(bookmaker_names)}")
        return len(bookmaker_names) >= 3

    
    def run_all_checks(self):
        """Run all health checks."""
        print("\n" + "="*50)
        print("🏥 HEALTH CHECK REPORT")
        print("="*50)
        
        checks = [
            ("Data Freshness", self.check_data_freshness()),
            ("Game Count", self.check_game_count()),
            ("Bookmaker Coverage", self.check_bookmaker_coverage())
        ]
        
        for check_name, result in checks:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{check_name}: {status}")
        
        all_passed = all(result for _, result in checks)
        print("="*50)
        return all_passed


if __name__ == "__main__":
    health = HealthCheck()
    health.run_all_checks()

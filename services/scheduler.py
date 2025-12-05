"""
Background scheduler for automated data polling
"""
import schedule
import time
import logging
from services.odds_fetcher import OddsFetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PollingScheduler:
    """Manages background data polling."""
    
    def __init__(self, poll_interval_minutes=60):
        self.poll_interval = poll_interval_minutes
        self.fetcher = OddsFetcher()
    
    def job_fetch_nba_odds(self):
        """Scheduled job for NBA odds."""
        logger.info("🔄 Starting NBA odds fetch...")
        try:
            count = self.fetcher.ingest_odds(sport='basketball_nba')
            logger.info(f"✅ NBA fetch complete: {count} snapshots")
        except Exception as e:
            logger.error(f"❌ NBA fetch failed: {e}")
    
    def job_fetch_epl_odds(self):
        """Scheduled job for EPL (Soccer) odds."""
        logger.info("🔄 Starting EPL odds fetch...")
        try:
            count = self.fetcher.ingest_odds(sport='soccer_epl')
            logger.info(f"✅ EPL fetch complete: {count} snapshots")
        except Exception as e:
            logger.error(f"❌ EPL fetch failed: {e}")
    
    def job_fetch_nfl_odds(self):
        """Scheduled job for NFL odds."""
        logger.info("🔄 Starting NFL odds fetch...")
        try:
            count = self.fetcher.ingest_odds(sport='americanfootball_nfl')
            logger.info(f"✅ NFL fetch complete: {count} snapshots")
        except Exception as e:
            logger.error(f"❌ NFL fetch failed: {e}")
    
    def start(self):
        """Start the scheduler."""
        schedule.every(self.poll_interval).minutes.do(self.job_fetch_nba_odds)
        schedule.every(self.poll_interval).minutes.do(self.job_fetch_epl_odds)
        schedule.every(self.poll_interval).minutes.do(self.job_fetch_nfl_odds)
        
        logger.info(f"📅 Scheduler started (interval: {self.poll_interval} min)")
        logger.info("Jobs scheduled: NBA, EPL, NFL")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("⏹️  Scheduler stopped by user")


# Usage
if __name__ == "__main__":
    scheduler = PollingScheduler(poll_interval_minutes=60)
    scheduler.start()

"""
Fetches real-time odds from The Odds API (v4) using the /odds endpoint.
"""
import requests
import logging
from datetime import datetime, timedelta
from config.settings import (
    ODDS_API_KEY, ODDS_API_BASE, LOOKBACK_HOURS, ALL_BOOKS
)
from models.database import SessionLocal, Game, OddsSnapshot
from sqlalchemy.exc import IntegrityError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OddsFetcher:
    """Fetches real-time odds from The Odds API."""

    def __init__(self):
        self.api_key = ODDS_API_KEY
        self.base_url = ODDS_API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SportsBettingBot/1.0'
        })

    def get_upcoming_odds(self, sport='basketball_nba', hours_ahead=LOOKBACK_HOURS):
        """
        Fetch upcoming games + odds from The Odds API /odds endpoint.

        Args:
            sport: League identifier (e.g., 'basketball_nba', 'soccer_epl')
            hours_ahead: Only fetch games starting within N hours

        Returns:
            List of event objects (each includes bookmakers and markets)
        """
        endpoint = f'{self.base_url}/sports/{sport}/odds'

        # /odds requires at least regions; markets defaults to h2h if omitted, but
        # specifying h2h explicitly keeps things clear and matches docs.[web:61]
        params = {
            'apiKey': self.api_key,
            'regions': 'us,uk,eu',
            'markets': 'h2h',
            'oddsFormat': 'decimal',
            'dateFormat': 'iso',
            'commenceTimeTo': (
                datetime.utcnow() + timedelta(hours=hours_ahead)
            ).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }

        try:
            resp = self.session.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                logger.error(f"Unexpected response format from odds endpoint: {data}")
                return []
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to fetch odds (HTTP error): {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch odds (network error): {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to parse odds response: {e}")
            return []

    def ingest_odds(self, sport='basketball_nba'):
        """
        Main ingestion pipeline:
        1. Fetch upcoming games + odds from /odds
        2. For each game, create/update Game record
        3. For each bookmaker, calculate implied probabilities and store OddsSnapshot

        Returns:
            Count of ingested odds snapshots
        """
        db = SessionLocal()
        events = self.get_upcoming_odds(sport)

        if not events:
            logger.warning("No events returned from odds endpoint")
            db.close()
            return 0

        ingested_count = 0

        for event in events:
            try:
                event_id = event.get('id')
                home_team = event.get('home_team')
                away_team = event.get('away_team')
                commence_time_str = event.get('commence_time')

                if not (event_id and home_team and away_team and commence_time_str):
                    continue

                # Parse commence_time (ISO 8601 with Z suffix)
                commence_time = datetime.fromisoformat(
                    commence_time_str.replace('Z', '+00:00')
                )

                # 1. Create/Update Game record
                existing = db.query(Game).filter_by(odds_api_id=event_id).first()
                if not existing:
                    game = Game(
                        odds_api_id=event_id,
                        league=sport.upper(),
                        home_team=home_team,
                        away_team=away_team,
                        commence_time=commence_time,
                    )
                    db.add(game)
                    db.commit()
                    db.refresh(game)
                else:
                    game = existing

                # 2. Store odds snapshots from bookmakers
                bookmakers = event.get('bookmakers', [])
                if not bookmakers:
                    continue

                for bookmaker_data in bookmakers:
                    bookmaker_key = bookmaker_data.get('key')
                    if not bookmaker_key:
                        continue

                    # Optionally filter to known books
                    if ALL_BOOKS and bookmaker_key not in ALL_BOOKS:
                        continue

                    markets = bookmaker_data.get('markets', [])
                    if not markets:
                        continue

                    # We requested only h2h, so take the first market
                    market = markets[0]
                    outcomes = market.get('outcomes', [])
                    if not outcomes:
                        continue

                    # Map outcome name -> price
                    outcome_map = {o.get('name'): o.get('price') for o in outcomes}

                    home_odds = outcome_map.get(home_team)
                    away_odds = outcome_map.get(away_team)
                    draw_odds = outcome_map.get('Draw')

                    if not home_odds or not away_odds:
                        continue

                    # Calculate implied probabilities
                    home_prob = 1.0 / home_odds
                    away_prob = 1.0 / away_odds
                    draw_prob = 1.0 / draw_odds if draw_odds else None

                    snapshot = OddsSnapshot(
                        game_id=game.id,
                        bookmaker=bookmaker_key,
                        home_odds=home_odds,
                        away_odds=away_odds,
                        draw_odds=draw_odds,
                        home_implied_prob=home_prob,
                        away_implied_prob=away_prob,
                        draw_implied_prob=draw_prob,
                    )
                    db.add(snapshot)
                    ingested_count += 1

                db.commit()
                logger.info(f"✅ Ingested odds for {game.home_team} vs {game.away_team}")

            except IntegrityError:
                db.rollback()
                logger.debug("Duplicate snapshot, skipping")
            except Exception as e:
                db.rollback()
                logger.error(f"Error ingesting event {event.get('id')}: {e}")

        db.close()
        return ingested_count


if __name__ == "__main__":
    fetcher = OddsFetcher()
    count = fetcher.ingest_odds(sport='basketball_nba')
    print(f"Ingested {count} odds snapshots")

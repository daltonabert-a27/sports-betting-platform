"""
Market analysis and consensus probability calculation
"""
from models.database import SessionLocal, Game, OddsSnapshot
from sqlalchemy import desc
import logging

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Analyzes market odds to identify consensus probabilities."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def get_latest_snapshot_for_game(self, game_id):
        """Get the most recent odds snapshot for a game across all bookmakers."""
        snapshots = (
            self.db.query(OddsSnapshot)
            .filter_by(game_id=game_id)
            .order_by(desc(OddsSnapshot.snapshot_time))
            .all()
        )
        return snapshots
    
    def calculate_vig(self, home_prob, away_prob, draw_prob=None):
        """
        Calculate bookmaker's margin (vig/juice).
        
        Total implied probability > 1.0 due to vig.
        Vig = Total Prob - 1.0
        
        Returns:
            Dictionary with vig info
        """
        total_prob = home_prob + away_prob + (draw_prob or 0)
        vig = total_prob - 1.0
        vig_percent = vig / total_prob * 100 if total_prob > 0 else 0
        
        return {
            'total_probability': total_prob,
            'vig': vig,
            'vig_percent': vig_percent
        }
    
    def remove_vig(self, home_prob, away_prob, draw_prob=None):
        """
        De-vig odds to get fair probability.
        
        Formula: Fair Prob = Implied Prob / (1 + Vig)
        """
        vig_data = self.calculate_vig(home_prob, away_prob, draw_prob)
        
        if vig_data['vig'] == 0:
            return {
                'home': home_prob,
                'away': away_prob,
                'draw': draw_prob,
                'vig_removed': 0
            }
        
        fair_home = home_prob / (1 + vig_data['vig'])
        fair_away = away_prob / (1 + vig_data['vig'])
        fair_draw = (draw_prob / (1 + vig_data['vig'])) if draw_prob else None
        
        return {
            'home': fair_home,
            'away': fair_away,
            'draw': fair_draw,
            'vig_removed': vig_data['vig_percent']
        }
    
    def get_market_consensus(self, game_id, use_sharp_only=True):
        """
        Calculate consensus probability from market.
        
        Args:
            game_id: Game ID
            use_sharp_only: If True, only use sharp books (Pinnacle, Betfair)
        
        Returns:
            Consensus probability dictionary
        """
        snapshots = self.get_latest_snapshot_for_game(game_id)
        
        if not snapshots:
            return None
        
        if use_sharp_only:
            snapshots = [s for s in snapshots if s.bookmaker in ['pinnacle', 'betfair']]
        
        if not snapshots:
            logger.warning(f"No sharp book snapshots for game {game_id}")
            return None
        
        # Average implied probabilities
        avg_home_prob = sum(s.home_implied_prob for s in snapshots) / len(snapshots)
        avg_away_prob = sum(s.away_implied_prob for s in snapshots) / len(snapshots)
        avg_draw_prob = None

        # Only calculate draw probability if the market actually has draws
        if snapshots[0].draw_implied_prob is not None:
            avg_draw_prob = sum(s.draw_implied_prob for s in snapshots) / len(snapshots)

        return {
            'home_probability': avg_home_prob,
            'away_probability': avg_away_prob,
            'draw_probability': avg_draw_prob,
            'source_count': len(snapshots),
            'consensus_type': 'sharp' if use_sharp_only else 'all'
        }

    
    def identify_soft_book_discrepancies(self, game_id, min_edge_percent=5.0):
        """
        Compare soft book odds vs sharp book consensus.
        If soft book is paying significantly more, flag it.
        
        Args:
            game_id: Game ID
            min_edge_percent: Minimum edge % to flag (e.g., 5%)
        
        Returns:
            List of discrepancies
        """
        snapshots = self.get_latest_snapshot_for_game(game_id)
        consensus = self.get_market_consensus(game_id, use_sharp_only=True)
        
        if not consensus:
            return []
        
        discrepancies = []
        
        # Compare each soft book to consensus
        soft_snapshots = [s for s in snapshots if s.bookmaker in ['draftkings', 'fanduel', 'bet365', 'betmgm']]
        
        for snap in soft_snapshots:
            # Check home side
            home_fair_odds = 1.0 / consensus['home_probability']
            home_edge = ((snap.home_odds / home_fair_odds) - 1) * 100
            
            if home_edge >= min_edge_percent:
                discrepancies.append({
                    'bookmaker': snap.bookmaker,
                    'selection': 'Home',
                    'offered_odds': snap.home_odds,
                    'fair_odds': home_fair_odds,
                    'edge_percent': home_edge,
                    'implied_prob_soft': snap.home_implied_prob,
                    'implied_prob_consensus': consensus['home_probability']
                })
            
            # Check away side
            away_fair_odds = 1.0 / consensus['away_probability']
            away_edge = ((snap.away_odds / away_fair_odds) - 1) * 100
            
            if away_edge >= min_edge_percent:
                discrepancies.append({
                    'bookmaker': snap.bookmaker,
                    'selection': 'Away',
                    'offered_odds': snap.away_odds,
                    'fair_odds': away_fair_odds,
                    'edge_percent': away_edge,
                    'implied_prob_soft': snap.away_implied_prob,
                    'implied_prob_consensus': consensus['away_probability']
                })
        
        return discrepancies

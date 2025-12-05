"""
Identifies and tracks +EV (positive expected value) bets
"""
from models.database import SessionLocal, Game, OddsSnapshot, ValueBet
from services.market_analyzer import MarketAnalyzer
from config.settings import (
    MIN_EDGE_PERCENT, MIN_PROBABILITY, KELLY_FRACTION, DEFAULT_BANKROLL, MAX_BET_PERCENT
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValueFinder:
    """Identifies and tracks +EV (positive expected value) bets."""
    
    def __init__(self):
        self.db = SessionLocal()
        self.analyzer = MarketAnalyzer()
    
    def calculate_kelly_bet(self, win_prob, odds, bankroll=DEFAULT_BANKROLL, kelly_fraction=KELLY_FRACTION):
        """
        Calculate Kelly Criterion bet size.
        
        Full Kelly: f* = (bp - q) / b
          where b = odds - 1, p = win probability, q = 1 - p
        
        Fractional Kelly: Use f* * fraction to reduce variance
        
        Args:
            win_prob: Probability of winning (0-1)
            odds: Decimal odds
            bankroll: Total bankroll
            kelly_fraction: Fraction of kelly to use
        
        Returns:
            Recommended bet size in dollars
        """
        b = odds - 1
        q = 1 - win_prob
        
        if b <= 0 or odds <= 1:
            return 0
        
        full_kelly = (b * win_prob - q) / b
        
        # Use fractional kelly for safety
        kelly_pct = max(0, full_kelly * kelly_fraction)
        
        bet_size = bankroll * kelly_pct
        return max(0, min(bet_size, bankroll * MAX_BET_PERCENT))  # Cap at max percent
    
    def find_value_bets(self, min_edge_percent=MIN_EDGE_PERCENT, min_probability=MIN_PROBABILITY):
        """
        Scan all upcoming games for value.
        
        Strategy: Soft book vs Sharp book discrepancy
        
        Args:
            min_edge_percent: Minimum edge % to flag
            min_probability: Minimum probability threshold
        
        Returns:
            List of ValueBet objects
        """
        db = SessionLocal()
        games = db.query(Game).filter(
            Game.result.is_(None),  # Upcoming games only
            Game.commence_time > datetime.utcnow()
        ).all()
        
        value_bets = []
        
        for game in games:
            # Get market consensus (sharp book average)
            consensus = self.analyzer.get_market_consensus(game.id, use_sharp_only=True)
            if not consensus:
                continue
            
            # Find soft book discrepancies
            discrepancies = self.analyzer.identify_soft_book_discrepancies(
                game.id,
                min_edge_percent=min_edge_percent
            )
            
            for disc in discrepancies:
                if disc['selection'] == 'Home':
                    my_prob = consensus['home_probability']
                else:
                    my_prob = consensus['away_probability']
                
                if my_prob < min_probability:
                    continue
                
                # Calculate recommended bet size
                kelly_bet = self.calculate_kelly_bet(
                    win_prob=my_prob,
                    odds=disc['offered_odds'],
                    bankroll=DEFAULT_BANKROLL,
                    kelly_fraction=KELLY_FRACTION
                )
                
                value_bet = ValueBet(
                    game_id=game.id,
                    home_team=game.home_team,
                    away_team=game.away_team,
                    betting_selection=disc['selection'],
                    my_probability=my_prob,
                    market_probability=disc['implied_prob_consensus'],
                    offered_odds=disc['offered_odds'],
                    fair_odds=disc['fair_odds'],
                    edge_percent=disc['edge_percent'],
                    bookmaker=disc['bookmaker'],
                    kelly_fraction=KELLY_FRACTION,
                    recommended_stake=kelly_bet
                )
                
                db.add(value_bet)
                value_bets.append(value_bet)
                
                # Print to console
                print(f"\n💰 VALUE BET FOUND")
                print(f"  Match: {game.home_team} vs {game.away_team}")
                print(f"  Selection: {disc['selection']}")
                print(f"  My Fair Probability: {my_prob:.1%}")
                print(f"  Market Probability: {disc['implied_prob_consensus']:.1%}")
                print(f"  Offered Odds: {disc['offered_odds']}")
                print(f"  Fair Odds: {disc['fair_odds']:.2f}")
                print(f"  Edge: {disc['edge_percent']:.1f}%")
                print(f"  Recommended Bet: ${kelly_bet:.2f}")
                print(f"  Bookmaker: {disc['bookmaker']}")
        
        db.commit()
        db.close()
        
        logger.info(f"✅ Found {len(value_bets)} value bets")
        return value_bets


# Usage
if __name__ == "__main__":
    finder = ValueFinder()
    bets = finder.find_value_bets()
    print(f"\nTotal opportunities: {len(bets)}")

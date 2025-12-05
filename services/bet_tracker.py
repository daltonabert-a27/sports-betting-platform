"""
Tracks placed bets and their outcomes
"""
from models.database import SessionLocal, BetResult
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BetTracker:
    """Tracks all placed bets and outcomes."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def record_bet(self, value_bet_id, bookmaker, selection, odds, stake):
        """
        Record a placed bet.
        
        Args:
            value_bet_id: Reference to ValueBet entry
            bookmaker: Which sportsbook
            selection: What you bet on
            odds: Decimal odds at time of bet
            stake: Amount wagered
        
        Returns:
            BetResult object
        """
        bet = BetResult(
            value_bet_id=value_bet_id,
            bookmaker=bookmaker,
            selection=selection,
            odds_at_bet=odds,
            stake=stake,
            placed_at=datetime.utcnow()
        )
        self.db.add(bet)
        self.db.commit()
        logger.info(f"📝 Recorded bet: ${stake} @ {odds} on {selection}")
        return bet
    
    def settle_bet(self, bet_id, result, closing_odds=None):
        """
        Mark a bet as won/lost.
        
        Args:
            bet_id: BetResult ID
            result: 'WIN', 'LOSS', or 'VOID'
            closing_odds: Odds at game start (for CLV calculation)
        
        Returns:
            Updated BetResult object
        """
        bet = self.db.query(BetResult).filter_by(id=bet_id).first()
        
        if not bet:
            logger.error(f"Bet {bet_id} not found")
            return None
        
        if result == 'WIN':
            pnl = bet.stake * (bet.odds_at_bet - 1)
        elif result == 'LOSS':
            pnl = -bet.stake
        else:  # Void
            pnl = 0
        
        # Calculate Closing Line Value (CLV)
        clv = None
        if closing_odds:
            clv = (closing_odds / bet.odds_at_bet - 1) * 100
        
        bet.result = result
        bet.pnl = pnl
        bet.closing_line_value = clv
        bet.settled_at = datetime.utcnow()
        
        self.db.commit()
        logger.info(f"✅ Settled bet {bet_id}: {result} (P&L: ${pnl:.2f})")
        return bet
    
    def get_performance_report(self):
        """Generate performance statistics."""
        bets = self.db.query(BetResult).all()
        
        if not bets:
            logger.warning("No bets found")
            return None
        
        df = pd.DataFrame([{
            'result': b.result,
            'pnl': b.pnl,
            'clv': b.closing_line_value,
            'odds': b.odds_at_bet,
            'stake': b.stake
        } for b in bets if b.result])
        
        if df.empty:
            return None
        
        report = {
            'total_bets': len(df),
            'wins': len(df[df['result'] == 'WIN']),
            'losses': len(df[df['result'] == 'LOSS']),
            'win_rate': len(df[df['result'] == 'WIN']) / len(df) * 100 if len(df) > 0 else 0,
            'total_staked': df['stake'].sum(),
            'total_pnl': df['pnl'].sum(),
            'roi': (df['pnl'].sum() / df['stake'].sum() * 100) if df['stake'].sum() > 0 else 0,
            'avg_clv': df['clv'].mean() if not df['clv'].isna().all() else 0
        }
        
        return report

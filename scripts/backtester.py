"""
Historical backtesting framework
"""
from models.database import SessionLocal, Game, OddsSnapshot
from config.settings import MIN_EDGE_PERCENT, KELLY_FRACTION, DEFAULT_BANKROLL
from datetime import datetime, timedelta
from sqlalchemy import and_
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Backtester:
    """Simulates historical betting to validate strategy edge."""
    
    def __init__(self, initial_bankroll=DEFAULT_BANKROLL):
        self.db = SessionLocal()
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
    
    def get_historical_games(self, sport='BASKETBALL_NBA', start_date=None, end_date=None):
        """Retrieve games that have already been played (have results)."""
        query = self.db.query(Game).filter(
            Game.league == sport,
            Game.result.isnot(None)  # Only completed games
        )
        
        if start_date:
            query = query.filter(Game.commence_time >= start_date)
        if end_date:
            query = query.filter(Game.commence_time <= end_date)
        
        return query.order_by(Game.commence_time.asc()).all()
    
    def calculate_kelly_bet(self, win_prob, odds, kelly_fraction=KELLY_FRACTION):
        """Calculate Kelly Criterion bet size."""
        b = odds - 1
        q = 1 - win_prob
        
        if b <= 0 or odds <= 1:
            return 0
        
        full_kelly = (b * win_prob - q) / b
        kelly_pct = max(0, full_kelly * kelly_fraction)
        
        bet_size = self.bankroll * kelly_pct
        return max(0, min(bet_size, self.bankroll * 0.05))  # Cap at 5%
    
    def simulate_strategy_soft_vs_sharp(self, games, min_edge_percent=MIN_EDGE_PERCENT, kelly_fraction=KELLY_FRACTION):
        """
        Backtest Strategy: Bet when soft book pays significantly more than sharp book.
        """
        results = []
        
        for game in games:
            # Get latest odds for this game
            sharp_snapshots = self.db.query(OddsSnapshot).filter(
                and_(
                    OddsSnapshot.game_id == game.id,
                    OddsSnapshot.bookmaker.in_(['pinnacle', 'betfair'])
                )
            ).all()
            
            soft_snapshots = self.db.query(OddsSnapshot).filter(
                and_(
                    OddsSnapshot.game_id == game.id,
                    OddsSnapshot.bookmaker.in_(['draftkings', 'fanduel', 'bet365'])
                )
            ).all()
            
            if not sharp_snapshots or not soft_snapshots:
                continue
            
            # Calculate sharp consensus (fair price)
            sharp_home_prob = sum(s.home_implied_prob for s in sharp_snapshots) / len(sharp_snapshots)
            sharp_away_prob = sum(s.away_implied_prob for s in sharp_snapshots) / len(sharp_snapshots)
            sharp_home_odds = 1.0 / sharp_home_prob
            sharp_away_odds = 1.0 / sharp_away_prob
            
            # Check if soft book offers better odds
            for soft in soft_snapshots:
                # Home side
                home_edge = ((soft.home_odds / sharp_home_odds) - 1) * 100
                if home_edge >= min_edge_percent:
                    kelly_bet = self.calculate_kelly_bet(sharp_home_prob, soft.home_odds, kelly_fraction)
                    
                    if game.result == 'H':
                        win = kelly_bet * (soft.home_odds - 1)
                        self.bankroll += win
                        result_str = "WIN"
                    else:
                        win = -kelly_bet
                        self.bankroll += win
                        result_str = "LOSS"
                    
                    results.append({
                        'game': f"{game.home_team} vs {game.away_team}",
                        'selection': 'Home',
                        'odds': soft.home_odds,
                        'stake': kelly_bet,
                        'result': result_str,
                        'pnl': win,
                        'bankroll': self.bankroll,
                        'edge_percent': home_edge
                    })
                
                # Away side
                away_edge = ((soft.away_odds / sharp_away_odds) - 1) * 100
                if away_edge >= min_edge_percent:
                    kelly_bet = self.calculate_kelly_bet(sharp_away_prob, soft.away_odds, kelly_fraction)
                    
                    if game.result == 'A':
                        win = kelly_bet * (soft.away_odds - 1)
                        self.bankroll += win
                        result_str = "WIN"
                    else:
                        win = -kelly_bet
                        self.bankroll += win
                        result_str = "LOSS"
                    
                    results.append({
                        'game': f"{game.home_team} vs {game.away_team}",
                        'selection': 'Away',
                        'odds': soft.away_odds,
                        'stake': kelly_bet,
                        'result': result_str,
                        'pnl': win,
                        'bankroll': self.bankroll,
                        'edge_percent': away_edge
                    })
        
        return results
    
    def generate_backtest_report(self, results_df):
        """Generate statistics from backtest results."""
        if results_df.empty:
            print("❌ No bets placed in backtest")
            return
        
        total_bets = len(results_df)
        wins = len(results_df[results_df['result'] == 'WIN'])
        losses = len(results_df[results_df['result'] == 'LOSS'])
        win_rate = wins / total_bets * 100
        
        total_staked = results_df['stake'].sum()
        total_pnl = results_df['pnl'].sum()
        roi = (total_pnl / total_staked) * 100 if total_staked > 0 else 0
        
        print("\n" + "="*60)
        print("📊 BACKTEST REPORT")
        print("="*60)
        print(f"Total Bets: {total_bets}")
        print(f"Wins: {wins} | Losses: {losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Total Staked: ${total_staked:.2f}")
        print(f"Total P&L: ${total_pnl:.2f}")
        print(f"ROI: {roi:.2f}%")
        print(f"Starting Bankroll: ${self.initial_bankroll:.2f}")
        print(f"Ending Bankroll: ${self.bankroll:.2f}")
        print("="*60)
        
        return {
            'total_bets': total_bets,
            'win_rate': win_rate,
            'roi': roi,
            'total_pnl': total_pnl,
            'final_bankroll': self.bankroll
        }


if __name__ == "__main__":
    backtester = Backtester(initial_bankroll=1000.0)
    
    # Get past 30 days of completed games
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    games = backtester.get_historical_games(start_date=start_date, end_date=end_date)
    print(f"Found {len(games)} completed games")
    
    results = backtester.simulate_strategy_soft_vs_sharp(games)
    results_df = pd.DataFrame(results)
    
    backtester.generate_backtest_report(results_df)
    
    # Save results for analysis
    results_df.to_csv('./data/backtest_results.csv', index=False)
    print("\n💾 Results saved to ./data/backtest_results.csv")

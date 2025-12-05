"""
Visualize backtest results
"""
import pandas as pd
import matplotlib.pyplot as plt
import os


def plot_bankroll_growth(csv_file):
    """Plot bankroll progression over time."""
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        return
    
    df = pd.read_csv(csv_file)
    
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(df)), df['bankroll'], marker='o', linewidth=2)
    plt.xlabel('Bet Number')
    plt.ylabel('Bankroll ($)')
    plt.title('Bankroll Progression - Soft vs Sharp Strategy')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('./data/bankroll_growth.png', dpi=150)
    print("📊 Saved: ./data/bankroll_growth.png")
    
    plt.figure(figsize=(10, 5))
    win_loss = df['result'].value_counts()
    plt.bar(['Wins', 'Losses'], [win_loss.get('WIN', 0), win_loss.get('LOSS', 0)], color=['green', 'red'])
    plt.ylabel('Count')
    plt.title('Win/Loss Distribution')
    plt.tight_layout()
    plt.savefig('./data/win_loss_dist.png', dpi=150)
    print("📊 Saved: ./data/win_loss_dist.png")


if __name__ == "__main__":
    plot_bankroll_growth('./data/backtest_results.csv')

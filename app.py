import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from models.database import SessionLocal, Game, OddsSnapshot, ValueBet

st.set_page_config(page_title="Sports Betting Analytics", layout="wide")

st.title("📊 Sports Betting Analytics Dashboard")

db = SessionLocal()

# Sidebar navigation
page = st.sidebar.selectbox("Go to", ["Upcoming Games", "Latest Value Bets"])

if page == "Upcoming Games":
    st.header("Upcoming Games (Next 24h)")

    now = datetime.now(timezone.utc)
    games = (
        db.query(Game)
        .filter(Game.commence_time > now)
        .order_by(Game.commence_time.asc())
        .all()
    )

    if not games:
        st.info("No upcoming games found in the database.")
    else:
        rows = []
        for g in games:
            rows.append(
                {
                    "League": g.league,
                    "Commence Time (UTC)": g.commence_time,
                    "Home Team": g.home_team,
                    "Away Team": g.away_team,
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch")

elif page == "Latest Value Bets":
    st.header("Latest Value Bets")

    bets = (
        db.query(ValueBet)
        .order_by(ValueBet.identified_at.desc())
        .limit(50)
        .all()
    )

    if not bets:
        st.info(
            "No value bets found yet. Let the scheduler run and then run services.value_finder."
        )
    else:
        rows = []
        for b in bets:
            rows.append(
                {
                    "Match": f"{b.home_team} vs {b.away_team}",
                    "Selection": b.betting_selection,
                    "Bookmaker": b.bookmaker,
                    "My Prob": f"{b.my_probability:.1%}",
                    "Market Prob": f"{b.market_probability:.1%}",
                    "Offered Odds": b.offered_odds,
                    "Fair Odds": round(b.fair_odds, 3),
                    "Edge %": round(b.edge_percent, 2),
                    "Kelly Stake": round(b.recommended_stake, 2),
                    "Identified At (UTC)": b.identified_at,
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

db.close()

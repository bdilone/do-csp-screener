#!/usr/bin/env python3
"""
DIGITAL OPTIONS — CSP DAILY SCREENER WITH DISCORD INTEGRATION
Automated trading opportunity scanner that posts to Discord webhook
Runs daily at 8 AM ET via GitHub Actions
"""

import json
import requests
import os
from datetime import datetime, timedelta

# ============================================================================
# CONFIG
# ============================================================================

TICKER_UNIVERSE = [
    "PLTR", "NVDA", "AMD", "COIN", "CRWV", "CBRS", "HOOD", "CRSP", "GOOG", "SQ"
]

EARNINGS_BLACKOUT = {
    "PLTR": "2026-11-02",
    "AMD": "2026-11-03",
    "COIN": "2026-10-29",
    "HOOD": "2026-11-04",
}

CSP_PARAMETERS = {
    "delta_min": 0.35,
    "delta_max": 0.40,
    "dte_target": 15,
    "weekly_return_min": 0.70,
    "max_single_position": 0.10,
    "account_size": 182431,
}

LIVE_PRICES = {
    "PLTR": 191.47,
    "NVDA": 225.07,
    "AMD": 630.22,
    "COIN": 195.02,
    "CRWV": 15.50,
    "CBRS": 22.80,
    "HOOD": 23.40,
    "CRSP": 126.90,
    "GOOG": 178.50,
    "SQ": 185.30,
}

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK_CSP')

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def check_earnings_blackout(ticker):
    """Flag if earnings fall within Oct 10 expiration window"""
    if ticker not in EARNINGS_BLACKOUT:
        return False

    earnings_date = datetime.strptime(EARNINGS_BLACKOUT[ticker], "%Y-%m-%d")
    expiration_date = datetime(2026, 10, 10)

    return earnings_date <= expiration_date

def calculate_csp_opportunity(ticker, current_price, strike_premium):
    """Calculate CSP metrics"""
    estimated_strike = current_price * 0.94
    collateral = estimated_strike * 100
    total_credit = strike_premium * 100
    pop = (1 - 0.38) * 100
    dte = CSP_PARAMETERS["dte_target"]
    weeks = dte / 7
    weekly_return = (total_credit / collateral) / weeks * 100

    max_profit = total_credit
    max_loss = (estimated_strike * 100) - total_credit
    ev = (pop/100 * max_profit) - ((1 - pop/100) * max_loss)

    return {
        "ticker": ticker,
        "current_price": current_price,
        "strike": round(estimated_strike, 2),
        "premium_per_contract": strike_premium,
        "total_credit": total_credit,
        "collateral": collateral,
        "pop": round(pop, 1),
        "weekly_return": round(weekly_return, 2),
        "ev": round(ev, 0),
        "dte": dte,
        "max_contracts": int(CSP_PARAMETERS["account_size"] *
                             CSP_PARAMETERS["max_single_position"] / collateral),
    }

def rank_opportunities(tickers, prices):
    """Rank opportunities by EV"""
    opportunities = []

    for ticker in tickers:
        if check_earnings_blackout(ticker):
            continue

        current_price = prices.get(ticker, 0)
        if not current_price:
            continue

        if ticker in ["NVDA", "AMD", "COIN"]:
            strike_premium = current_price * 0.025
        elif ticker in ["PLTR", "HOOD"]:
            strike_premium = current_price * 0.020
        else:
            strike_premium = current_price * 0.015

        opp = calculate_csp_opportunity(ticker, current_price, strike_premium)

        if opp["weekly_return"] >= CSP_PARAMETERS["weekly_return_min"]:
            opportunities.append(opp)

    ranked = sorted(opportunities, key=lambda x: x["ev"], reverse=True)
    return ranked[:3]

# ============================================================================
# DISCORD INTEGRATION
# ============================================================================

def send_to_discord(ranked_opps):
    """Post screener results to Discord webhook"""

    if not DISCORD_WEBHOOK:
        print("[ERROR] DISCORD_WEBHOOK_CSP not set in environment")
        return False

    today = datetime.now().strftime("%Y-%m-%d")

    # Build embed
    embed = {
        "title": "🚀 DO CSP DAILY DIGEST",
        "description": f"**{today}** | Oct 10 expiration (15 DTE) | Account: $182,431",
        "color": 65416,  # Green
        "fields": [],
        "footer": {"text": "Digital Options Trading System — Automated Scanner"}
    }

    if not ranked_opps:
        embed["description"] = "❌ No opportunities today. Market conditions not favorable."
        embed["color"] = 16711680  # Red
    else:
        for i, opp in enumerate(ranked_opps, 1):
            field = {
                "name": f"#{i} {opp['ticker']} ${opp['strike']}P | {opp['pop']}% PoP",
                "value": (
                    f"💰 **Premium:** ${opp['total_credit']:.2f}/contract\n"
                    f"📊 **Weekly Return:** {opp['weekly_return']}% | "
                    f"**EV:** ${opp['ev']}\n"
                    f"🎯 **Size:** {opp['max_contracts']} contracts max | "
                    f"**All-in:** ${opp['collateral'] * opp['max_contracts']:,.0f}\n"
                    f"⚡ **Action:** SELL {opp['max_contracts']} @ ${opp['strike']}"
                ),
                "inline": False
            }
            embed["fields"].append(field)

    payload = {
        "content": "📈 Your daily trading opportunities are ready.",
        "embeds": [embed]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        if response.status_code == 204:
            print(f"[SUCCESS] Posted to Discord at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return True
        else:
            print(f"[ERROR] Discord webhook failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Discord post failed: {e}")
        return False

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run screener and post to Discord"""

    print("=" * 70)
    print("DIGITAL OPTIONS — CSP DAILY SCREENER")
    print("=" * 70)
    print(f"Scan time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
    print(f"Tickers: {len(TICKER_UNIVERSE)}")
    print()

    # Rank opportunities
    ranked = rank_opportunities(TICKER_UNIVERSE, LIVE_PRICES)

    if not ranked:
        print("⚠️  No qualifying opportunities today.")
    else:
        print(f"✅ Found {len(ranked)} executable opportunities")
        for i, opp in enumerate(ranked, 1):
            print(f"  #{i} {opp['ticker']} ${opp['strike']}P → ${opp['weekly_return']}% weekly")
        print()

    # Send to Discord
    success = send_to_discord(ranked)

    if success:
        print("[DONE] Screener executed and posted to Discord")
        return 0
    else:
        print("[FAIL] Screener executed but Discord post failed")
        return 1

if __name__ == "__main__":
    exit(main())

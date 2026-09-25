import requests
import json
import os
from datetime import datetime, timedelta

# CONFIG
TICKER_UNIVERSE = ["PLTR", "NVDA", "AMD", "COIN", "CRWV", "CBRS", "HOOD", "CRSP", "GOOG", "SQ"]
DISCORD_WEBHOOK_CSP = os.getenv("DISCORD_WEBHOOK_CSP")

CSP_PARAMETERS = {
    "NVDA": {"premium_pct": 0.025, "delta_target": 0.35},
    "AMD": {"premium_pct": 0.025, "delta_target": 0.35},
    "COIN": {"premium_pct": 0.025, "delta_target": 0.35},
    "PLTR": {"premium_pct": 0.020, "delta_target": 0.35},
    "HOOD": {"premium_pct": 0.020, "delta_target": 0.35},
    "CRWV": {"premium_pct": 0.015, "delta_target": 0.35},
    "CBRS": {"premium_pct": 0.015, "delta_target": 0.35},
    "CRSP": {"premium_pct": 0.015, "delta_target": 0.35},
    "GOOG": {"premium_pct": 0.015, "delta_target": 0.35},
    "SQ": {"premium_pct": 0.015, "delta_target": 0.35},
}

EARNINGS_BLACKOUT = {
    "NVDA": "2026-10-15",
    "AMD": "2026-10-20",
    "COIN": "2026-10-28",
    "PLTR": "2026-11-05",
    "GOOG": "2026-10-29",
}

def get_live_price(ticker):
    """Fetch live stock price from Alpha Vantage"""
    try:
        api_key = os.getenv("ALPHA_VANTAGE_KEY", "demo")
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={api_key}"
        response = requests.get(url, timeout=5)
        data = response.json()
        if "Global Quote" in data and "05. price" in data["Global Quote"]:
            price_str = data["Global Quote"]["05. price"]
            if price_str:
                return float(price_str)
    except Exception as e:
        print(f"⚠️ Price fetch error for {ticker}: {e}")
    return None

def check_earnings_blackout(ticker, dte, earnings_date_str):
    """Check if trade expires through earnings"""
    try:
        expiry = datetime.now() + timedelta(days=dte)
        earnings = datetime.strptime(earnings_date_str, "%Y-%m-%d")
        return expiry >= earnings
    except:
        return False

def calculate_csp_opportunity(ticker, current_price):
    """Calculate CSP trade opportunity"""
    if not current_price or current_price < 5:
        return None
    
    params = CSP_PARAMETERS.get(ticker, {"premium_pct": 0.015, "delta_target": 0.35})
    
    # Strike at 94% of current price
    strike = round(current_price * 0.94, 2)
    
    # Premium calculation
    premium_per_share = current_price * params["premium_pct"]
    total_credit = premium_per_share * 100
    
    # Collateral required
    collateral = strike * 100
    
    # DTE: 21 days
    dte = 21
    
    # Weekly return
    weekly_return = (total_credit / collateral) / (dte / 7) * 100
    
    # PoP (simplified: 62%)
    pop = 62.0
    
    # Breakeven
    breakeven = strike - premium_per_share
    
    # EV (simplified positive check)
    max_gain = total_credit
    max_loss = (strike - breakeven) * 100
    ev = (pop / 100 * max_gain) - ((1 - pop / 100) * max_loss)
    
    return {
        "ticker": ticker,
        "strike": strike,
        "premium": round(premium_per_share, 2),
        "total_credit": round(total_credit, 0),
        "collateral": int(collateral),
        "dte": dte,
        "weekly_return": round(weekly_return, 2),
        "pop": pop,
        "breakeven": round(breakeven, 2),
        "ev": round(ev, 2),
        "current_price": current_price,
    }

def rank_opportunities(opportunities):
    """Filter for EXECUTE tier (2.0%+ weekly return), rank by weekly return"""
    execute = [o for o in opportunities if o["weekly_return"] >= 2.0]
    execute.sort(key=lambda x: x["weekly_return"], reverse=True)
    return execute

def send_to_discord(execute_opportunities):
    """Post screener to Discord with locked format"""
    if not DISCORD_WEBHOOK_CSP:
        print("⚠️ DISCORD_WEBHOOK_CSP not set")
        return
    
    if not execute_opportunities:
        message = "🚀 DO CSP Screener | " + datetime.now().strftime("%B %d, %Y") + "\nBy\nDigital Options\nInvest. Create. Grow.\n\n⚠️ NO EXECUTE OPPORTUNITIES TODAY\n\nWaiting for better setups..."
        payload = {"content": message}
        try:
            requests.post(DISCORD_WEBHOOK_CSP, json=payload, timeout=10)
        except Exception as e:
            print(f"Discord error: {e}")
        return
    
    # Build locked format
    lines = [
        "🚀 DO CSP Screener | " + datetime.now().strftime("%B %d, %Y"),
        "By",
        "Digital Options",
        "Invest. Create. Grow.",
        "",
        "✅ EXECUTE (2.0%+ trade return)",
        ""
    ]
    
    for i, opp in enumerate(execute_opportunities, 1):
        lines.append(f"{i}. {opp['ticker']}")
        lines.append(f"Current Price: ${opp['current_price']:.2f}")
        lines.append(f"Trade Return: {opp['weekly_return']:.2f}%")
        lines.append(f"📅 DTE: {opp['dte']} | Strike: ${opp['strike']:.2f}")
        lines.append(f"💰 Premium Received: ${int(opp['total_credit'])}")
        lines.append(f"💳 Requirement: ${opp['collateral']:,}")
        lines.append("")
    
    lines.append("—")
    lines.append("")
    lines.append("⚡ Reply with DO [TICKER] for full analysis + execution.")
    
    message = "\n".join(lines)
    payload = {"content": message}
    
    try:
        response = requests.post(DISCORD_WEBHOOK_CSP, json=payload, timeout=10)
        print(f"✅ Discord post status: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord error: {e}")

def main():
    """Main screener loop"""
    print("🚀 Starting CSP Screener...\n")
    
    opportunities = []
    
    for ticker in TICKER_UNIVERSE:
        current_price = get_live_price(ticker)
        
        if not current_price:
            print(f"⚠️ Could not fetch price for {ticker}")
            continue
        
        # Check earnings blackout
        if ticker in EARNINGS_BLACKOUT:
            if check_earnings_blackout(ticker, 21, EARNINGS_BLACKOUT[ticker]):
                print(f"⏭️ {ticker} blackout (earnings within 21 DTE)")
                continue
        
        # Calculate opportunity
        opp = calculate_csp_opportunity(ticker, current_price)
        if opp:
            opportunities.append(opp)
            print(f"✅ {ticker}: {opp['weekly_return']:.2f}% weekly return")
    
    # Rank and execute
    execute_tier = rank_opportunities(opportunities)
    print(f"\n📊 Total scanned: {len(opportunities)}")
    print(f"✅ EXECUTE tier: {len(execute_tier)}\n")
    
    # Post to Discord
    send_to_discord(execute_tier)
    print("✅ Screener complete")

if __name__ == "__main__":
    main()

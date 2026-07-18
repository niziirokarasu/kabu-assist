"""株価・指数データの取得 (yfinance使用・無料)"""
import json
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent


def load_config():
    with open(ROOT / "config.json", encoding="utf-8") as f:
        return json.load(f)


def load_knowledge():
    with open(ROOT / "knowledge" / "sector_map.json", encoding="utf-8") as f:
        sector_map = json.load(f)
    with open(ROOT / "knowledge" / "event_calendar.json", encoding="utf-8") as f:
        calendar = json.load(f)
    return sector_map, calendar


def fetch_ticker_summary(ticker: str) -> dict | None:
    """1銘柄の直近データを取得。直近5営業日の終値から変動率も計算"""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="7d", interval="1d")
        if hist.empty or len(hist) < 2:
            return None
        closes = hist["Close"]
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        week_ago = float(closes.iloc[0])
        day_chg = (last - prev) / prev * 100
        week_chg = (last - week_ago) / week_ago * 100
        info = {}
        try:
            info = t.fast_info or {}
        except Exception:
            pass
        return {
            "ticker": ticker,
            "price": round(last, 2),
            "day_change_pct": round(day_chg, 2),
            "week_change_pct": round(week_chg, 2),
            "year_high": round(float(getattr(info, "year_high", 0) or 0), 2),
            "year_low": round(float(getattr(info, "year_low", 0) or 0), 2),
        }
    except Exception as e:
        print(f"[warn] {ticker} の取得失敗: {e}")
        return None


def fetch_market_snapshot(config: dict) -> dict:
    """指数+ウォッチリスト全体のスナップショットを取得"""
    snapshot = {"indices": [], "watchlist": []}

    for ticker, name in config["indices"].items():
        d = fetch_ticker_summary(ticker)
        if d:
            d["name"] = name
            snapshot["indices"].append(d)

    for market, tickers in config["watchlist"].items():
        for ticker in tickers:
            d = fetch_ticker_summary(ticker)
            if d:
                d["market"] = market
                snapshot["watchlist"].append(d)

    return snapshot


if __name__ == "__main__":
    cfg = load_config()
    snap = fetch_market_snapshot(cfg)
    print(json.dumps(snap, ensure_ascii=False, indent=2))

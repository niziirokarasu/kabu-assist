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


def _read_fast_info(info, key: str) -> float:
    """fast_info は yfinance のバージョンによって属性アクセス / 辞書アクセスの
    どちらでも返りうるため、両方を試してから 0 にフォールバックする"""
    val = None
    try:
        val = info[key]
    except Exception:
        val = getattr(info, key, None)
    try:
        return round(float(val or 0), 2)
    except (TypeError, ValueError):
        return 0.0


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
            "year_high": _read_fast_info(info, "year_high"),
            "year_low": _read_fast_info(info, "year_low"),
        }
    except Exception as e:
        print(f"[warn] {ticker} の取得失敗: {e}")
        return None


def fetch_market_snapshot(config: dict) -> dict:
    """指数+ウォッチリスト全体のスナップショットを取得"""
    snapshot = {"indices": [], "watchlist": []}
    missing = []

    for ticker, name in config["indices"].items():
        d = fetch_ticker_summary(ticker)
        if d:
            d["name"] = name
            snapshot["indices"].append(d)
        else:
            missing.append(f"{name}({ticker})")

    for market, tickers in config["watchlist"].items():
        for ticker in tickers:
            d = fetch_ticker_summary(ticker)
            if d:
                d["market"] = market
                snapshot["watchlist"].append(d)
            else:
                missing.append(ticker)

    if missing:
        # 銘柄コードの誤りに気づけるよう、取得できなかった分をまとめて表示する
        print(f"[warn] データ取得できず除外: {', '.join(missing)}")

    return snapshot


if __name__ == "__main__":
    cfg = load_config()
    snap = fetch_market_snapshot(cfg)
    print(json.dumps(snap, ensure_ascii=False, indent=2))

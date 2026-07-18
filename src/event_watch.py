"""急変動監視: 市場時間中に定期実行され、しきい値超えの動きがあれば随時Discordに通知する。
同じアラートを繰り返さないよう、状態ファイル(.alert_state.json)で当日の通知済みを記録する
(GitHub Actionsのキャッシュで永続化)"""
import json
from datetime import date
from pathlib import Path

from analyze import generate_event_alert
from fetch_data import fetch_market_snapshot, load_config, load_knowledge
from notify import post_to_discord

STATE_FILE = Path(__file__).resolve().parent.parent / ".alert_state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if state.get("date") == date.today().isoformat():
                return state
        except Exception:
            pass
    return {"date": date.today().isoformat(), "alerted": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def detect_triggers(snapshot: dict, thresholds: dict, alerted: list) -> list[dict]:
    triggers = []

    for idx in snapshot["indices"]:
        key = f"idx:{idx['ticker']}"
        # VIXは水準で判定
        if idx["ticker"] == "^VIX":
            if idx["price"] >= thresholds["vix_level"] and key not in alerted:
                triggers.append({"type": "VIX急騰", "detail": f"{idx['name']} が {idx['price']} (しきい値{thresholds['vix_level']}超え)。市場の警戒感が強い", "key": key})
            continue
        # ドル円は専用しきい値
        limit = thresholds["usdjpy_move_pct"] if idx["ticker"] == "JPY=X" else thresholds["index_move_pct"]
        if abs(idx["day_change_pct"]) >= limit and key not in alerted:
            direction = "上昇" if idx["day_change_pct"] > 0 else "下落"
            triggers.append({"type": "指数急変", "detail": f"{idx['name']} が前日比 {idx['day_change_pct']:+}% の{direction}", "key": key})

    for w in snapshot["watchlist"]:
        key = f"wl:{w['ticker']}"
        if abs(w["day_change_pct"]) >= thresholds["watchlist_move_pct"] and key not in alerted:
            direction = "急騰" if w["day_change_pct"] > 0 else "急落"
            triggers.append({"type": "ウォッチリスト銘柄の急変", "detail": f"{w['ticker']} が前日比 {w['day_change_pct']:+}% の{direction} (現在値 {w['price']})", "key": key})

    return triggers


def main():
    config = load_config()
    sector_map, _ = load_knowledge()
    state = load_state()

    print("市場データ取得中...")
    snapshot = fetch_market_snapshot(config)

    triggers = detect_triggers(snapshot, config["alert_thresholds"], state["alerted"])

    if not triggers:
        print("しきい値超えの変動なし。通知はスキップ")
        return

    print(f"{len(triggers)}件の急変動を検知。Claudeで分析中...")
    alert = generate_event_alert(
        [{"type": t["type"], "detail": t["detail"]} for t in triggers],
        snapshot, sector_map, config["claude"],
    )
    post_to_discord("# 🚨 市場アラート\n\n" + alert)

    state["alerted"].extend(t["key"] for t in triggers)
    save_state(state)


if __name__ == "__main__":
    main()

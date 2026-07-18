"""日次ブリーフィング: 毎朝実行され、市況+知識補佐をDiscordに投稿する"""
from datetime import date

from analyze import generate_daily_brief
from fetch_data import fetch_market_snapshot, load_config, load_knowledge
from notify import post_to_discord


def main():
    config = load_config()
    sector_map, calendar = load_knowledge()

    print("市場データ取得中...")
    snapshot = fetch_market_snapshot(config)

    print("Claudeで分析中...")
    brief = generate_daily_brief(snapshot, sector_map, calendar, config["claude"])

    header = f"# ☀️ デイリーブリーフィング {date.today().strftime('%Y/%m/%d')}\n\n"
    post_to_discord(header + brief)


if __name__ == "__main__":
    main()

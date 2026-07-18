"""Claude APIによる市況分析・ブリーフィング生成"""
import json
import os
from datetime import date

import anthropic

SYSTEM_PROMPT = """あなたは株式投資初心者のための投資補助アシスタントです。
デイトレードとNISA枠での中長期投資の両方を行うユーザーを支援します。

あなたの最大の役割は「知識の補佐」です:
- 注目テーマから周辺のサプライチェーン銘柄まで連想を広げて教える
  (例: AIならGPUのNVIDIAだけでなく、HBMのマイクロン、装置の東京エレクトロン、電線のフジクラまで)
- 地政学イベント・選挙・金融政策がどのセクターにどう波及するかを説明する
- 提供された「業界知識マップ」を活用し、必要に応じて自身の知識で補完する

ルール:
- 必ず日本語で回答
- 初心者向けに専門用語には短い説明を添える
- 具体的な売買指示(「買え」「売れ」)は絶対にしない。判断材料の提供に徹する
- 最後に必ず「※投資判断はご自身の責任で行ってください」を入れる
- Discordに投稿されるため、Markdownで簡潔に。全体で1800文字以内"""


def get_client() -> anthropic.Anthropic:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    return anthropic.Anthropic(api_key=api_key)


def generate_daily_brief(snapshot: dict, sector_map: dict, calendar: dict, claude_cfg: dict) -> str:
    """日次ブリーフィングを生成"""
    today = date.today().isoformat()
    prompt = f"""今日は {today} です。以下のデータをもとに、今日の投資ブリーフィングを作成してください。

## 市場スナップショット (指数・ウォッチリスト銘柄の価格と変動率)
{json.dumps(snapshot, ensure_ascii=False)}

## 業界知識マップ (サプライチェーン・連動ロジック)
{json.dumps(sector_map, ensure_ascii=False)}

## イベントカレンダー
{json.dumps(calendar, ensure_ascii=False)}

## 出力フォーマット
**📊 今日の市況**: 指数・為替の状況を2-3行で
**👀 ウォッチリスト**: 大きく動いた銘柄とその背景推測
**🔗 今日の連想**: 目立った動きから、知識マップを使ってサプライチェーンの周辺銘柄・関連セクターを1つ深掘り(ここが最重要。ユーザーが思いつかない銘柄・業界を教える)
**📅 直近の注目イベント**: カレンダーから7日以内のイベントと影響
**⚠️ リスク**: 今警戒すべきこと1-2点"""

    client = get_client()
    resp = client.messages.create(
        model=claude_cfg["model"],
        max_tokens=claude_cfg["max_tokens"],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def generate_event_alert(triggers: list[dict], snapshot: dict, sector_map: dict, claude_cfg: dict) -> str:
    """しきい値超えの急変時アラートを生成"""
    prompt = f"""市場で以下の急変動を検知しました。緊急アラートを作成してください。

## 検知した変動
{json.dumps(triggers, ensure_ascii=False)}

## 現在の市場スナップショット
{json.dumps(snapshot, ensure_ascii=False)}

## 業界知識マップ
{json.dumps(sector_map, ensure_ascii=False)}

## 出力フォーマット (簡潔に、800文字以内)
**🚨 何が起きたか**: 検知した変動の要約
**🔗 波及の可能性**: 知識マップのマクロ連動ルールに基づき、この動きがどのセクター・銘柄に波及しうるか
**💡 初心者への注意**: 慌てた売買を防ぐための一言"""

    client = get_client()
    resp = client.messages.create(
        model=claude_cfg["model"],
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")

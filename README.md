# gov-monitor

官公庁サイトの更新を自動監視し、差分を通知・記録するシステム。

## 概要

厚生労働省・中小企業庁・東京都など官公庁サイトの更新を見逃さないための仕組みです。RSS対応・非対応サイトの両方に対応し、更新を検知したらAIサマリーと一次情報URLをSlack通知・スプレッドシート追記します。

```
更新検知 → キーワードフィルタ → AIサマリー生成 → Slack通知 + Sheets追記
```

## 現在の実装範囲

既定ブランチで収録されているのは、Phase 1のRSS/HTML解析・状態管理とそのテストです。以下の機能一覧・設定例・CLI例・構成図には未実装の設計内容も含まれます。AI要約、Slack/Sheets出力、設定管理、スケジューラ、CLIはロードマップ上の後続段階です。クロール間隔やrobots.txt遵守の項目も運用方針であり、現コードによる自動強制が確認された機能ではありません。

## 機能（計画を含む）

- **RSS監視** — feedparserによるRSSポーリング（厚労省・e-Gov・東京都等）
- **HTMLスクレイピング** — RSS非対応ページをCSS/XPathセレクタで差分検知
- **重複排除** — 一度通知した更新は再通知しない（SQLite管理）
- **キーワードフィルタ** — 障害福祉・補助金など関心領域だけに絞れる
- **AIサマリー** — Claude Haiku APIで変更内容を3行要約
- **Slack通知** — Webhook経由で即時通知
- **Google Sheets追記** — 更新ログを差分形式でスプレッドシートに蓄積
- **CLIで手動実行** — 任意のタイミングで実行可能

## セットアップ

### 必要環境

- Python 3.11+

### インストール

```bash
git clone <repository-url>
cd gov-monitor
pip install -e ".[dev]"
```

### 環境変数

`.env.example` をコピーして設定します。

```bash
cp .env.example .env
```

```env
ANTHROPIC_API_KEY=sk-ant-...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
GOOGLE_SERVICE_ACCOUNT_JSON=<base64エンコードしたサービスアカウントJSON>
SHEETS_ID=<スプレッドシートID>
```

### 監視URLの設定

`monitors.yaml` に監視対象を追加します。

```yaml
monitors:
  - id: mhlw_shingi_shougai
    name: 厚労省 社会保障審議会 障害者部会
    url: https://www.mhlw.go.jp/stf/shingi/other-syougai_446935_00001.html
    type: html
    selector: "table.m-tableFlex tbody tr"
    interval_minutes: 60
    keywords:
      - 障害
    notify:
      - slack
      - sheets

  - id: mhlw_rss
    name: 厚労省 新着情報
    url: https://www.mhlw.go.jp/stf/news.rdf
    type: rss
    interval_minutes: 15
    keywords:
      - 障害
      - 補助金
      - 助成金
    notify:
      - slack
      - sheets
```

`type` は `rss` または `html` を指定します。`html` の場合は `selector` でCSSセレクタを指定してください。

## 使い方

```bash
# 全モニターを1回実行
gov-monitor run

# 特定のモニターだけ実行
gov-monitor run --id mhlw_shingi_shougai

# 最終確認日時の一覧を表示
gov-monitor status

# 通知テスト（実際の更新がなくてもSlackに送信）
gov-monitor test-notify --id mhlw_rss
```

スケジューラとして常駐させる場合（`monitors.yaml` の `interval_minutes` が適用されます）：

```bash
gov-monitor start
```

## 通知フォーマット（Slack）

```
[更新検知] 厚労省 社会保障審議会 障害者部会
📅 2026-04-28
🔗 https://www.mhlw.go.jp/stf/newpage_72919.html

第55回の資料が追加されました。
議題：障害福祉サービスの報酬改定について。
資料10件（PDF）が公開されています。
```

## スプレッドシート出力カラム

| 検知日時 | モニター名 | タイトル | サマリー | 一次情報URL | カテゴリ |
|----------|-----------|---------|---------|------------|---------|

## アーキテクチャ

```
gov_monitor/
├── pollers/
│   ├── rss_poller.py      # RSSフィード取得・パース
│   └── html_scraper.py    # HTMLスクレイピング・差分検知
├── processors/
│   ├── keyword_filter.py  # キーワードフィルタ
│   └── ai_summarizer.py   # Claude Haiku APIサマリー生成
├── notifiers/
│   ├── slack_notifier.py  # Slack Webhook通知
│   ├── sheets_writer.py   # Google Sheets追記
│   └── jsonl_archive.py   # ローカルJSONLアーカイブ
├── state_store.py         # 既読管理（SQLite）
├── models.py              # データモデル
└── config.py              # YAML設定読み込み
```

## 開発

```bash
# テスト実行（カバレッジ付き）
python -m pytest

# 特定ファイルのみ
python -m pytest tests/test_rss_poller.py -v
```

テストはフィクスチャHTMLを使用するため、外部通信なしで実行できます。

## 対応済みサイト

| サイト | 方式 | RSS URL |
|--------|------|---------|
| 厚生労働省 | RSS + HTML | `https://www.mhlw.go.jp/stf/news.rdf` |
| e-Gov（デジタル庁） | RSS | `https://www.e-gov.go.jp/news/news.xml` |
| 東京都 | RSS | `https://www.metro.tokyo.lg.jp/...rss` |
| 中小企業庁 | HTML（RSS未対応） | — |

## クロールポリシー

- 各サイトの `robots.txt` を遵守します
- 最小クロール間隔は15分（スケジューラが強制）
- User-Agentを識別可能な文字列に設定します
- 商用利用の場合は各省庁の利用規約を確認してください

## ロードマップ

- [x] Phase 1: RSSポーラー・HTMLスクレイパー・状態管理
- [ ] Phase 2: キーワードフィルタ・AIサマリー・UpdateEvent組み立て
- [ ] Phase 3: Slack通知・Google Sheets追記・JSONLアーカイブ
- [ ] Phase 4: スケジューラ・CLI・設定管理
- [ ] Phase 5: Playwright対応（JavaScript重いサイト）・PDFハッシュ比較

## 成立と開発段階

[設計書](design.md)は、RSSだけでは拾えない個別ページをHTMLの範囲指定で補い、一次情報URLへ戻れる更新記録を作ることを出発点にしています。[2026年4月29日の初期コミット](https://github.com/masa-san-jp/public-info-monitoring/commit/76eb9ede8590a6fe722a7a04c87a101e15f37aed)に、RSS/HTML解析と状態保存、フィクスチャを使ったテスト基盤が収録されています。設計書の日付表記とGitの記録時刻は区別してください。

現段階は末尾ロードマップのPhase 1です。例えば[HTMLScraper](gov_monitor/pollers/html_scraper.py)は渡されたHTMLをCSSセレクタで抽出しハッシュ化する解析部品です。通知・要約・CLIを含む全体フローは設計上の到達点であり、継続監視や実通知が稼働済みという意味ではありません。次段階では処理層、出力層、スケジューラを接続して検証します。

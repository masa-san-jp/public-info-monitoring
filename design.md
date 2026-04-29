# gov-monitor — 官公庁ページ更新監視システム 設計書

作成日: 2026-04-30
ステータス: 設計フェーズ

---

## 1. 目的と要件

### コアゴール
官公庁サイトの更新を自動検知し、**いつ・何が変わったか・一次情報URL**を即時把握できる仕組みを構築する。

### 機能要件
| # | 要件 | 優先度 |
|---|------|--------|
| F1 | 指定URLリストを定期クロール（RSS対応・非対応両方） | 必須 |
| F2 | 前回との差分を検出（新規追加・内容変更） | 必須 |
| F3 | 更新日時・サマリー・一次情報URLを記録 | 必須 |
| F4 | 更新を通知（Slack または メール） | 必須 |
| F5 | スプレッドシートに差分追記 | 必須 |
| F6 | ノイズ除去（ナビ・バナー変更を無視） | 重要 |
| F7 | AI要約生成（変更内容を3行サマリーに） | 重要 |
| F8 | PDF・添付ファイル更新の検知 | 任意 |

### 非機能要件
- 更新見逃しゼロ（False Negative < 1%）
- 誤通知最小化（False Positive < 5%）
- セルフホスト可能（外部SaaSへの依存なし）
- 監視サイトに迷惑をかけない（クロール間隔 ≥ 1時間、robots.txt遵守）

---

## 2. 調査から得た知見

### 類似サービスの成功要因
1. **CSS/XPathセレクタで監視範囲を絞る** → ナビ・バナー変更を排除
2. **RSSと直接スクレイピングを併用** → RSS対応サイトはリアルタイム、非対応は定期ポーリング
3. **LLMサマリーで "何が変わったか" を可読化** → テキストdiffだけでは読めない
4. **一次情報URLを構造データとして保存** → 後からの検索・参照を可能に

### 対象URL（厚労省 障害者施策検討チーム）の特性
- ページ固有RSSなし → HTMLスクレイピングが必須
- HTTP Last-Modifiedヘッダーなし → HTML内の `<time datetime>` 属性が更新日付の代替
- 更新パターン: 新しい会合ごとに `<tr>` 1行追加 → 行数またはテキスト差分で検知可能
- 検知セレクタ(案): `table.m-tableFlex tbody tr:nth-child(2) td:first-child`（最新回数セル）
- robots.txt: `/stf/shingi/` パスは制限なし → クロール可

### 厚労省RSS（`https://www.mhlw.go.jp/stf/news.rdf`）
- 実測で稼働確認済み、100件収録、dc:dateタグあり
- 個別審議会ページへの直接エントリはないが、新資料ページ（`newpage_XXXXX`）はRSSに出現する可能性あり
- RSSとスクレイピングの併用で検出漏れを防ぐ

---

## 3. システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: 監視層 (Poller)                               │
│  ┌──────────────┐  ┌──────────────────────────────────┐  │
│  │ RSSPoller    │  │ HTMLScraper                      │  │
│  │ feedparser   │  │ httpx + BeautifulSoup             │  │
│  │ 15分間隔     │  │ CSS/XPathセレクタ + ハッシュ比較 │  │
│  └──────────────┘  └──────────────────────────────────┘  │
│            ↓                    ↓                        │
│  ┌──────────────────────────────────────────────────┐    │
│  │ StateStore (SQLite / JSONL)                       │    │
│  │ url, last_seen_hash, last_seen_at, entries[]      │    │
│  └──────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────┘
                     │ 差分イベント
┌────────────────────▼────────────────────────────────────┐
│  Layer 2: 処理層 (Processor)                            │
│  ┌──────────────────┐  ┌────────────────────────────┐  │
│  │ KeywordFilter    │  │ AISummarizer               │  │
│  │ 障害福祉/補助金等 │  │ Claude Haiku API           │  │
│  └──────────────────┘  └────────────────────────────┘  │
│            ↓                    ↓                        │
│  ┌──────────────────────────────────────────────────┐    │
│  │ UpdateEvent                                       │    │
│  │ {url, title, detected_at, summary, source_url}    │    │
│  └──────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Layer 3: 出力層 (Notifier)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ SlackNotifier│  │ SheetsWriter │  │ JSONLArchive │   │
│  │ Webhook      │  │ Google Sheets│  │ ローカル保存 │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 技術スタック

| 用途 | ライブラリ | 理由 |
|------|-----------|------|
| HTTPクライアント | `httpx` | async対応、タイムアウト管理 |
| HTMLパース | `beautifulsoup4` | 実績・安定性 |
| RSSパース | `feedparser` | 全フォーマット対応（RSS1/2, Atom, RDF） |
| 状態管理 | `SQLite`（標準ライブラリ） | 依存ゼロ、十分な性能 |
| AIサマリー | `anthropic` SDK（Claude Haiku） | コスト効率、日本語品質 |
| Google Sheets | `gspread` | シンプルなAPI |
| スケジューラ | `APScheduler` | 軽量、cronライク |
| テスト | `pytest` + `pytest-httpx` | モックHTTP対応 |
| 設定 | `YAML` + 環境変数 | 人間が読める形式 |

---

## 4. URLリスト設定（YAML）

```yaml
# monitors.yaml
monitors:
  - id: mhlw_shingi_shougai
    name: 厚労省 社会保障審議会 障害者部会
    url: https://www.mhlw.go.jp/stf/shingi/other-syougai_446935_00001.html
    type: html
    selector: "table.m-tableFlex tbody tr:nth-child(2)"
    interval_minutes: 60
    keywords:
      - 障害
      - 部会
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
      - 福祉
    notify:
      - slack
      - sheets
```

---

## 5. UpdateEventのデータモデル

```python
@dataclass
class UpdateEvent:
    id: str              # SHA256(url + detected_at)
    url: str             # 監視対象URL
    source_url: str      # 一次情報URL（記事・PDF直リンク）
    title: str           # 更新タイトル
    detected_at: str     # 検知日時（ISO8601）
    published_at: str    # 記事公開日（取得可能な場合）
    diff_text: str       # テキスト差分（raw）
    summary: str         # AI生成サマリー
    category: str        # "新着" | "更新" | "削除"
    monitor_id: str      # monitors.yamlのid
```

---

## 6. TDD開発ロードマップ

### Phase 1: 基盤 — 小さな成功を積む（Week 1）

**M1: RSS取得・重複排除** ← 最初のテスト
```
テスト: test_rss_poller.py
- test_parse_mhlw_rss_feed()           # RSSを取得してエントリ数確認
- test_deduplicate_seen_entries()      # 既知IDを除外する
- test_extract_entry_fields()          # title, url, published_at取得
```

**M2: HTMLスクレイパー**
```
テスト: test_html_scraper.py
- test_fetch_mhlw_page()               # ページ取得（fixtures使用）
- test_extract_table_rows()            # テーブル行数抽出
- test_detect_change_by_hash()         # ハッシュ比較で差分検知
- test_extract_source_urls()           # newpage_XXXXX リンク抽出
```

**M3: 状態管理（StateStore）**
```
テスト: test_state_store.py
- test_save_and_load_state()
- test_mark_as_seen()
- test_get_unseen_entries()
```

### Phase 2: 処理層（Week 2）

**M4: キーワードフィルタ**
```
テスト: test_keyword_filter.py
- test_pass_matching_entry()
- test_block_non_matching_entry()
```

**M5: AI要約（Claude Haiku）**
```
テスト: test_ai_summarizer.py
- test_summarize_diff_text()           # モック使用
- test_summary_format()                # 3行以内
- test_fallback_on_api_error()
```

**M6: UpdateEventの組み立て**
```
テスト: test_event_builder.py
- test_build_from_rss_entry()
- test_build_from_html_diff()
```

### Phase 3: 出力層（Week 3）

**M7: JSONLアーカイブ（ローカル保存）**
- まずファイル出力で動作確認

**M8: Google Sheets追記**
```
テスト: test_sheets_writer.py（モック）
- test_append_update_event()
- test_format_row()
```

**M9: Slack通知**
```
テスト: test_slack_notifier.py（モック）
- test_send_notification()
- test_format_message()
```

### Phase 4: スケジューラ & 設定（Week 4）

**M10: スケジューラ**
- APSchedulerでcronジョブ登録
- monitors.yamlのinterval_minutesを反映

**M11: 手動実行 CLI**
```bash
python -m gov_monitor run          # 全モニター実行
python -m gov_monitor run --id mhlw_shingi_shougai  # 個別実行
python -m gov_monitor status       # 最終確認日時の一覧
python -m gov_monitor test-notify  # 通知テスト送信
```

---

## 7. ディレクトリ構成

```
gov-monitor/
├── gov_monitor/
│   ├── __init__.py
│   ├── config.py          # YAML設定読み込み
│   ├── models.py          # UpdateEvent dataclass
│   ├── state_store.py     # SQLite状態管理
│   ├── pollers/
│   │   ├── rss_poller.py
│   │   └── html_scraper.py
│   ├── processors/
│   │   ├── keyword_filter.py
│   │   └── ai_summarizer.py
│   └── notifiers/
│       ├── slack_notifier.py
│       ├── sheets_writer.py
│       └── jsonl_archive.py
├── tests/
│   ├── fixtures/
│   │   └── mhlw_page.html   # テスト用静的ファイル
│   ├── test_rss_poller.py
│   ├── test_html_scraper.py
│   ├── test_state_store.py
│   ├── test_keyword_filter.py
│   ├── test_ai_summarizer.py
│   ├── test_sheets_writer.py
│   └── test_slack_notifier.py
├── monitors.yaml
├── .env.example
├── requirements.txt
├── pyproject.toml
└── design.md
```

---

## 8. 秘密情報の管理

`.env` ファイルで管理（gitignore済み）:

```
ANTHROPIC_API_KEY=
SLACK_WEBHOOK_URL=
GOOGLE_SERVICE_ACCOUNT_JSON=  # base64エンコード
SHEETS_ID=
```

---

## 9. 既知リスクと対策

| リスク | 対策 |
|--------|------|
| サイト構造変更でセレクタが壊れる | テスト + アラートで即時検知 |
| レートリミット・IP遮断 | 1時間以上の間隔、User-Agentを識別可能に設定 |
| LLM API費用 | Claude Haiku使用、キャッシュ活用、月額上限設定 |
| robots.txt変更 | クロール前に毎回確認するオプションを実装 |
| PDFの内容変更（URL不変） | ファイルハッシュ比較（Phase 2以降に対応） |

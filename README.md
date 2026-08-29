# プリズム

科学を伝えるための道具・人・場所を集めたカタログ。**CSVを直せば、公開されているサイトが自動で更新されます。**

---

## GitHubのWeb画面だけで運用する手順

### 手順1　リポジトリを作る

1. https://github.com/new を開く
2. Repository name に `prism`
3. **Public** を選ぶ（Privateだと無料プランでGitHub Pagesが使えません）
4. 「Add a README file」は**チェックを外す**（これから上げるファイルと衝突します）
5. Create repository

### 手順2　ファイルを上げる

作成直後の画面にある **「uploading an existing file」** をクリック。
このフォルダ（`prism-repo`）の**中身をすべて**ドラッグ&ドロップします。

> ドラッグするのは `prism-repo` フォルダそのものではなく、**中にあるファイルとフォルダ**です。
> `.github` フォルダも必ず含めてください（隠しフォルダ扱いで見落としやすい）。
> Macで `.github` が見えないときは、Finderで `Command + Shift + .` を押すと表示されます。

下の「Commit changes」を押して確定します。

### 手順3　GitHub Pages を有効にする

1. リポジトリの **Settings** タブ
2. 左メニューの **Pages**
3. Source を **GitHub Actions** に変更（"Deploy from a branch" ではありません）

### 手順4　最初のビルドを走らせる

1. **Actions** タブを開く
2. 左の "build and deploy" をクリック
3. 右の **Run workflow** ボタン → 緑の Run workflow

2〜3分で緑のチェックが付きます。**Settings → Pages** に戻ると、
`https://<あなたのユーザー名>.github.io/prism/` が表示されます。これが公開URLです。

### 手順5　アフィリエイトIDを入れる（収益化するとき）

1. **Settings → Secrets and variables → Actions**
2. **New repository secret** を押して、下記を1つずつ登録

| Name | Secret に入れる値 |
|---|---|
| `AMAZON_TAG` | AmazonアソシエイトのトラッキングID（例 `yourname-22`） |
| `RAKUTEN_ID` | 楽天アフィリエイトID |
| `RAKUTEN_TRAVEL_ID` | 楽天トラベルのアフィリエイトID |
| `JALAN_ID` | じゃらんのvos値（使う場合） |

登録したら Actions → Run workflow をもう一度押すと、リンクに反映されます。

> **申請の順序に注意。** Amazonアソシエイトは審査時にサイトが公開済みで中身があることを求めます。
> **先に手順4まで終えて公開 → 申請 → IDを登録して再実行**、の順です。

---

## 毎日の運用（これだけ）

### 掲載を1件足す

1. `data/listings.csv` を開く
2. 右上の **鉛筆アイコン（Edit this file）**
3. 一番下に1行足す
4. 下の **Commit changes** を押す

→ Actionsが自動で走り、物品分解とビルドが実行され、**数分後には公開サイトに反映されます。**

CSVが読みにくければ、GitHubの表示を **Raw** から切り替えると表形式で見られます。

### 列の意味

`data/listings.csv` の主な列。空でよい列も多いです。

| 列 | 必須 | 内容 |
|---|---|---|
| `url` | ● | 一次情報のURL |
| `title` | ● | 名称 |
| `provider` | ● | 提供者名 |
| `providerType` | | 大学・研究機関 / 企業・メーカー / 科学館・博物館 / 自治体・公的機関 / NPO・市民団体 / 学会・専門団体 / クリエイター・YouTuber / 個人コミュニケーター / 研究者・専門家 |
| `media_type` | | youtube / tiktok / instagram / note / toy / kit / museum / event / person など24種 |
| `format` | | 表示用の形式名 |
| `act_group` | | みる・きく / つかう / よむ / やってみる / よぶ・あう / いく。**空なら自動で決まります** |
| `field` | | 分野。**またぐものは空でよい**（空だと虹色のカードになります） |
| `audience` `purpose` `topics` | | `|` 区切り |
| `txn` | | 無料 / 購入（買い切り）/ 予約（日時指定）/ 要見積もり / サブスク / フリーミアム |
| `更新頻度` | | 日次 / 週次 / 月次 / 年次。**週次以上が「今週の更新」に出ます** |
| `region_pref` `region_city` | | 「いく」で必須。**空だと旅行リンクが出ません** |
| `description` | ● | 1〜3文。**ここから物品が分解されます** |

`description` が薄いと物品分解も薄くなります。ここだけは丁寧に書いてください。

### 手元にPythonがなくても確認できる

Actionsのログに毎回こう出ます。

```
146件 → 物品 894点（毎回いるもの 584点 = 65%）
  安全確認で購入導線を止めるもの 24点／「いく」掲載 22件
■ 何をしたいか
   よむ  10件   ← 手薄
```

「← 手薄」が出た区分に掲載を足していけば、網羅が埋まります。

---

## ファイル構成

```
├─ data/listings.csv          ← 触るのはここだけ
├─ prism/                     パイプライン
│   ├─ taxonomy.py            語彙（メディア24種・動詞6種）
│   ├─ schema.py              CSVの列定義
│   ├─ extract.py             URL→掲載レコード、監視フィードの自動推定
│   ├─ decompose.py           物品分解（掲載でも送客でも通る共有ステージ）
│   ├─ monetize.py            アフィリエイト解決・開示文・安全ゲート
│   └─ discover.py            探索元20経路
├─ run.py                     CLI（decompose / coverage / submit / seeds）
├─ site/
│   ├─ template.html          画面。__PRISM_DATA__ にデータが差し込まれる
│   └─ build.py               CSV → 1枚のHTML
└─ .github/workflows/deploy.yml   push・毎朝5時・手動でビルドして公開
```

生成物（`_site/`、`data/materials.csv`）はコミットしません。Actionsが毎回作り直します。

---

## 公開前に必ずやること

**フッターの連絡先を書き換える。** `site/template.html` の `REPLACE_WITH_YOUR_EMAIL` を実際のアドレスにしてください。掲載146件は実在の団体です。削除・修正の依頼窓口がないまま公開するのは避けてください。

**安全に関わる24点。** 保護めがね、ヘルメット、解剖ばさみ、火気。確認がすむまで購入リンクが出ない実装ですが、裏を返すと確認しないかぎり収益になりません。`prism/decompose.py` の物品マスタで `saf=` が付いているものです。

**開示文を消さない。** 準備物の下に1行あります。Amazon・楽天の規約要件であり、日本のステマ規制の対象でもあります。消すと収益源ごと失います。

---

## いまできていないこと

読み取り（見る・探す・絞る・並べ替える）は完全に動きます。**書き込みはできません。**

| 項目 | 状態 |
|---|---|
| リアクションの保存 | 押せるが再読み込みで戻る |
| 実施記録の投稿 | 表示枠のみ。投稿できない |
| 掲載フォーム | 説明のみ。投稿できない |
| 依頼フロー（要見積もり29件） | 未着手 |
| 商品画像 | ファビコンのみ |

静的サイトの限界です。ここから先はサーバー側（Supabase や Cloudflare D1）が必要になります。テーブルは `reactions` / `practices` / `submissions` の3つから始められます。

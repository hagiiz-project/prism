/**
 * プリズム「AIに聞く」中継役（Google Apps Script）
 *
 * なぜ中継が要るか：
 *   Gemini の APIキーを静的サイトに書くと、ブラウザの開発者ツールで誰でも見えます。
 *   キーはこの Apps Script の中（スクリプトプロパティ）に置き、外からは見えないようにします。
 *
 * なぜベクトル検索（RAG）を使わないか：
 *   掲載が数百件のうちは、全件をそのまま Gemini に渡すほうが正確で安くて速い。
 *   埋め込みとベクトルDBが要るのは、数千件を超えてからです。
 *
 * 安全のための設計：
 *   AI には「どの掲載が該当するか」の id と、短い理由だけを答えさせます。
 *   価格・URL・連絡先は AI に書かせません。サイト側が本物のデータから描きます。
 *
 * ── 設置手順 ──────────────────────────────────
 * 1. スプレッドシートを開く → 拡張機能 → Apps Script
 * 2. このファイルの中身をすべて貼り付ける
 * 3. 左の歯車（プロジェクトの設定）→ スクリプト プロパティ に次を追加
 *      GEMINI_API_KEY   … Google AI Studio で発行したキー
 *      SHEET_ID         … スプレッドシートのURLの /d/ と /edit の間の文字列
 *      SHEET_NAME       … listings（既定）
 * 4. 右上「デプロイ」→ 新しいデプロイ → 種類＝ウェブアプリ
 *      次のユーザーとして実行： 自分
 *      アクセスできるユーザー： 全員
 * 5. 発行された URL（/exec で終わるもの）を GitHub の Secrets に AI_ENDPOINT として登録
 */

const MODEL = 'gemini-2.0-flash';

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents || '{}');
    const q = String(body.q || '').slice(0, 400);
    if (!q.trim()) return json_({ answer: '', ids: [] });

    const catalog = getCatalog_();
    const out = askGemini_(q, catalog);
    return json_(out);
  } catch (err) {
    return json_({ answer: '', ids: [], error: String(err) });
  }
}

// ブラウザから直接開いたときの動作確認用
function doGet() {
  return json_({ ok: true, items: getCatalog_().length });
}

/** スプレッドシートから、AIに渡す最小限の目録を作る。6時間キャッシュする。 */
function getCatalog_() {
  const cache = CacheService.getScriptCache();
  const hit = cache.get('catalog');
  if (hit) return JSON.parse(hit);

  const p = PropertiesService.getScriptProperties();
  const sh = SpreadsheetApp.openById(p.getProperty('SHEET_ID'))
                           .getSheetByName(p.getProperty('SHEET_NAME') || 'listings');
  const values = sh.getDataRange().getValues();
  const head = values[0].map(String);
  const col = (name) => head.indexOf(name);

  const items = [];
  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    const get = (n) => { const i = col(n); return i < 0 ? '' : String(row[i] || ''); };
    if (!get('title') || !get('url')) continue;
    items.push({
      id: Number(get('id') || r),
      t: get('title'),
      p: get('provider'),
      g: get('act_group'),
      f: get('field'),
      fm: get('format'),
      a: get('audience'),
      pu: get('purpose'),
      x: get('txn'),
      pr: get('priceNum'),
      d: get('description').slice(0, 120)
    });
  }
  cache.put('catalog', JSON.stringify(items), 21600);   // 6時間
  return items;
}

function askGemini_(q, catalog) {
  const key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  const sys =
    'あなたは科学コミュニケーションの相談員です。以下の目録から、質問に合う掲載を最大6件選びます。\n' +
    '厳守すること：\n' +
    '- 目録にない掲載を作らない。id は必ず目録から選ぶ\n' +
    '- 価格・URL・連絡先・開催日は書かない（画面が本物のデータを表示するため）\n' +
    '- 合うものが無ければ ids を空にし、なぜ無いかと条件の変え方を answer に書く\n' +
    '- answer は日本語で、150字以内。選んだ理由と、選ぶときの注意を1つ書く\n' +
    '出力は次のJSONのみ： {"ids":[数値],"answer":"文字列"}\n\n' +
    '目録(JSON):\n' + JSON.stringify(catalog);

  const res = UrlFetchApp.fetch(
    'https://generativelanguage.googleapis.com/v1beta/models/' + MODEL + ':generateContent?key=' + key,
    {
      method: 'post',
      contentType: 'application/json',
      muteHttpExceptions: true,
      payload: JSON.stringify({
        systemInstruction: { parts: [{ text: sys }] },
        contents: [{ role: 'user', parts: [{ text: q }] }],
        generationConfig: { temperature: 0.2, responseMimeType: 'application/json' }
      })
    });

  const data = JSON.parse(res.getContentText());
  if (!data.candidates || !data.candidates.length) {
    return { ids: [], answer: '', error: 'モデルから応答がありませんでした' };
  }
  const text = data.candidates[0].content.parts[0].text;
  const parsed = JSON.parse(text);
  const valid = new Set(catalog.map(function (c) { return c.id; }));
  return {
    ids: (parsed.ids || []).map(Number).filter(function (n) { return valid.has(n); }).slice(0, 6),
    answer: String(parsed.answer || '')
  };
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
                       .setMimeType(ContentService.MimeType.JSON);
}

/** キャッシュを手で消したいとき（掲載を足した直後など）に実行する */
function clearCatalogCache() {
  CacheService.getScriptCache().remove('catalog');
}

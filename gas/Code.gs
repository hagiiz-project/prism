/**
 * プリズム「AIに聞く」中継役（Google Apps Script）v2
 *
 * v1からの変更：
 *   - GET で受けるようにした。/exec は POST だとリダイレクトで GET に化けることがあるため
 *   - エラーを握りつぶさず、そのまま返す（画面に原因が出ます）
 *   - エディタ内で実行できる自己診断 selfTest() を追加
 *
 * ── 設置手順 ──────────────────────────────────
 * 1. スプレッドシート → 拡張機能 → Apps Script
 * 2. この中身をすべて貼り付ける（前の内容は消す）
 * 3. 左の歯車（プロジェクトの設定）→ スクリプト プロパティ
 *      GEMINI_API_KEY   … https://aistudio.google.com/apikey で発行したキー
 *      SHEET_ID         … スプレッドシートURLの /d/ と /edit の間
 *      SHEET_NAME       … listings
 *      GEMINI_MODEL     … 任意。空なら 3.5-flash-lite → 3.6-flash → 3.7-flash の順に試す
 * 4. ★まず selfTest を実行し、実行ログで原因を確認する
 * 5. デプロイ → 新しいデプロイ → 種類＝ウェブアプリ
 *      次のユーザーとして実行： 自分 ／ アクセスできるユーザー： 全員
 * 6. /exec で終わるURLを GitHub の Secrets に AI_ENDPOINT として登録
 *
 * ── 意見・感想について ────────────────────────
 * feedback シートは初回の投稿時に自動で作られます（手で作る必要はありません）。
 * 投稿は必ず status=pending で入り、published に変えたものだけがサイトに出ます。
 * reply 列に書くと、その意見の下に運営からの返答として並びます。
 * fbStatus を実行すると、掲載待ちが何件あるかを実行ログで確認できます。
 *
 * ★コードを直したあとは必ず
 *   「デプロイ」→「デプロイを管理」→ 鉛筆マーク → バージョン「新バージョン」→ デプロイ
 *   を行ってください。これをしないと古いコードが動き続けます。
 *   「新しいデプロイ」を選ぶと URL が変わるので、上の手順を使います。
 */

/**
 * モデル名はスクリプト プロパティ GEMINI_MODEL で上書きできます。
 * 未設定なら下の候補を上から順に試し、404（提供終了）なら次へ進みます。
 * モデルが世代交代してもコードを直さずに済むようにするためです。
 */
// この用途（目録から該当IDを選ぶだけ）は最安のモデルで足ります。
// 上から順に試し、404（提供終了）なら次へ進みます。
const MODEL_CANDIDATES = ['gemini-3.5-flash-lite', 'gemini-3.6-flash', 'gemini-3.7-flash'];

function models_() {
  const fixed = PropertiesService.getScriptProperties().getProperty('GEMINI_MODEL');
  return fixed ? [fixed] : MODEL_CANDIDATES;
}

/** サイトからは GET で呼ばれる */
function doGet(e) {
  try {
    const p = (e && e.parameter) || {};
    const action = String(p.action || '');

    // 意見・感想の読み出し／書き込み
    if (action === 'fb_list') return json_({ ok: true, items: fbList_() });
    if (action === 'fb_post') return json_(fbPost_(p));

    const q = String(p.q || '').slice(0, 400);
    if (!q.trim()) return json_({ ok: true, items: getCatalog_().length, models: models_() });
    return json_(askGemini_(q, getCatalog_()));
  } catch (err) {
    return json_({ ids: [], answer: '', error: String((err && err.message) || err) });
  }
}

/* ======================================================================
   意見・感想（feedback シート）
   ----------------------------------------------------------------------
   誰でも書き込めるURLなので、投稿は必ず status=pending で入ります。
   シートで published に変えたものだけがサイトに出ます。
   reply 列に書くと、その意見の下に運営からの返答として並びます。
   ====================================================================== */
const FB_SHEET  = 'feedback';
const FB_HEAD   = ['created_at', 'name', 'role', 'message', 'page', 'status', 'reply', 'admin_note'];
const FB_ROLES  = ['教員・学校関係', '保護者', '研究者・専門家', '科学館・団体', '企業', '学生', 'その他'];

function fbSheet_() {
  const p = PropertiesService.getScriptProperties();
  const book = SpreadsheetApp.openById(p.getProperty('SHEET_ID'));
  let sh = book.getSheetByName(FB_SHEET);
  if (!sh) {                                   // 無ければ見出し付きで作る
    sh = book.insertSheet(FB_SHEET);
    sh.getRange(1, 1, 1, FB_HEAD.length).setValues([FB_HEAD]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}

function fbList_() {
  const sh = fbSheet_();
  const v = sh.getDataRange().getValues();
  if (v.length < 2) return [];
  const idx = {};
  v[0].forEach(function (h, i) { idx[String(h).trim()] = i; });
  const get = function (row, n) { return idx[n] === undefined ? '' : String(row[idx[n]] || ''); };

  const out = [];
  for (let r = v.length - 1; r >= 1; r--) {                 // 新しい順
    if (get(v[r], 'status') !== 'published') continue;
    const d = v[r][idx['created_at']];
    out.push({
      at: (d instanceof Date) ? Utilities.formatDate(d, 'Asia/Tokyo', 'yyyy/MM/dd') : String(d).slice(0, 10),
      name: get(v[r], 'name') || '匿名',
      role: get(v[r], 'role'),
      message: get(v[r], 'message'),
      reply: get(v[r], 'reply')
    });
    if (out.length >= 30) break;
  }
  return out;
}

function fbPost_(p) {
  const msg  = String(p.message || '').trim().slice(0, 600);
  const name = String(p.name || '').trim().slice(0, 40);
  const role = String(p.role || '').trim().slice(0, 20);
  const page = String(p.page || '').trim().slice(0, 60);

  if (msg.length < 5)  return { ok: false, error: '内容が短すぎます。5文字以上でお書きください。' };
  if (/https?:\/\//i.test(msg) || /https?:\/\//i.test(name)) {
    return { ok: false, error: 'URLを含む投稿は受け付けていません。ご意見の文章のみお書きください。' };
  }
  // 1日あたりの上限。宣伝の連投を止めるための簡易な歯止め
  const cache = CacheService.getScriptCache();
  const key = 'fbcount_' + Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyyMMdd');
  const n = Number(cache.get(key) || 0);
  if (n >= 200) return { ok: false, error: '本日の受付上限に達しました。時間をおいてお試しください。' };
  cache.put(key, String(n + 1), 21600);

  fbSheet_().appendRow([new Date(), name, role, msg, page, 'pending', '', '']);
  return { ok: true, message: 'お送りいただきありがとうございます。確認のうえ掲載します。' };
}

/** 投稿の受付状況をログに出す（掲載待ちが何件あるか） */
function fbStatus() {
  const v = fbSheet_().getDataRange().getValues();
  const idx = {}; v[0].forEach(function (h, i) { idx[String(h).trim()] = i; });
  const c = { pending: 0, published: 0, rejected: 0, other: 0 };
  for (let r = 1; r < v.length; r++) {
    const st = String(v[r][idx['status']] || '');
    if (c[st] === undefined) c.other++; else c[st]++;
  }
  Logger.log('掲載待ち pending : ' + c.pending);
  Logger.log('掲載中 published : ' + c.published);
  Logger.log('見送り rejected  : ' + c.rejected);
  Logger.log('その他            : ' + c.other);
  Logger.log('※ status を published に変えるとサイトに出ます。reply 列に書くと返答として並びます。');
}

/** 念のため POST も受ける */
function doPost(e) {
  try {
    const pp = (e && e.parameter) || {};
    if (String(pp.action || '') === 'fb_list') return json_({ ok: true, items: fbList_() });
    if (String(pp.action || '') === 'fb_post') return json_(fbPost_(pp));
    let q = '';
    if (e && e.parameter && e.parameter.q) q = String(e.parameter.q);
    else if (e && e.postData && e.postData.contents) {
      try { q = String(JSON.parse(e.postData.contents).q || ''); } catch (_) {}
    }
    q = q.slice(0, 400);
    if (!q.trim()) return json_({ ok: true, items: getCatalog_().length });
    return json_(askGemini_(q, getCatalog_()));
  } catch (err) {
    return json_({ ids: [], answer: '', error: String((err && err.message) || err) });
  }
}

/** シートから、AIに渡す最小限の目録を作る。6時間キャッシュする。 */
function getCatalog_() {
  const cache = CacheService.getScriptCache();
  const hit = cache.get('catalog');
  if (hit) return JSON.parse(hit);

  const p = PropertiesService.getScriptProperties();
  const sid = p.getProperty('SHEET_ID');
  if (!sid) throw new Error('スクリプト プロパティ SHEET_ID が未設定です');
  const name = p.getProperty('SHEET_NAME') || 'listings';

  const book = SpreadsheetApp.openById(sid);
  const sh = book.getSheetByName(name);
  if (!sh) {
    const names = book.getSheets().map(function (x) { return x.getName(); }).join(' / ');
    throw new Error('シート「' + name + '」が見つかりません。存在するシート：' + names);
  }

  const values = sh.getDataRange().getValues();
  if (values.length < 2) throw new Error('シート「' + name + '」にデータ行がありません');

  const idx = {};
  values[0].forEach(function (h, i) { idx[String(h).trim()] = i; });
  const get = function (row, n) { return idx[n] === undefined ? '' : String(row[idx[n]] || ''); };

  const items = [];
  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    if (!get(row, 'title') || !get(row, 'url')) continue;
    items.push({
      id: Number(get(row, 'id') || r),
      t: get(row, 'title'), p: get(row, 'provider'), g: get(row, 'act_group'),
      f: get(row, 'field'), fm: get(row, 'format'), a: get(row, 'audience'),
      pu: get(row, 'purpose'), x: get(row, 'txn'), pr: get(row, 'priceNum'),
      d: get(row, 'description').slice(0, 120)
    });
  }
  if (!items.length) {
    throw new Error('title と url の両方が入った行がありません。列名がシートと一致しているか確認してください');
  }
  cache.put('catalog', JSON.stringify(items), 21600);
  return items;
}

function askGemini_(q, catalog) {
  const key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!key) return { ids: [], answer: '', error: 'スクリプト プロパティ GEMINI_API_KEY が未設定です' };

  const sys =
    'あなたは科学コミュニケーションの相談員です。以下の目録から、質問に合う掲載を最大6件選びます。\n' +
    '厳守すること：\n' +
    '- 目録にない掲載を作らない。id は必ず目録から選ぶ\n' +
    '- 価格・URL・連絡先・開催日は書かない（画面が本物のデータを表示するため）\n' +
    '- 合うものが無ければ ids を空にし、なぜ無いかと条件の変え方を answer に書く\n' +
    '- answer は日本語で150字以内。選んだ理由と、選ぶときの注意を1つ書く\n' +
    '出力は次のJSONのみ： {"ids":[数値],"answer":"文字列"}\n\n' +
    '目録(JSON):\n' + JSON.stringify(catalog);

  // Gemini 3系では temperature / topK / topP の指定が無視されるかエラーになるため送らない
  const payload = JSON.stringify({
    systemInstruction: { parts: [{ text: sys }] },
    contents: [{ role: 'user', parts: [{ text: q }] }],
    generationConfig: { responseMimeType: 'application/json' }
  });

  const list = models_();
  let lastErr = '';
  for (let i = 0; i < list.length; i++) {
    const model = list[i];
    const res = UrlFetchApp.fetch(
      'https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent?key=' + key,
      { method: 'post', contentType: 'application/json', muteHttpExceptions: true, payload: payload });

    const code = res.getResponseCode();
    const body = res.getContentText();

    if (code === 404) {                       // 提供終了。次の候補へ
      let msg = body.slice(0, 200);
      try { msg = JSON.parse(body).error.message; } catch (_) {}
      lastErr = model + ' は使えません：' + msg;
      continue;
    }
    if (code !== 200) {
      let msg = body.slice(0, 300);
      try { msg = JSON.parse(body).error.message; } catch (_) {}
      return { ids: [], answer: '', error: 'Gemini APIが ' + code + ' を返しました（' + model + '）：' + msg };
    }

    let data;
    try { data = JSON.parse(body); }
    catch (_) { return { ids: [], answer: '', error: 'Geminiの応答を解釈できませんでした' }; }

    if (!data.candidates || !data.candidates.length) {
      return { ids: [], answer: '', error: 'モデルから候補が返りませんでした（安全フィルタの可能性）' };
    }

    const text = data.candidates[0].content.parts[0].text;
    let parsed;
    try { parsed = JSON.parse(text); }
    catch (_) { return { ids: [], answer: String(text).slice(0, 300), error: '', model: model }; }

    const valid = {};
    catalog.forEach(function (c) { valid[c.id] = true; });
    return {
      ids: (parsed.ids || []).map(Number).filter(function (n) { return valid[n]; }).slice(0, 6),
      answer: String(parsed.answer || ''),
      model: model
    };
  }
  return { ids: [], answer: '', error: '使えるモデルがありませんでした。' + lastErr +
    ' 　listModels を実行して、使える名前を GEMINI_MODEL に設定してください。' };
}

/**
 * ★このキーで使えるモデル名の一覧を実行ログに出す★
 * モデルが世代交代したら、これを実行して名前を確認し、
 * スクリプト プロパティ GEMINI_MODEL に設定してください。
 */
function listModels() {
  const key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  const res = UrlFetchApp.fetch(
    'https://generativelanguage.googleapis.com/v1beta/models?key=' + key + '&pageSize=100',
    { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) { Logger.log('取得できません：' + res.getContentText().slice(0, 300)); return; }
  const ms = JSON.parse(res.getContentText()).models || [];
  Logger.log('generateContent が使えるモデル：');
  ms.forEach(function (m) {
    if ((m.supportedGenerationMethods || []).indexOf('generateContent') >= 0) {
      Logger.log('  ' + m.name.replace('models/', ''));
    }
  });
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
                       .setMimeType(ContentService.MimeType.JSON);
}

/** 掲載を足した直後など、目録を作り直したいとき */
function clearCatalogCache() {
  CacheService.getScriptCache().remove('catalog');
  Logger.log('キャッシュを消しました');
}

/**
 * ★自己診断★
 * エディタ上部の関数名の欄で selfTest を選び「実行」。下の実行ログに原因が出ます。
 */
function selfTest() {
  const p = PropertiesService.getScriptProperties();
  Logger.log('1. SHEET_ID       : ' + (p.getProperty('SHEET_ID') ? 'あり' : '★未設定'));
  Logger.log('2. SHEET_NAME     : ' + (p.getProperty('SHEET_NAME') || 'listings（既定）'));
  Logger.log('3. GEMINI_API_KEY : ' + (p.getProperty('GEMINI_API_KEY') ? 'あり' : '★未設定'));

  let cat;
  try {
    CacheService.getScriptCache().remove('catalog');
    cat = getCatalog_();
    Logger.log('4. 目録の件数     : ' + cat.length + ' 件');
    Logger.log('   1件目          : ' + JSON.stringify(cat[0]));
  } catch (e) {
    Logger.log('4. ★目録の作成に失敗: ' + e.message);
    return;
  }

  Logger.log('5. 試すモデル     : ' + models_().join(' → '));
  const out = askGemini_('小学生に防災を伝えたい', cat);
  Logger.log('6. Geminiの応答   : ' + JSON.stringify(out));
  if (out.error) {
    Logger.log('   ★エラーの内容  : ' + out.error);
    if (out.error.indexOf('404') >= 0 || out.error.indexOf('no longer available') >= 0) {
      Logger.log('   → listModels() を実行し、出た名前を GEMINI_MODEL に設定してください。');
    }
  } else {
    Logger.log('   → 正常です。デプロイを管理から「新バージョン」で更新してください。');
  }
}

/* ======================================================================
   毎週の更新取得（週1回）
   ----------------------------------------------------------------------
   1つの処理で「判定」と「取得」を両方やります。
     判定：feed_type が空の行を調べ、フィードの有無を埋める
     取得：auto_update=TRUE の行を見に行き、新しい回を stream シートに足す
   判定を毎週やるので、掲載フォームから入った新しい行も、翌週には
   自動で取得対象になります。1回きりの設定作業はありません。

   ── 設置 ────────────────────────────────
   左の時計アイコン（トリガー）→ トリガーを追加
     実行する関数： weeklyUpdate
     イベントのソース： 時間主導型
     時間ベースのタイマー： 週タイマー（日曜・午前5〜6時など）
   ※ 初回は手で weeklyUpdate を実行してください。146件の判定に数分かかります。
   ====================================================================== */

const STREAM_SHEET = 'stream';
const STREAM_HEAD  = ['listing_id','external_id','title','url','published_at','kind','fetched_at','status'];
const FEED_COLS    = ['feed_url','feed_type','auto_update','last_item_at','last_checked_at','check_status','fail_count'];
const BATCH        = 20;    // 同時に叩く数
const MAX_ITEMS    = 10;    // 1フィードから拾う最大数

function weeklyUpdate() {
  const t0 = new Date();
  const sh = listSheet_();
  ensureColumns_(sh, FEED_COLS);
  const probed = probeFeeds_(sh);
  const added  = fetchFeeds_(sh);
  CacheService.getScriptCache().remove('catalog');   // AIの目録も作り直す
  Logger.log('判定した行 : ' + probed);
  Logger.log('足した回   : ' + added);
  Logger.log('所要       : ' + Math.round((new Date() - t0) / 1000) + '秒');
}

function listSheet_() {
  const p = PropertiesService.getScriptProperties();
  const book = SpreadsheetApp.openById(p.getProperty('SHEET_ID'));
  const sh = book.getSheetByName(p.getProperty('SHEET_NAME') || 'listings');
  if (!sh) throw new Error('listings シートが見つかりません');
  return sh;
}

function streamSheet_() {
  const p = PropertiesService.getScriptProperties();
  const book = SpreadsheetApp.openById(p.getProperty('SHEET_ID'));
  let sh = book.getSheetByName(STREAM_SHEET);
  if (!sh) {
    sh = book.insertSheet(STREAM_SHEET);
    sh.getRange(1, 1, 1, STREAM_HEAD.length).setValues([STREAM_HEAD]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}

/** 足りない列を右端に足す。人が手で列を用意する必要をなくす */
function ensureColumns_(sh, cols) {
  const head = sh.getRange(1, 1, 1, Math.max(sh.getLastColumn(), 1)).getValues()[0].map(String);
  const miss = cols.filter(function (c) { return head.indexOf(c) < 0; });
  if (!miss.length) return;
  sh.getRange(1, head.length + 1, 1, miss.length).setValues([miss]).setFontWeight('bold');
}

function colIndex_(sh) {
  const head = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(String);
  const idx = {}; head.forEach(function (h, i) { idx[h.trim()] = i + 1; });   // 1始まり
  return idx;
}

/* ---------------- 判定：フィードがあるか調べる ---------------- */
function probeFeeds_(sh) {
  const idx = colIndex_(sh);
  const last = sh.getLastRow();
  if (last < 2) return 0;
  const urls  = sh.getRange(2, idx['url'], last - 1, 1).getValues();
  const types = sh.getRange(2, idx['feed_type'], last - 1, 1).getValues();

  const todo = [];
  for (let i = 0; i < urls.length; i++) {
    const u = String(urls[i][0] || '').trim();
    if (!u) continue;
    if (String(types[i][0] || '').trim()) continue;        // 判定済みは飛ばす
    todo.push({ row: i + 2, url: u });
  }
  if (!todo.length) return 0;

  let done = 0;
  for (let s = 0; s < todo.length; s += BATCH) {
    if (overTime_()) break;
    const part = todo.slice(s, s + BATCH);
    const reqs = part.map(function (t) {
      return { url: t.url, muteHttpExceptions: true, followRedirects: true };
    });
    let res = [];
    try { res = UrlFetchApp.fetchAll(reqs); } catch (e) { res = []; }
    part.forEach(function (t, k) {
      const body = (res[k] && res[k].getResponseCode() === 200) ? res[k].getContentText() : '';
      const f = detectFeed_(t.url, body);
      sh.getRange(t.row, idx['feed_url']).setValue(f.url || '');
      sh.getRange(t.row, idx['feed_type']).setValue(f.type);
      sh.getRange(t.row, idx['auto_update']).setValue(f.type === 'none' ? 'FALSE' : 'TRUE');
      sh.getRange(t.row, idx['check_status']).setValue(f.type === 'none' ? 'ok' : 'ok');
      done++;
    });
  }
  return done;
}

/** URLと本文から、監視できるフィードを見つける */
function detectFeed_(url, body) {
  // TikTok / Instagram / X は公開フィードが無い。掲載はするが自動取得はしない
  if (/tiktok\.com|instagram\.com|(^|\.)x\.com|twitter\.com/i.test(url)) return { type: 'none', url: '' };

  // YouTube：チャンネルIDがあれば公式Atom
  let m = url.match(/\/channel\/(UC[\w-]{20,})/);
  if (m) return { type: 'youtube_rss', url: ytFeed_(m[1]) };
  if (/youtube\.com|youtu\.be/i.test(url)) {
    // @handle や /c/ は本文からチャンネルIDを拾う
    m = body.match(/"channelId":"(UC[\w-]{20,})"/) || body.match(/channel_id=(UC[\w-]{20,})/);
    if (m) return { type: 'youtube_rss', url: ytFeed_(m[1]) };
    return { type: 'none', url: '' };
  }

  // note は規約でURLが決まっている
  m = url.match(/note\.com\/([^\/\?#]+)/);
  if (m) return { type: 'rss', url: 'https://note.com/' + m[1] + '/rss' };

  // それ以外は本文から自動発見
  const link = body.match(/<link[^>]+type=["']application\/(?:rss|atom)\+xml["'][^>]*>/i);
  if (link) {
    const href = link[0].match(/href=["']([^"']+)["']/i);
    if (href) return { type: 'rss', url: absolute_(url, href[1]) };
  }
  return { type: 'none', url: '' };
}

function ytFeed_(id) { return 'https://www.youtube.com/feeds/videos.xml?channel_id=' + id; }

function absolute_(base, href) {
  if (/^https?:\/\//i.test(href)) return href;
  const m = base.match(/^(https?:\/\/[^\/]+)(.*)$/);
  if (!m) return href;
  if (href.indexOf('/') === 0) return m[1] + href;
  return m[1] + m[2].replace(/[^\/]*$/, '') + href;
}

/* ---------------- 取得：新しい回を拾う ---------------- */
function fetchFeeds_(sh) {
  const idx = colIndex_(sh);
  const last = sh.getLastRow();
  if (last < 2) return 0;
  const width = sh.getLastColumn();
  const all = sh.getRange(2, 1, last - 1, width).getValues();

  const todo = [];
  for (let i = 0; i < all.length; i++) {
    const row = all[i];
    const auto = String(row[idx['auto_update'] - 1] || '').toUpperCase();
    const furl = String(row[idx['feed_url'] - 1] || '').trim();
    const st   = String(row[idx['check_status'] - 1] || '');
    if (auto !== 'TRUE' || !furl || st === 'retired') continue;
    todo.push({
      row: i + 2,
      id: Number(row[idx['id'] - 1] || (i + 1)),
      feed: furl,
      type: String(row[idx['feed_type'] - 1] || ''),
      since: row[idx['last_checked_at'] - 1] ? new Date(row[idx['last_checked_at'] - 1]) : null,
      fail: Number(row[idx['fail_count'] - 1] || 0)
    });
  }
  if (!todo.length) return 0;

  const st = streamSheet_();
  const known = knownIds_(st);
  const now = new Date();
  const add = [];
  let n = 0;

  for (let s = 0; s < todo.length; s += BATCH) {
    if (overTime_()) break;
    const part = todo.slice(s, s + BATCH);
    let res = [];
    try {
      res = UrlFetchApp.fetchAll(part.map(function (t) {
        return { url: t.feed, muteHttpExceptions: true, followRedirects: true };
      }));
    } catch (e) { res = []; }

    part.forEach(function (t, k) {
      const ok = res[k] && res[k].getResponseCode() === 200;
      sh.getRange(t.row, idx['last_checked_at']).setValue(now);
      if (!ok) {
        const f = t.fail + 1;
        sh.getRange(t.row, idx['fail_count']).setValue(f);
        // 自動では消さない。4回続けて駄目なら人が見る印を付けるだけ
        sh.getRange(t.row, idx['check_status']).setValue(f >= 4 ? 'retired' : (f >= 3 ? 'fail' : 'ok'));
        return;
      }
      sh.getRange(t.row, idx['fail_count']).setValue(0);
      sh.getRange(t.row, idx['check_status']).setValue('ok');

      const items = parseFeed_(res[k].getContentText()).slice(0, MAX_ITEMS);
      let newest = null;
      items.forEach(function (x) {
        if (!x.id || !x.title) return;
        const key = t.id + '|' + x.id;
        if (known[key]) return;
        if (t.since && x.at && x.at <= t.since) return;      // 前回見に行った時点より後だけ
        if (x.at && x.at > now) return;                       // 未来日は捨てる
        known[key] = true;
        add.push([t.id, x.id, String(x.title).slice(0, 120), x.url, x.at || now, 'episode', now, 'ok']);
        if (!newest || (x.at && x.at > newest)) newest = x.at;
        n++;
      });
      if (newest) sh.getRange(t.row, idx['last_item_at']).setValue(newest);
    });
  }

  if (add.length) st.getRange(st.getLastRow() + 1, 1, add.length, STREAM_HEAD.length).setValues(add);
  return n;
}

function knownIds_(st) {
  const out = {};
  const last = st.getLastRow();
  if (last < 2) return out;
  const v = st.getRange(2, 1, last - 1, 2).getValues();
  v.forEach(function (r) { out[r[0] + '|' + r[1]] = true; });
  return out;
}

/** Atom と RSS の両方を読む */
function parseFeed_(body) {
  const out = [];
  const entries = body.match(/<entry[\s>][\s\S]*?<\/entry>/g);
  if (entries) {                                   // Atom（YouTubeなど）
    entries.forEach(function (e) {
      const vid = pick_(e, 'yt:videoId') || pick_(e, 'id');
      const ttl = pick_(e, 'title');
      const pub = pick_(e, 'published') || pick_(e, 'updated');
      const lnk = (e.match(/<link[^>]+href=["']([^"']+)["']/) || [])[1];
      out.push({ id: vid, title: ttl, url: lnk || '', at: pub ? new Date(pub) : null });
    });
    return out;
  }
  const items = body.match(/<item[\s>][\s\S]*?<\/item>/g);   // RSS
  if (items) {
    items.forEach(function (e) {
      const lnk = pick_(e, 'link');
      const gid = pick_(e, 'guid') || lnk;
      const ttl = pick_(e, 'title');
      const pub = pick_(e, 'pubDate') || pick_(e, 'dc:date');
      out.push({ id: gid, title: ttl, url: lnk || '', at: pub ? new Date(pub) : null });
    });
  }
  return out;
}

function pick_(xml, tag) {
  const m = xml.match(new RegExp('<' + tag + '[^>]*>([\\s\\S]*?)<\\/' + tag + '>'));
  if (!m) return '';
  return m[1].replace(/<!\[CDATA\[([\s\S]*?)\]\]>/, '$1')
             .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"').replace(/&#39;/g, "'").trim();
}

/** 実行時間が6分に近づいたら中断する。次の週に続きをやる */
let _t0 = null;
function overTime_() {
  if (!_t0) _t0 = new Date();
  return (new Date() - _t0) > 4 * 60 * 1000;
}

/** 取得の状況を見る */
function updateStatus() {
  const sh = listSheet_(); const idx = colIndex_(sh);
  const last = sh.getLastRow();
  const v = sh.getRange(2, 1, last - 1, sh.getLastColumn()).getValues();
  const c = { 未判定: 0, 自動: 0, 手動のみ: 0, 失敗: 0, 退役: 0 };
  v.forEach(function (r) {
    const ft = String(r[idx['feed_type'] - 1] || '');
    const st = String(r[idx['check_status'] - 1] || '');
    if (!ft) c.未判定++;
    else if (ft === 'none') c.手動のみ++;
    else c.自動++;
    if (st === 'fail') c.失敗++;
    if (st === 'retired') c.退役++;
  });
  Logger.log('未判定     : ' + c.未判定 + '（次回の weeklyUpdate で判定されます）');
  Logger.log('自動取得   : ' + c.自動);
  Logger.log('自動不可   : ' + c.手動のみ + '（TikTok/Instagram/フィード無し。掲載は続きます）');
  Logger.log('連続失敗中 : ' + c.失敗);
  Logger.log('退役       : ' + c.退役 + '（消していません。人が確認してください）');
  Logger.log('溜まった回 : ' + Math.max(0, streamSheet_().getLastRow() - 1));
}

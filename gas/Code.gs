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
    const q = String((e && e.parameter && e.parameter.q) || '').slice(0, 400);
    if (!q.trim()) return json_({ ok: true, items: getCatalog_().length, models: models_() });
    return json_(askGemini_(q, getCatalog_()));
  } catch (err) {
    return json_({ ids: [], answer: '', error: String((err && err.message) || err) });
  }
}

/** 念のため POST も受ける */
function doPost(e) {
  try {
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

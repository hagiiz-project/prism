# -*- coding: utf-8 -*-
"""物品分解。掲載のときにも、送客のときにも、必ずここを通る共有ステージ。
「いく」は物品ではなく 移動・滞在・入場 が発生するため、そこも対象に含める。"""
import re

LLM_PROMPT = """あなたは理科教育と科学イベントの準備担当です。
以下の本文から、この活動を実施・参加するために実際に用意しなければならないものを抽出してください。
制約:
- 本文にないものを推測で足さない。ただし実施上ほぼ確実に要るものは inferred=true を付けて挙げてよい
- 現地に行くものは、移動・滞在・入場・持ち物も対象に含める
- 1件につき: name, category(材料/道具/機材/持ち物/移動/滞在/入場), spec, qty_note,
  consumable, substitute, likely_owned, safety, inferred, confidence(0-1)
出力はJSON配列のみ。
本文:
"""

M = {
 "砂":dict(c=True,b="500-1500円",cat="材料",sub="園芸用の砂で代用可"),
 "霧吹き":dict(c=False,b="200-600円",cat="道具",sub="ドレッシングボトルで代用可",own=True),
 "炭酸用ペットボトル":dict(c=True,b="100-200円",cat="材料",sub="飲み終えた容器で可"),
 "線香":dict(c=True,b="300-800円",cat="材料",saf="火気。換気と着火役を決める"),
 "透明容器":dict(c=False,b="500-2000円",cat="道具",sub="タッパーや水槽で代用可",own=True),
 "養生シート":dict(c=True,b="500-1500円",cat="材料",sub="新聞紙とゴミ袋で代用可"),
 "模造紙":dict(c=True,b="300-900円",cat="材料"),
 "付箋":dict(c=True,b="300-800円",cat="材料",own=True),
 "色ペン":dict(c=True,b="500-1500円",cat="材料",own=True),
 "印刷用紙":dict(c=True,b="500-1000円",cat="材料",own=True),
 "記録用ノート":dict(c=True,b="200-600円",cat="材料",own=True),
 "乾電池":dict(c=True,b="500-1500円",cat="材料"),
 "導線":dict(c=True,b="500-1500円",cat="材料"),
 "LED":dict(c=True,b="500-1500円",cat="材料"),
 "磁石":dict(c=False,b="500-2000円",cat="道具"),
 "虫めがね":dict(c=False,b="300-1500円",cat="道具",own=True),
 "顕微鏡":dict(c=False,b="8000-60000円",cat="機材",own=True),
 "プレパラート":dict(c=True,b="800-2500円",cat="材料"),
 "ピンセット":dict(c=False,b="300-1200円",cat="道具",own=True),
 "観察ケース":dict(c=False,b="500-2000円",cat="道具"),
 "双眼鏡":dict(c=False,b="4000-20000円",cat="機材"),
 "星座早見盤":dict(c=False,b="400-1200円",cat="道具"),
 "赤色ライト":dict(c=False,b="800-3000円",cat="道具",sub="懐中電灯に赤いセロファンで代用可"),
 "ハザードマップ":dict(c=True,b="無料配布",cat="材料",sub="自治体サイトから印刷"),
 "保護めがね":dict(c=False,b="800-2500円",cat="機材",saf="薬品・飛散を伴う場合は必須"),
 "軍手":dict(c=True,b="300-800円",cat="材料"),
 "ヘルメット":dict(c=False,b="2000-5000円",cat="機材",saf="規格品を使う"),
 "解剖ばさみ":dict(c=False,b="1000-4000円",cat="機材",saf="刃物。取り扱い説明を先に行う"),
 "重曹":dict(c=True,b="300-800円",cat="材料"),
 "クエン酸":dict(c=True,b="300-900円",cat="材料"),
 "紙コップ":dict(c=True,b="200-600円",cat="材料"),
 "ストロー":dict(c=True,b="200-500円",cat="材料"),
 "風船":dict(c=True,b="300-900円",cat="材料"),
 "輪ゴム":dict(c=True,b="200-500円",cat="材料",own=True),
 "培養土":dict(c=True,b="400-1200円",cat="材料"),
 "種子":dict(c=True,b="200-600円",cat="材料"),
 "プロジェクタ":dict(c=False,b="30000円〜",cat="機材",own=True),
 "延長コード":dict(c=False,b="800-2000円",cat="道具",own=True),
 "タブレット":dict(c=False,b="—",cat="機材",own=True),
 "温度計":dict(c=False,b="500-2500円",cat="道具",own=True),
 # 「いく」で発生するもの。旅行系の接点
 "入場券":dict(c=True,b="無料〜2000円",cat="入場"),
 "交通費":dict(c=True,b="実費",cat="移動"),
 "宿泊":dict(c=True,b="実費",cat="滞在"),
 "弁当・飲み物":dict(c=True,b="実費",cat="持ち物"),
 "雨具":dict(c=False,b="500-3000円",cat="持ち物",own=True),
 "歩きやすい靴":dict(c=False,b="—",cat="持ち物",own=True),
 "防寒具":dict(c=False,b="—",cat="持ち物",own=True),
 "日よけ・帽子":dict(c=False,b="1000-3000円",cat="持ち物",own=True),
}
RULES = [
 (r"土砂|斜面|地盤|液状化|流水|侵食", ["砂","透明容器","霧吹き","養生シート","記録用ノート"]),
 (r"雲|気圧|天気|気象|前線",          ["炭酸用ペットボトル","線香","印刷用紙","記録用ノート"]),
 (r"防災|避難|ハザード|災害|地震|津波",["ハザードマップ","色ペン","付箋","模造紙"]),
 (r"星|天体|宇宙|惑星|プラネタリウム",["星座早見盤","赤色ライト","防寒具","双眼鏡"]),
 (r"昆虫|生きもの|植物|動物|飼育|観察",["観察ケース","虫めがね","記録用ノート","ピンセット"]),
 (r"顕微鏡|細胞|プランクトン|標本",    ["顕微鏡","プレパラート","ピンセット"]),
 (r"化学|反応|結晶|溶液|薬品",         ["保護めがね","軍手","重曹","クエン酸","紙コップ"]),
 (r"電気|回路|電子|発電|モーター|ロボット",["乾電池","導線","LED","磁石"]),
 (r"工作|ものづくり|プログラミング",   ["乾電池","導線","輪ゴム","記録用ノート"]),
 (r"ワークショップ|体験|教室|講座",    ["模造紙","付箋","色ペン","印刷用紙"]),
 (r"講演|トーク|出張授業|ショー",      ["プロジェクタ","延長コード","印刷用紙"]),
 (r"動画|オンライン|アプリ|VR|配信",   ["タブレット","印刷用紙"]),
 (r"図鑑|書籍|漫画|読む",              ["付箋","記録用ノート"]),
]
GO_BASE   = ["入場券","交通費","弁当・飲み物","歩きやすい靴"]
GO_FIELD  = ["雨具","日よけ・帽子"]

def decompose(text="", fmt="", field="", topics=(), act_group="", media_type="", far=False, outdoor=False):
    hay = " ".join([text or "", fmt or "", field or "", " ".join(topics or []), media_type or ""])
    names, seen = [], set()
    if act_group == "いく":
        for n in GO_BASE: seen.add(n); names.append(n)
        if far:  seen.add("宿泊"); names.append("宿泊")
        if outdoor:
            for n in GO_FIELD:
                if n not in seen: seen.add(n); names.append(n)
    for rx, items in RULES:
        if re.search(rx, hay):
            for n in items:
                if n not in seen: seen.add(n); names.append(n)
    if not names: names = ["印刷用紙","記録用ノート"]
    out = []
    for n in names[:8]:
        m = M[n]
        out.append(dict(name=n, material_id=n, category=m["cat"], consumable=m["c"], spec=None,
            qty_note=None, band=m["b"], substitute=m.get("sub"), likely_owned=m.get("own", False),
            safety=m.get("saf"), inferred=(n in GO_BASE), confidence=0.6,
            review_state="needs_review" if m.get("saf") else "auto_ok", source="rule"))
    return out

# -*- coding: utf-8 -*-
"""アフィリエイト解決。物品分解の結果だけを入力にする。
  1. safety が付いた物品は出さない
  2. 開示文は必ず付ける（一覧の下に1行）
  3. 掲載順は手数料で変えない
"""
import os
from urllib.parse import quote

IDS = dict(amazon=os.environ.get("AMAZON_TAG",""), rakuten=os.environ.get("RAKUTEN_ID",""),
           rakuten_travel=os.environ.get("RAKUTEN_TRAVEL_ID",""), jalan=os.environ.get("JALAN_ID",""))
GOODS_CAT  = {"材料","道具","機材","持ち物"}
TRAVEL_CAT = {"移動","滞在","入場"}
DISCLOSURE = {
 "goods":"この一覧のリンクから購入があった場合、プリズムに手数料が入ります。掲載順や表示内容は手数料の有無で変えていません。",
 "travel":"宿泊・交通のリンクから予約があった場合、プリズムに手数料が入ります。施設の掲載順や説明は手数料の有無で変えていません。"}

def goods_links(m, area=""):
    if m.get("safety"):
        return dict(gated=True, reason="安全に関わるため、確認がすむまで購入先を出さない", links={})
    cat = m.get("category")
    if cat in TRAVEL_CAT:
        if cat == "滞在":
            q = quote(area or "")
            return dict(gated=False, disclosure="travel", links=dict(rakuten_travel=
                f"https://travel.rakuten.co.jp/dsearch/?f_keyword={q}"
                + (f"&f_teikei={IDS['rakuten_travel']}" if IDS['rakuten_travel'] else "")))
        return dict(gated=True, reason=f"{cat}のため物販の対象外。金額の目安のみ表示する", links={})
    q = quote(m["name"])
    return dict(gated=False, disclosure="goods", links=dict(
        amazon=f"https://www.amazon.co.jp/s?k={q}" + (f"&tag={IDS['amazon']}" if IDS['amazon'] else ""),
        rakuten=f"https://search.rakuten.co.jp/search/mall/{q}/" + (f"?scid={IDS['rakuten']}" if IDS['rakuten'] else "")))

def travel_links(listing):
    if listing.get("act_group") != "いく": return None
    pref = (listing.get("region_pref") or "").strip()
    if not pref: return dict(gated=True, reason="所在地が未確認のため出さない", links={})
    area = quote(pref + (listing.get("region_city") or ""))
    return dict(gated=False, disclosure="travel", links=dict(
        rakuten_travel=f"https://travel.rakuten.co.jp/dsearch/?f_keyword={area}"
            + (f"&f_teikei={IDS['rakuten_travel']}" if IDS['rakuten_travel'] else ""),
        jalan=f"https://www.jalan.net/kankou/?keyword={area}" + (f"&vos={IDS['jalan']}" if IDS['jalan'] else "")))

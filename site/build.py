#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSV → 1枚のHTML。パイプラインが出したCSVをそのまま読む。

  python3 site/build.py --listings data/listings.csv --materials data/materials.csv --out _site/index.html

アフィリエイトIDは環境変数から入れる（ソースに書かない）。
  AMAZON_TAG / RAKUTEN_ID / RAKUTEN_TRAVEL_ID
"""
import argparse, csv, io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism import taxonomy, monetize

CTA = {"無料":"見る・使う","購入（買い切り）":"買う","予約（日時指定）":"予約する",
       "要見積もり":"相談・依頼する","サブスク":"申し込む","フリーミアム":"試す"}
BAND = {"材料":"300-1500円","道具":"300-2000円","機材":"1000円〜","持ち物":"—",
        "入場":"無料〜2000円","移動":"実費","滞在":"実費"}

def rows(p): return list(csv.DictReader(io.StringIO(open(p, encoding="utf-8-sig").read())))
def sp(v):   return [x for x in (v or "").split("|") if x]
def tf(v):   return str(v).strip().upper() == "TRUE"

def main(a):
    mats = {}
    if a.materials and os.path.exists(a.materials):
        for m in rows(a.materials):
            r = monetize.goods_links(dict(name=m["name"], category=m["category"],
                                          safety=m["safety"] or None), area="")
            mats.setdefault(str(m["listing_id"]), []).append(dict(
                name=m["name"], cat=m["category"], consumable=tf(m["consumable"]),
                band=BAND.get(m["category"], "—"), substitute=m["substitute"] or None,
                likely_owned=tf(m["likely_owned"]), safety=m["safety"] or None,
                review_state=m["review_state"], shop=r["links"]))
    items = []
    for i, r in enumerate(rows(a.listings), start=1):
        lid = str(r.get("id") or i)
        f = (r.get("field") or "").strip()
        items.append(dict(id=int(lid), url=r["url"].strip(), title=r["title"].strip(),
            desc=(r.get("description") or "").strip(), provider=r["provider"].strip(),
            ptype=r.get("providerType") or r.get("provider_type") or "",
            field=f, fmt=r.get("format",""),
            grp=r.get("act_group") or taxonomy.MEDIA.get(r.get("media_type",""),{}).get("act")
                or taxonomy.FORMAT_TO_ACT.get(r.get("format",""), "つかう"),
            audience=sp(r.get("audience")), purpose=sp(r.get("purpose")),
            scale=r.get("scale",""), level=r.get("level",""), txn=r.get("txn",""),
            cta=CTA.get(r.get("txn",""), "見る"), price=r.get("priceNum") or r.get("price_num") or "",
            topics=sp(r.get("topics")), since=r.get("year_since",""),
            freq=r.get("更新頻度") or r.get("update_freq") or "",
            mats=mats.get(lid, [])))
    db = dict(items=items, groups=taxonomy.ACT_GROUPS,
        fields=sorted({i["field"] for i in items if i["field"]}),
        ptypes=sorted({i["ptype"] for i in items if i["ptype"]}),
        txns=taxonomy.TXNS, audiences=taxonomy.AUDIENCES,
        purposes=sorted({p for i in items for p in i["purpose"]}),
        disclosure_goods=monetize.DISCLOSURE["goods"],
        disclosure_travel=monetize.DISCLOSURE["travel"])
    here = os.path.dirname(os.path.abspath(__file__))
    tpl = open(os.path.join(here, "template.html"), encoding="utf-8").read()
    html = tpl.replace("__PRISM_DATA__", json.dumps(db, ensure_ascii=False))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(html)
    nm = sum(len(i["mats"]) for i in items)
    print(f"{a.out}（{len(items)}件 / 物品 {nm}点 / {len(html.encode())//1024}KB）")
    if not os.environ.get("AMAZON_TAG"):
        print("※ AMAZON_TAG などが未設定のため、リンクはアフィリエイトIDなしの検索URLです。")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--listings", default="data/listings.csv")
    p.add_argument("--materials", default="data/materials.csv")
    p.add_argument("--out", default="_site/index.html")
    main(p.parse_args())

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

def recent_stream(path, items_by_id, days_first=7, days_fallback=30, per_listing=2, total=20):
    """今週の更新。7日で足りなければ30日に広げる。1掲載につき最大2件。"""
    import datetime
    if not path or not os.path.exists(path): return []
    rows = list(csv.DictReader(io.StringIO(open(path, encoding="utf-8-sig").read())))
    now = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for r in rows:
        t = (r.get("title") or "").strip()
        if not t: continue
        lid = str(r.get("listing_id") or "")
        li = items_by_id.get(lid)
        if not li: continue
        raw = (r.get("published_at") or "").strip()
        try:
            d = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if d.tzinfo is None: d = d.replace(tzinfo=datetime.timezone.utc)
        except Exception:
            continue
        out.append(dict(listing_id=int(lid), title=t[:90], url=(r.get("url") or li["url"]),
                        at=d.strftime("%-m月%-d日") if os.name != "nt" else d.strftime("%m月%d日"),
                        ts=d, provider=li["provider"], fmt=li["fmt"]))
    out.sort(key=lambda x: x["ts"], reverse=True)

    def pick(days):
        lim = now - datetime.timedelta(days=days)
        seen, res = {}, []
        for x in out:
            if x["ts"] < lim: continue
            n = seen.get(x["listing_id"], 0)
            if n >= per_listing: continue
            seen[x["listing_id"]] = n + 1
            res.append(x)
            if len(res) >= total: break
        return res

    got = pick(days_first) or pick(days_fallback)
    for x in got: x.pop("ts", None)
    return got


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
            last_item_at=(r.get("last_item_at") or "").strip()[:10],
            mats=mats.get(lid, [])))
    # 検索の語候補：topics の出現頻度から実際によく出る語を拾う
    from collections import Counter
    tc = Counter(t for i in items for t in i["topics"])
    topics_top = [t for t, n in tc.most_common(60) if n >= 2]

    by_id = {str(i["id"]): i for i in items}
    stream = recent_stream(a.stream, by_id)

    db = dict(items=items, groups=taxonomy.ACT_GROUPS, topics_top=topics_top, stream=stream,
        fields=sorted({i["field"] for i in items if i["field"]}),
        ptypes=sorted({i["ptype"] for i in items if i["ptype"]}),
        txns=taxonomy.TXNS, audiences=taxonomy.AUDIENCES,
        purposes=sorted({p for i in items for p in i["purpose"]}),
        disclosure_goods=monetize.DISCLOSURE["goods"],
        disclosure_travel=monetize.DISCLOSURE["travel"])
    here = os.path.dirname(os.path.abspath(__file__))
    tpl = open(os.path.join(here, "template.html"), encoding="utf-8").read()
    html = tpl.replace("__PRISM_DATA__", json.dumps(db, ensure_ascii=False))
    html = html.replace("__AI_ENDPOINT__", os.environ.get("AI_ENDPOINT", ""))
    html = html.replace("REPLACE_WITH_YOUR_EMAIL", os.environ.get("CONTACT_EMAIL", "REPLACE_WITH_YOUR_EMAIL"))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(html)
    nm = sum(len(i["mats"]) for i in items)
    print(f"{a.out}（{len(items)}件 / 物品 {nm}点 / 今週の更新 {len(stream)}件 / {len(html.encode())//1024}KB）")
    if not os.environ.get("AMAZON_TAG"):
        print("※ AMAZON_TAG などが未設定のため、リンクはアフィリエイトIDなしの検索URLです。")
    if not os.environ.get("AI_ENDPOINT"):
        print("※ AI_ENDPOINT が未設定のため、「AIに聞く」は接続先なしの表示になります。")
    if not os.environ.get("CONTACT_EMAIL"):
        print("※ CONTACT_EMAIL が未設定です。フッターの連絡先が未設定のままです。")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--listings", default="data/listings.csv")
    p.add_argument("--materials", default="data/materials.csv")
    p.add_argument("--stream", default="data/stream.csv")
    p.add_argument("--out", default="_site/index.html")
    main(p.parse_args())

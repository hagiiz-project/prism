#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""プリズム パイプライン

  python3 run.py template                        CSVの列の説明を出す
  python3 run.py seeds                           探索元の一覧
  python3 run.py submit --url URL [--offline]    掲載1件（取得→抽出→物品分解→送客解決）
  python3 run.py decompose --in data/listings.csv --out data/materials.csv
  python3 run.py coverage  --in data/listings.csv
"""
import argparse, csv, io, json, os, urllib.request
from datetime import datetime, timezone
from prism import schema, taxonomy, extract, decompose as dec, monetize, discover, sheet

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
HERE = os.path.dirname(os.path.abspath(__file__))

def rows_from(p): return list(csv.DictReader(io.StringIO(open(p, encoding="utf-8-sig").read())))
def write_csv(path, cols, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=schema.header(cols)); w.writeheader()
        for r in rows: w.writerow({k: r.get(k, "") for k in schema.header(cols)})
def act_of(r):
    return (r.get("act_group") or taxonomy.MEDIA.get(r.get("media_type",""), {}).get("act")
            or taxonomy.FORMAT_TO_ACT.get(r.get("format",""), "つかう"))
def fetch(url, offline):
    if offline: return f"<html><head><title>{url}</title></head><body>offline sample</body></html>"
    req = urllib.request.Request(url, headers={"User-Agent":"PrismCollector/0.2 (+contact@example.jp)"})
    with urllib.request.urlopen(req, timeout=20) as r: return r.read().decode("utf-8","replace")

def cmd_template(a):
    for name, cols in [("listings",schema.LISTINGS),("materials",schema.MATERIALS),
                       ("affiliate",schema.AFFILIATE),("sources",schema.SOURCES)]:
        write_csv(os.path.join(HERE,"templates",f"{name}_template.csv"), cols, [])
        print(f"■ {name}_template.csv"); print(schema.doc(cols)); print()
    print("語彙：")
    print("  何をしたいか :", " / ".join(taxonomy.ACT_GROUPS))
    print("  メディア種別 :", " / ".join(taxonomy.MEDIA.keys()))
    print("  提供者種別   :", " / ".join(taxonomy.PROVIDER_TYPES))

def cmd_seeds(a):
    cur = None
    for s in discover.SEEDS:
        if s["act"] != cur: cur = s["act"]; print(f"\n■ {cur}")
        print(f"   {s['media']:<11} {s['how']:<18} {s['note']}")

def cmd_submit(a):
    base = extract.from_html(a.url, fetch(a.url, a.offline))
    if a.title: base["title"] = a.title
    feed = extract.feed_for(a.url, base["media_type"], a.freq)
    mats = dec.decompose(text=base.get("description","")+" "+base.get("title",""),
        fmt=base["media_type"], field=a.field or "", topics=(a.topics or "").split("|"),
        act_group=a.act or base["act_group"], media_type=base["media_type"], far=a.far, outdoor=a.outdoor)
    listing = dict(id=a.id or 0, url=a.url, title=base["title"], provider=base["provider"],
        media_type=base["media_type"], act_group=a.act or base["act_group"], field=a.field or "",
        region_pref=a.pref or "", region_city=a.city or "", description=base.get("description",""),
        source_feed=feed["url"], status="needs_review", updated_at=NOW())
    print(f"■ 掲載候補  {listing['title'][:50]}")
    print(f"   媒体 {listing['media_type']} / 何をしたいか {listing['act_group']}")
    print(f"   更新監視 {feed['source_type']}（{feed['cadence']}） {feed['url'][:70]}")
    print(f"\n■ 物品分解  {len(mats)}点（毎回いるもの {sum(1 for m in mats if m['consumable'])}点）")
    for m in mats:
        r = monetize.goods_links(m, listing["region_pref"] + listing["region_city"])
        tag = "毎回" if m["consumable"] else "再利用"
        sub = f"／代用: {m['substitute']}" if m["substitute"] else ""
        dest = "／".join(r["links"].keys()) if not r["gated"] else f"× {r['reason']}"
        print(f"   [{m['category']}/{tag}] {m['name']}  {m['band']}{sub}")
        print(f"        → {dest}")
    t = monetize.travel_links(listing)
    if t and not t["gated"]: print(f"\n■ 旅行  宿泊・周辺 → {'／'.join(t['links'].keys())}")
    print("\n" + monetize.DISCLOSURE["goods"])
    print("※ status=needs_review。提供者が確認するまで公開しない。")
    if a.csv:
        write_csv(a.csv, schema.LISTINGS, [listing])
        print(f"→ {a.csv} に1行書き出しました。data/listings.csv に貼り足してください。")

def cmd_sync(a):
    """Googleスプレッドシート → data/listings.csv"""
    sid = a.sheet or os.environ.get("SHEET_ID", "")
    if not sid:
        print("SHEET_ID が指定されていません。--sheet か環境変数 SHEET_ID を設定してください。")
        print("設定がないので、いまの data/listings.csv をそのまま使います。"); return
    rows = sheet.parse(sheet.fetch(sid, a.name))
    ok, ng = sheet.validate(rows)
    write_csv(a.out, schema.LISTINGS, [{k: r.get(k, "") for k in schema.header(schema.LISTINGS)} for r in ok])
    print(f"シートから {len(rows)}行 取得 → 公開 {len(ok)}件 / 見送り {len(ng)}件 → {a.out}")
    for i, t, why in ng[:20]:
        print(f"   {i}行目 {t[:28]:<30} {why}")
    if len(ng) > 20: print(f"   ほか {len(ng)-20}件")

def cmd_decompose(a):
    rows, out = rows_from(a.inp), []
    st = dict(n=0, con=0, gate=0, go=0)
    for i, r in enumerate(rows, start=1):
        act = act_of(r)
        mats = dec.decompose(text=r.get("description",""), fmt=r.get("format",""), field=r.get("field",""),
            topics=[t for t in (r.get("topics","") or "").split("|") if t], act_group=act,
            media_type=r.get("media_type",""), far=False,
            outdoor=("フィールド" in r.get("format","")))
        if act == "いく": st["go"] += 1
        for m in mats:
            st["n"] += 1; st["con"] += m["consumable"]; st["gate"] += bool(m["safety"])
            out.append(dict(listing_id=(r.get("id") or i), material_id=m["material_id"], name=m["name"],
                category=m["category"], consumable=str(m["consumable"]).upper(), qty_note="", spec="",
                substitute=m["substitute"] or "", likely_owned=str(m["likely_owned"]).upper(),
                safety=m["safety"] or "", inferred=str(m["inferred"]).upper(),
                review_state=m["review_state"], confidence=m["confidence"], source=m["source"]))
    write_csv(a.out, schema.MATERIALS, out)
    print(f"{len(rows)}件 → 物品 {st['n']}点（毎回いるもの {st['con']}点 = {round(st['con']/st['n']*100)}%）")
    print(f"  安全確認で購入導線を止めるもの {st['gate']}点／「いく」掲載 {st['go']}件")
    print(f"  → {a.out}")

def cmd_coverage(a):
    rows = rows_from(a.inp)
    for r in rows: r["act_group"] = act_of(r)
    c, m = discover.coverage(rows)
    print("■ 何をしたいか")
    for g in taxonomy.ACT_GROUPS:
        print(f"   {g:<8} {c.get(g,0):>4}件" + ("   ← 手薄" if c.get(g,0) < len(rows)*0.08 else ""))
    print("\n■ メディア種別")
    for k, v in m.most_common(12): print(f"   {k or '(未記入)':<12} {v:>4}件")

if __name__ == "__main__":
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("template").set_defaults(f=cmd_template)
    s.add_parser("seeds").set_defaults(f=cmd_seeds)
    b = s.add_parser("submit")
    for x in ("url","title","act","field","topics","pref","city","csv"): b.add_argument("--"+x)
    b.add_argument("--freq", default="月次"); b.add_argument("--id", type=int, default=0)
    b.add_argument("--far", action="store_true"); b.add_argument("--outdoor", action="store_true")
    b.add_argument("--offline", action="store_true"); b.set_defaults(f=cmd_submit)
    c = s.add_parser("decompose"); c.add_argument("--in", dest="inp", default="data/listings.csv")
    c.add_argument("--out", default="data/materials.csv"); c.set_defaults(f=cmd_decompose)
    e = s.add_parser("sync"); e.add_argument("--sheet"); e.add_argument("--name", default="listings")
    e.add_argument("--out", default="data/listings.csv"); e.set_defaults(f=cmd_sync)
    d = s.add_parser("coverage"); d.add_argument("--in", dest="inp", default="data/listings.csv")
    d.set_defaults(f=cmd_coverage)
    a = p.parse_args(); a.f(a)

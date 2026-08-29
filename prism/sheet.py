# -*- coding: utf-8 -*-
"""Googleスプレッドシートを掲載データベースとして読む。

シートを「ウェブに公開」しておけば、認証なしでCSVとして取得できる。
掲載フォーム（Googleフォーム）の回答も同じシートに入るので、
  フォーム投稿 → シート → ここ → 物品分解 → ビルド → 公開
が1本になる。
"""
import csv, io, re, urllib.request

def csv_url(sheet_id, sheet_name="listings"):
    """シートID と シート名 から CSV の取得URLを作る。"""
    return (f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
            f"?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}")

import urllib.parse  # noqa: E402

REQUIRED = ("url", "title", "provider", "description")

def fetch(sheet_id, sheet_name="listings", timeout=30):
    req = urllib.request.Request(csv_url(sheet_id, sheet_name),
                                 headers={"User-Agent": "PrismSync/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def validate(rows):
    """公開してよい行だけを通す。落とした行は理由つきで返す。"""
    ok, ng = [], []
    seen = set()
    for i, r in enumerate(rows, start=2):          # 2行目からがデータ
        miss = [k for k in REQUIRED if not (r.get(k) or "").strip()]
        if miss:
            ng.append((i, r.get("title", ""), "必須列が空：" + "／".join(miss))); continue
        u = r["url"].strip()
        if not re.match(r"^https?://", u):
            ng.append((i, r.get("title",""), "URLの形式が不正")); continue
        if u in seen:
            ng.append((i, r.get("title",""), "URLが重複")); continue
        seen.add(u)
        if (r.get("status") or "").strip() in ("gone", "rejected", "draft"):
            ng.append((i, r.get("title",""), f"status={r['status']} のため公開しない")); continue
        if (r.get("act_group") or "").strip() == "いく" and not (r.get("region_pref") or "").strip():
            r["region_pref"] = ""    # 落とさない。旅行リンクが出ないだけ
        ok.append(r)
    return ok, ng

def parse(text):
    return list(csv.DictReader(io.StringIO(text)))

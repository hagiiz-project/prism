# -*- coding: utf-8 -*-
"""URL → 掲載レコード。規則で埋め、残りをLLMに回す。"""
import re
from urllib.parse import urlparse
from .taxonomy import MEDIA

LLM_PROMPT_LISTING = """次のページ本文から掲載情報を抽出してください。書かれていないことは推測せず null に。
出力はJSONのみ。{"title":..,"provider":..,"providerType":..,"media_type":..,"format":..,"field":..,
"audience":[..],"purpose":[..],"scale":..,"level":..,"txn":..,"priceNum":..,"topics":[..],
"year_since":..,"region_pref":..,"region_city":..,"access_note":..,"description":"1〜3文"}
media_type は次から選ぶ: %s
本文:
""" % ", ".join(MEDIA.keys())

HOST_RULES = [(r"youtube\.com|youtu\.be","youtube"),(r"tiktok\.com","tiktok"),(r"instagram\.com","instagram"),
 (r"(^|\.)x\.com|twitter\.com","x"),(r"note\.com","note"),
 (r"open\.spotify\.com|anchor\.fm|podcasts\.apple\.com","podcast"),
 (r"nhk\.or\.jp|tv-asahi|ntv\.co\.jp|tbs\.co\.jp","broadcast"),
 (r"takaratomy|bandai|epoch\.jp|megahouse","toy"),
 (r"museum|kahaku|miraikan|planetarium","museum"),(r"\.ac\.jp","facility"),(r"\.go\.jp","facility")]

def guess_media(url, text=""):
    h = urlparse(url).netloc.lower() + urlparse(url).path.lower()
    for rx, m in HOST_RULES:
        if re.search(rx, h): return m
    t = text or ""
    for rx, m in [(r"科学館|博物館|プラネタリウム|展示","museum"),(r"出張授業|出前授業|講師派遣","outreach"),
                  (r"講演|トーク","person"),(r"ワークショップ|教室|体験","workshop"),(r"キット|教材","kit"),
                  (r"図鑑|書籍","book"),(r"アプリ|ゲーム","app")]:
        if re.search(rx, t): return m
    return "blog"

def feed_for(url, media, freq="月次"):
    u = urlparse(url); path = u.path
    cad = {"日次":"daily","週次":"weekly","月次":"monthly","年次":"yearly","手動":"manual"}.get(freq,"monthly")
    if media == "youtube":
        m = re.search(r"/channel/(UC[\w-]{20,})", path)
        if m: return dict(source_type="youtube_rss", extractor="atom_video", cadence="daily",
            url=f"https://www.youtube.com/feeds/videos.xml?channel_id={m.group(1)}", note="APIキー不要の公式Atom")
        return dict(source_type="manual", extractor="resolve_channel_id", cadence="manual", url=url,
            note="@handle は初回だけ channel_id を解決する")
    if media == "note":
        m = re.match(r"^/([^/]+)", path)
        if m: return dict(source_type="note_rss", extractor="rss_item", cadence=cad,
            url=f"https://note.com/{m.group(1)}/rss", note="")
    if media in ("tiktok","instagram","x"):
        return dict(source_type="manual", extractor="page_hash", cadence="manual", url=url,
            note="公開フィードなし。公式APIか経路③（見つけた人が登録）で更新する")
    if media == "podcast":
        return dict(source_type="rss", extractor="rss_item", cadence=cad, url=url, note="配信RSSを直接指定")
    if media == "event":
        return dict(source_type="ical_or_html", extractor="ics_event", cadence=cad, url=url,
            note="ICSがあれば開催回を取得。無ければ本文ハッシュ")
    return dict(source_type="rss_autodiscover", extractor="rss_then_hash", cadence=cad, url=url,
        note="RSSを探し、無ければ本文ハッシュ監視に降格")

OG = {k: re.compile(r'<meta[^>]+(?:property|name)=["\']og:%s["\'][^>]+content=["\'](.*?)["\']' % k, re.I|re.S)
      for k in ("title","description","image","site_name")}

def from_html(url, html):
    g = lambda k: (OG[k].search(html).group(1).strip() if OG[k].search(html) else None)
    t = re.search(r"<title>(.*?)</title>", html, re.S)
    title = g("title") or (t.group(1).strip() if t else "")
    media = guess_media(url, title + " " + (g("description") or ""))
    return dict(url=url, title=title, provider=g("site_name") or urlparse(url).netloc,
        media_type=media, act_group=MEDIA[media]["act"], description=g("description") or "",
        og_image=g("image"))

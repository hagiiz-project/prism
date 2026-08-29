# -*- coding: utf-8 -*-
"""CSV の列定義。これがフォーマットの正本。"""
LISTINGS = [
 ("id","通し番号。空なら自動採番"),("url","一次情報のURL。必須"),("title","名称。必須"),
 ("provider","提供者名。必須"),("providerType","taxonomy.PROVIDER_TYPES のいずれか"),
 ("media_type","taxonomy.MEDIA のキー。youtube / tiktok / toy / museum など"),
 ("format","表示用の形式名"),("act_group","何をしたいか。空なら自動補完"),
 ("field","分野。またぐ場合は空でよい"),("audience","'|'区切り"),("purpose","'|'区切り"),
 ("scale","1人 / 少人数（2〜10）/ 中規模（10〜50）/ 大規模（50+）"),("level","入門 / 初級 / 中級 / 上級"),
 ("txn","無料 / 購入（買い切り）/ 予約（日時指定）/ 要見積もり / サブスク / フリーミアム"),
 ("priceNum","数値のみ。不明は空"),("topics","'|'区切りの話題語"),("year_since","開始年"),
 ("更新頻度","日次 / 週次 / 月次 / 年次 / 手動"),
 ("region_pref","都道府県。「いく」で必須"),("region_city","市区町村"),("lat","緯度"),("lng","経度"),
 ("access_note","最寄り駅・所要時間など"),("description","1〜3文の説明"),
 ("source_feed","更新監視URL。空なら自動推定"),("license_note","利用条件の注意"),
 ("status","active / needs_review / stale / gone"),("updated_at","ISO8601"),
]
MATERIALS = [
 ("listing_id","対応する掲載のid"),("material_id","物品マスタの正規化キー"),("name","物品名（一般名）"),
 ("category","材料 / 道具 / 機材 / 持ち物 / 移動 / 滞在 / 入場"),
 ("consumable","TRUE=毎回いる FALSE=くり返し使える"),("qty_note","必要量"),("spec","規格・容量"),
 ("substitute","代用案"),("likely_owned","TRUE=学校等にありがち"),("safety","安全上の注意"),
 ("inferred","TRUE=推定"),("review_state","auto_ok / needs_review / approved / rejected"),
 ("confidence","0.0〜1.0"),("source","rule / llm / provider / practice"),
]
AFFILIATE = [("ref_type","material / listing"),("ref_id","参照先id"),
 ("network","amazon / rakuten / rakuten_travel / jalan"),("query","検索語"),("url","遷移先"),
 ("gated","TRUE=表示しない"),("disclosure","開示文のキー"),("updated_at","ISO8601")]
SOURCES = [("listing_id","掲載のid"),("source_type","youtube_rss / note_rss / rss_autodiscover / ical / html_watch / manual"),
 ("url","監視URL"),("cadence","daily / weekly / monthly / yearly / manual"),
 ("extractor","atom_video / rss_item / page_hash / ics_event"),("note","備考")]
def header(cols): return [c for c,_ in cols]
def doc(cols):    return "\n".join(f"  {c:<14} {d}" for c,d in cols)

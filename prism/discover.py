# -*- coding: utf-8 -*-
"""情報収集の探索元。6区分すべてを埋めるための地図。"""
SEEDS = [
 dict(act="みる・きく",media="youtube",how="チャンネル検索",note="科学 解説 / 実験 などで列挙し channel_id を解決"),
 dict(act="みる・きく",media="tiktok",how="手動＋公式API",note="公開フィードなし。ハッシュタグから人手で候補を出す"),
 dict(act="みる・きく",media="instagram",how="手動＋公式API",note="研究室・科学館の公式アカウントが中心"),
 dict(act="みる・きく",media="podcast",how="配信RSS",note="Apple/Spotify の科学カテゴリから RSS を取得"),
 dict(act="みる・きく",media="broadcast",how="番組表ページ",note="放送局の科学番組ページを月次で監視"),
 dict(act="よむ",media="note",how="note RSS",note="/{user}/rss。科学系マガジンから著者を辿る"),
 dict(act="よむ",media="book",how="出版社の新刊ページ",note="図鑑・学習まんが・一般書をシリーズ単位で"),
 dict(act="よむ",media="magazine",how="RSS",note="科学雑誌・大学広報誌"),
 dict(act="つかう",media="toy",how="メーカー製品ページ",note="玩具メーカーの知育・科学カテゴリ"),
 dict(act="つかう",media="kit",how="教材メーカー",note="理科教材の総合カタログ"),
 dict(act="つかう",media="instrument",how="機材メーカー",note="顕微鏡・望遠鏡・観測機器"),
 dict(act="やってみる",media="event",how="イベント一覧・ICS",note="科学イベント、大学祭、地域の科学の日"),
 dict(act="やってみる",media="workshop",how="施設の催し物ページ",note="科学館・公民館・図書館の講座欄"),
 dict(act="やってみる",media="program",how="養成講座の募集ページ",note="年次。募集時期が決まっている"),
 dict(act="やってみる",media="community",how="学会の広報委員会",note="市民科学・アウトリーチ部会"),
 dict(act="よぶ・あう",media="outreach",how="大学の社会連携ページ",note="出前授業の一覧。.ac.jp に集中"),
 dict(act="よぶ・あう",media="person",how="講師派遣の窓口",note="学会・自治体の講師バンク"),
 dict(act="いく",media="museum",how="施設一覧",note="全国科学館連携協議会などの加盟館リスト"),
 dict(act="いく",media="facility",how="研究機関広報",note="研究所の一般公開、工場見学"),
 dict(act="いく",media="fieldsite",how="自治体・自然公園",note="ジオパーク、ビジターセンター"),
]
def coverage(rows):
    from collections import Counter
    return (Counter(r.get("act_group") or "" for r in rows),
            Counter(r.get("media_type") or "" for r in rows))

# -*- coding: utf-8 -*-
"""語彙。ここを増やせば網羅範囲が広がる。"""
ACT_GROUPS = ["みる・きく", "つかう", "よむ", "やってみる", "よぶ・あう", "いく"]

MEDIA = {
 "youtube":dict(label="YouTube",act="みる・きく",feed="youtube_rss"),
 "tiktok":dict(label="TikTok",act="みる・きく",feed="manual"),
 "instagram":dict(label="Instagram",act="みる・きく",feed="manual"),
 "x":dict(label="X（旧Twitter）",act="みる・きく",feed="manual"),
 "podcast":dict(label="ポッドキャスト",act="みる・きく",feed="rss"),
 "broadcast":dict(label="テレビ・ラジオ",act="みる・きく",feed="html_watch"),
 "note":dict(label="note",act="よむ",feed="note_rss"),
 "blog":dict(label="ブログ・Webメディア",act="よむ",feed="rss_autodiscover"),
 "book":dict(label="書籍・図鑑",act="よむ",feed="html_watch"),
 "magazine":dict(label="新聞・雑誌",act="よむ",feed="rss_autodiscover"),
 "app":dict(label="アプリ・ゲーム",act="みる・きく",feed="html_watch"),
 "toy":dict(label="玩具・製品",act="つかう",feed="html_watch"),
 "kit":dict(label="実験キット・教材",act="つかう",feed="html_watch"),
 "instrument":dict(label="観察器具・機材",act="つかう",feed="html_watch"),
 "museum":dict(label="科学館・博物館",act="いく",feed="html_watch"),
 "facility":dict(label="研究施設・工場",act="いく",feed="html_watch"),
 "fieldsite":dict(label="フィールド・自然地",act="いく",feed="html_watch"),
 "event":dict(label="イベント・企画",act="やってみる",feed="ical_or_html"),
 "workshop":dict(label="ワークショップ・教室",act="やってみる",feed="html_watch"),
 "show":dict(label="サイエンスショー",act="やってみる",feed="html_watch"),
 "person":dict(label="講師・研究者",act="よぶ・あう",feed="html_watch"),
 "outreach":dict(label="出張授業・出前講座",act="よぶ・あう",feed="html_watch"),
 "program":dict(label="講座・養成課程",act="やってみる",feed="html_watch"),
 "community":dict(label="学会・市民科学・団体",act="やってみる",feed="rss_autodiscover"),
}
PROVIDER_TYPES = ["大学・研究機関","企業・メーカー","科学館・博物館","自治体・公的機関","NPO・市民団体",
 "学会・専門団体","クリエイター・YouTuber","個人コミュニケーター","研究者・専門家","出版社","放送局","学校・教育機関"]
FIELDS = ["宇宙・天文","生きもの・生命科学","医療・健康・人体","地球・自然・防災",
 "物理・化学・材料","工学・ものづくり","情報・数理・AI","環境・気候・エネルギー"]
AUDIENCES = ["未就学児","小学生","中学生","高校生","大学生・院生","社会人","シニア","全年齢"]
PURPOSES  = ["授業で使う","家庭で楽しむ","探究・自由研究","職能開発","地域活動","啓発・広報","進路・キャリア"]
TXNS      = ["無料","フリーミアム","購入（買い切り）","サブスク","予約（日時指定）","要見積もり"]

FORMAT_TO_ACT = {"教材セット":"つかう","実験キット":"つかう","観察器具":"つかう","模型・立体教具":"つかう",
 "防災グッズ":"つかう","ボードゲーム・カード":"つかう","書籍・図鑑":"よむ","電子書籍":"よむ",
 "動画・オンライン講座":"みる・きく","アプリ":"みる・きく","VR/AR":"みる・きく",
 "ワークショップ":"やってみる","フィールドワーク":"やってみる","サイエンスショー":"やってみる",
 "出張授業":"よぶ・あう","講演・トークイベント":"よぶ・あう","展示・施設イベント":"いく"}

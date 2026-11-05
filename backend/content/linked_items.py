from urllib.parse import quote


def balad(place_id):
    return f"https://balad.ir/p/{place_id}"


def google_map(name, city):
    return f"https://www.google.com/maps/search/?api=1&query={quote(name + ' ' + city)}"


def apple_podcast(podcast_id):
    return f"https://podcasts.apple.com/podcast/id{podcast_id}"


def taaghche_search(title):
    return f"https://taaghche.com/search?term={quote(title)}"


def imdb_link(title, year, imdb_id=""):
    if imdb_id:
        return f"https://www.imdb.com/title/{imdb_id}/"
    return f"https://www.imdb.com/find/?q={quote(f'{title} {year}')}"


CAFE = {"social": 3, "comfort": 2}
BOOK_CAFE = {"solo": 2, "thoughtful": 2, "comfort": 2}
OLD_CAFE = {"social": 2, "nostalgic": 3, "comfort": 2}
ART_CAFE = {"social": 2, "art": 3, "comfort": 2}
GAME_CAFE = {"social": 3, "funny": 2}
WALK = {"outdoor": 3, "calm": 2, "body": 1}
HISTORY_PLACE = {"outdoor": 2, "nostalgic": 3, "history": 2}
MOUNTAIN = {"outdoor": 3, "body": 3, "adventure": 2}

PODCASTS = [
    ("چنل‌بی", "روایت رویدادهای واقعی", 1070642732, {"escape": 3, "learning": 2, "long": 1}),
    ("بی‌پلاس", "خلاصه‌ی کتاب", 1378125252, {"learning": 3, "short": 2, "motivational": 2}),
    ("رادیو مرز", "مستند روایی", 1412116121, {"reflective": 3, "emotional": 2, "escape": 2}),
    ("رادیو کارنکن", "کسب‌وکار", 1439014988, {"learning": 3, "motivational": 2, "focus": 2}),
    ("رادیو راه", "با مجتبی شکوری", 1496988806, {"learning": 3, "reflective": 2}),
    ("سفری در تاریخ", "تاریخ", 1443354601, {"history": 3, "learning": 2, "long": 1}),
    ("پادکست کافئین", "روایت‌های تاریخی", 1895456459, {"history": 3, "escape": 2}),
    ("همسفر", "سفر و رشد فردی", 1697671815, {"adventure": 2, "reflective": 2, "hopeful": 2}),
    ("رادیو جولون", "سفر", 1385380982, {"adventure": 3, "escape": 2}),
    ("فیکشن", "داستان", 1471783534, {"escape": 3, "emotional": 2}),
    ("اندرون", "رشد فردی", 1750979152, {"mindful": 2, "reflective": 3}),
    ("سبکتو", "تکنولوژی و کتاب", 1447879286, {"learning": 3, "science": 2}),
]

ARTICLES = [
    (
        "۱۰ دلیل که خواب کافی مهم‌تر از چیزی است که فکر می‌کنید",
        "دیجی‌کالا مگ",
        "https://www.digikala.com/mag/10-reasons-why-good-sleep-is-important/",
        {"learning": 2, "short": 2, "calm": 1},
    ),
    (
        "تکنیک پومودورو چیست و چگونه با آن زمان خود را مدیریت کنیم؟",
        "زومیت",
        "https://www.zoomit.ir/howto/223461-education-pomodoro-time-management-technique/",
        {"focus": 3, "short": 3, "learning": 2},
    ),
    (
        "همه چیز درباره‌ی تکنیک مدیریت زمان پومودورو",
        "دیجی‌کالا مگ",
        "https://www.digikala.com/mag/pomodoro-technique/",
        {"focus": 3, "learning": 2},
    ),
    (
        "فرسودگی شغلی چیست؟",
        "فرادرس",
        "https://blog.faradars.org/فرسودگی-شغلی-چیست/",
        {"mindful": 2, "learning": 2, "calm": 1},
    ),
    (
        "فرسودگی شغلی چیست و چه تأثیری بر فرد و کسب‌وکارها دارد؟",
        "درمانکده",
        "https://www.darmankade.com/blog/burnout/",
        {"mindful": 2, "learning": 2},
    ),
    (
        "خستگی عاطفی چیست و چگونه درمان می‌شود؟",
        "دیجی‌کالا مگ",
        "https://www.digikala.com/mag/emotional-exhaustion/",
        {"mindful": 3, "calm": 2, "short": 1},
    ),
    (
        "How to Stop Procrastinating by Using the 2-Minute Rule",
        "جیمز کلیر، به انگلیسی",
        "https://jamesclear.com/how-to-stop-procrastinating",
        {"motivational": 3, "short": 3},
    ),
]

TEHRAN_CAFES = [
    ("کافه نادری", "خیابان جمهوری", "ضلع شرقی پل حافظ، نرسیده به چهارراه استانبول، پلاک ۵۲۴", "1reZtus64yaKS3", OLD_CAFE),
    ("کافه هنر", "خیابان انقلاب", "بین قدس و وصال شیرازی، جنب سینما سپیده، کوچه اسکو، پلاک ۸", "1c3CjobjeHqtj9", ART_CAFE),
    ("کافه رستوران چای‌بار", "اندرزگو", "اندرزگو، سلیمی شمالی، پلاک ۱۴۵", "1JdqFsetIVSbwe", CAFE),
    ("کافه گل رضاییه", "خیابان سی تیر", "خیابان جمهوری، خیابان سی تیر، بالاتر از موزه آبگینه، پلاک ۱۷۲", "4hqojJXeWcysq5", OLD_CAFE),
    ("کافه کتاب دارالخلافه", "خیابان امام خمینی", "خیابان شیخ هادی، کوچه مظفری‌خواه، پلاک ۱۷", "2Mt4l9lu7AFORB", BOOK_CAFE),
    ("وی‌کافه", "خیابان فلسطین", "خیابان انقلاب، خیابان فلسطین، نبش کوچه نایبی", "1STM7Djj5AdvRu", CAFE),
    ("کافه روحی", "بهارستان", "خیابان دانش‌سرا، خیابان شریعت‌مدار رفیع، باغ موزه نگارستان", "40xQEIL0jsy30U", ART_CAFE),
    ("کافه تهرون کندوان", "خیابان انقلاب", "روبه‌روی خیابان استاد نجات‌اللهی، کوچه کندوان، نبش مهرانی، پلاک ۱۹", "2RGXYeaoZBG7B8", CAFE),
    ("سام کافه", "خیابان فرشته", "مجتمع تجاری سام سنتر، طبقه اول", "4RXd8ExwteNKe0", CAFE),
    ("کافه لمیز", "پاسداران", "خیابان پایدارفرد، مقابل بوستان سوم، پلاک ۵", "4gAzSl6HO6U1Ap", CAFE),
    ("کافه نزدیک کتاب", "کریمخان", "بین ایرانشهر و ماهشهر، شماره ۱۳۴، طبقه اول", "5prsoqW9QaMKBy", BOOK_CAFE),
    ("کافه روبرتو", "پاسداران", "بوستان دوم، پلاک ۴", "4ctFksRaCpebRg", CAFE),
    ("کافه تایپ", "کریمخان", "خیابان ایرانشهر شمالی، نبش خیابان کلانتری", "44brcjs59QyvfS", BOOK_CAFE),
    ("کافه امجدیه", "خیابان مفتح جنوبی", "خیابان ورزنده، نبش کوچه سلماسی", "5qCtOjEJpIs7XC", OLD_CAFE),
    ("کافه کتاب نیکو", "خیابان ایرانشهر", "بن‌بست نیکوشهر", "634v2Lzdk2Za6c", BOOK_CAFE),
    ("کافه کاریز", "خیابان شریعتی", "خیابان دولت، نبش نعمتی، باغ خانه شاعران ایران", "PEl1Cjpu9DUX8n", ART_CAFE),
    ("کافه گالری هاگ", "نیاوران", "خیابان امیدوار، کوچه پانزدهم", "4hqBGRUVXXY27C", ART_CAFE),
    ("کافه لوشانه", "تجریش", "میدان تجریش، بازار قائم، طبقه ۵", "6Z4nYeEqpHHupj", CAFE),
    ("کافه رستوران کاما", "خیابان بهشتی", "تقاطع خیابان سهروردی، پلاک ۱۳۶", "1GUeKZrrwHA2ei", CAFE),
]

ISFAHAN_CAFES = [
    ("کافه مس و قالی", "میدان نقش جهان", "ورودی میدان نقش جهان، خیابان سپه، تیمچه مثقالی", "2080TNeUr2DG4S", OLD_CAFE),
    ("چایخانه آزادگان", "میدان نقش جهان", "بازار لواف‌ها، کوچه چاه حج میرزا", "5ZcZm2QmZIShY7", OLD_CAFE),
    ("شربت‌سرای روزگار", "میدان نقش جهان", "میدان نقش جهان، سرای اسپادانا", "5A4CJW7fmVdyJW", OLD_CAFE),
    ("کافه لوانت", "جلفا", "خیابان نظر میانی، مقابل میدان جلفا، مجتمع اپیک سنتر", "2KtK7j0NQHfwG5", CAFE),
    ("شربت‌خانه بهارنارنج", "جلفا", "خیابان حکیم نظامی، کوچه کلیسای وانک، روبه‌روی هتل جلفا", "2iiGqtsKaWi3ij", CAFE),
    ("کافه لاندا", "خیابان نظر غربی", "بلوار بوستان سعدی، خیابان مارنان، خیابان نظر غربی، جنب بانک صادرات", "6ZbO8QXeTqFtV7", CAFE),
    ("کافه رگ راگ", "خیابان فردوسی", "تقاطع خیابان فردوسی و فلسطین", "PbDcxmHdWn0q2e", CAFE),
    ("کافه بازی اصفهان", "خیابان آمادگاه", "روبه‌روی هتل عباسی، ضلع شرقی مجتمع عباسی، طبقه بالا", "6l4pxeQB8iZVKY", GAME_CAFE),
]

TEHRAN_PLACES = [
    ("پل طبیعت", "عباس‌آباد", "پل پیاده‌روی سه‌طبقه بین پارک طالقانی و پارک آب و آتش.", WALK),
    ("پارک آب و آتش", "عباس‌آباد", "پارکی که از پل طبیعت هم می‌شه بهش رسید.", WALK),
    ("برج میلاد", "گیشا", "برج ۴۳۵ متری با تراس و چشم‌انداز ۳۶۰ درجه از تهران.", {"outdoor": 2, "adventure": 2, "social": 2}),
    ("دربند", "شمیران", "محله‌ی کوهستانی و یکی از نقطه‌های شروع کوهنوردی.", MOUNTAIN),
    ("بام تهران", "ولنجک", "منطقه‌ی کوهستانی شمال تهران.", MOUNTAIN),
]

ISFAHAN_PLACES = [
    ("میدان نقش جهان", "مرکز شهر", "میراث جهانی یونسکو، با بازار اصفهان در کنارش.", HISTORY_PLACE),
    ("سی‌وسه‌پل", "زاینده‌رود", "پل صفوی ۳۳ دهانه روی زاینده‌رود، با ورود رایگان.", HISTORY_PLACE),
    ("پل خواجو", "زاینده‌رود", "پل صفوی روی زاینده‌رود و پاتوق غروب.", HISTORY_PLACE),
    ("چهل‌ستون", "مرکز شهر", "کاخ صفوی با باغ و نقاشی‌های دیواری.", {"art": 3, "nostalgic": 2, "calm": 2}),
    ("کلیسای وانک", "جلفا", "کلیسای جامع ارامنه در محله‌ی جلفا، همراه با موزه.", {"art": 3, "history": 2, "calm": 2}),
    ("خیابان چهارباغ عباسی", "مرکز شهر", "خیابان تاریخی برای پیاده‌روی.", WALK),
]


def build_linked_items():
    items = [
        ("podcast", title, subtitle, "", tags, None, None, apple_podcast(podcast_id))
        for title, subtitle, podcast_id, tags in PODCASTS
    ]
    items += [
        ("article", title, source, "", tags, None, None, url)
        for title, source, url, tags in ARTICLES
    ]
    items += [
        ("cafe", title, area, address, tags, "tehran", None, balad(place_id))
        for title, area, address, place_id, tags in TEHRAN_CAFES
    ]
    items += [
        ("cafe", title, area, address, tags, "isfahan", None, balad(place_id))
        for title, area, address, place_id, tags in ISFAHAN_CAFES
    ]
    items += [
        ("cafe", title, area, description, tags, "tehran", None, google_map(title, "تهران"))
        for title, area, description, tags in TEHRAN_PLACES
    ]
    items += [
        ("cafe", title, area, description, tags, "isfahan", None, google_map(title, "اصفهان"))
        for title, area, description, tags in ISFAHAN_PLACES
    ]
    items.append(
        ("game", "شطرنج آنلاین", "", "", {"focus": 3, "thoughtful": 3}, None, 20, "https://lichess.org")
    )
    return items

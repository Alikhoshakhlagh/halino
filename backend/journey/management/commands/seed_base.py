"""
دیتای پایه حالینو: شهرها، تگ‌ها، دسته‌ها، مودها، سؤال‌ها، مناسبت‌ها و آیتم‌های غیرفیلم.

    python manage.py seed_base

قابل اجرای چندباره است (idempotent). فیلم و سریال با دستور import_titles وارد می‌شوند.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import City
from content.models import Category, Item, ItemTag, Occasion, Tag
from content.national_days import NATIONAL_DAYS
from content.taxonomy import TAGS
from journey.models import DAILY_BOX_SPAN, Mood, MoodTag, OptionTag, Question, QuestionOption

CITIES = [
    ("تهران", "tehran", True),
    ("اصفهان", "isfahan", True),
    ("مشهد", "mashhad", False),
    ("شیراز", "shiraz", False),
    ("تبریز", "tabriz", False),
    ("کرج", "karaj", False),
]

# slug, نام, آیکون, رنگ, ترتیب, دنباله‌دار, وابسته به شهر
CATEGORIES = [
    ("book", "کتاب", "", "#FF8A5B", 3, True, False),
    ("podcast", "پادکست", "", "#F472B6", 4, False, False),
    ("article", "مقاله", "", "#34D399", 5, False, False),
    ("cafe", "کافه و مکان", "", "#FFC93C", 6, False, True),
    ("sport", "ورزش", "", "#FF6B6B", 7, False, False),
    ("meditation", "مدیتیشن", "", "#A78BFA", 8, False, False),
    ("writing", "نوشتن", "", "#14B8A6", 9, False, False),
    ("game", "بازی", "", "#A3E635", 10, False, False),
]

# نام, چهره, ایموجی, رنگ, انرژی, خوشایندی, {تگ: وزن}
#
# تصمیم محصولی مهم — «مود غمگین یعنی محتوای شاد بدهیم یا هم‌حال؟»
# انتخاب: هم‌حال نه، ولی شادِ تصنعی هم نه. برای مودهای منفی، تگ‌های
# «امیدوارکننده» و «دلگرم‌کننده» بالا می‌روند و «تلخ» با وزن منفی سرکوب می‌شود.
MOODS = [
    ("سرحال", "happy", "", "#FFC93C", 2, 2, {"energizing": 3, "social": 2, "adventure": 2, "outdoor": 2}),
    ("آرام", "calm", "", "#4ADE80", -1, 2, {"calm": 3, "mindful": 2, "reflective": 2, "comfort": 2}),
    ("متمرکز", "focused", "", "#4CC9F0", 1, 1, {"focus": 3, "learning": 3, "science": 2, "thoughtful": 2}),
    ("خسته", "tired", "", "#A78BFA", -2, 0, {"light": 3, "short": 3, "comfort": 2, "calm": 2, "heavy": -3, "long": -2}),
    ("بی‌حوصله", "bored", "", "#94A3B8", -1, -1, {"funny": 3, "light": 2, "escape": 3, "thrilling": 2, "heavy": -2}),
    ("دلتنگ", "longing", "", "#F472B6", -1, -1, {"nostalgic": 3, "romantic": 2, "emotional": 2, "comfort": 2}),
    ("مضطرب", "anxious", "", "#FB923C", 1, -2, {"mindful": 3, "calm": 3, "body": 2, "hopeful": 2, "thrilling": -3, "dark": -3}),
    ("غمگین", "sad", "", "#60A5FA", -2, -2, {"hopeful": 3, "comfort": 3, "uplifting": 2, "emotional": 2, "dark": -3}),
    ("عصبانی", "angry", "", "#FF6B6B", 2, -2, {"body": 3, "outdoor": 3, "energizing": 2, "social": -2, "dark": -1}),
]

# (متن سؤال, حالت, [(متن گزینه, {تگ: وزن}), ...], «مورد دیگه» دارد؟)
#
# سؤال‌هایی که گزینه‌هایشان سلیقه‌ای است (فعالیت، حال‌وهوا، ژانر…) چیپ «مورد دیگه…»
# می‌گیرند؛ پاسخ آزاد فقط ذخیره می‌شود و وزنی به پروفایل نمی‌دهد.
ONBOARDING = [
    ("وقت آزادت رو بیشتر چطور می‌گذرونی؟", "multi", [
        ("فیلم و سریال", {"escape": 3, "emotional": 1}),
        ("کتاب خوندن", {"thoughtful": 3, "learning": 2, "solo": 1}),
        ("پادکست و رادیو", {"learning": 2, "light": 2}),
        ("ورزش و پیاده‌روی", {"body": 3, "outdoor": 2, "energizing": 2}),
        ("بیرون رفتن با دوستا", {"social": 3, "outdoor": 2}),
        ("تنها بودن و فکر کردن", {"solo": 3, "reflective": 3}),
    ], True),
    ("وقتی حالت خوب نیست، چی بیشتر بهت کمک می‌کنه؟", "single", [
        ("یه فیلم یا موسیقی خوب", {"escape": 3, "comfort": 2}),
        ("حرف زدن با یه نفر", {"social": 3, "comfort": 2}),
        ("تنها بودن و ساکت موندن", {"solo": 3, "calm": 3, "mindful": 2}),
        ("راه رفتن و ورزش", {"body": 3, "outdoor": 3}),
    ], True),
    ("این روزها بیشتر دنبال چی هستی؟", "single", [
        ("آرامش", {"calm": 3, "mindful": 3}),
        ("انرژی و انگیزه", {"energizing": 3, "motivational": 3}),
        ("یاد گرفتن چیزهای تازه", {"learning": 3, "science": 2}),
        ("فقط سرگرمی", {"funny": 3, "light": 3, "escape": 2}),
    ], True),
    ("معمولاً چقدر وقت آزاد داری؟", "single", [
        ("کمتر از نیم‌ساعت", {"short": 3, "light": 2, "long": -2}),
        ("حدود یک ساعت", {"short": 1}),
        ("چند ساعت", {"long": 3}),
    ], False),
    ("بیشتر با کدوم حال‌وهوا حال می‌کنی؟", "multi", [
        ("خنده‌دار", {"funny": 3, "light": 2}),
        ("هیجانی", {"thrilling": 3, "adventure": 2}),
        ("عاشقانه", {"romantic": 3, "emotional": 2}),
        ("تلخ و عمیق", {"dark": 3, "heavy": 2, "thoughtful": 2}),
        ("فانتزی و خیالی", {"fantasy": 3, "escape": 2}),
        ("واقعی و مستند", {"documentary": 3, "science": 2, "history": 2}),
    ], True),
    ("کارها رو ترجیح می‌دی تنها انجام بدی یا با بقیه؟", "single", [
        ("تنها", {"solo": 3, "indoor": 1}),
        ("با بقیه", {"social": 3, "outdoor": 1}),
        ("فرقی نداره", {}),
    ], False),
]

# سؤال‌های روزانه — دو جعبه (DAILY_BOX_TITLES)، هر جعبه چند سؤال کوتاه که موتور
# مستقیماً می‌خورد: انرژی/خواسته → مود امروز؛ وقت/همراه/خونه‌یابیرون → شرایط امروز.
# order = شماره‌ی جعبه × DAILY_BOX_SPAN + ردیف. (متن، حالت، گزینه‌ها، «مورد دیگه»)
DAILY_BOXES = [
    [  # جعبه‌ی ۱: حال امروزت
        ("امروز چقدر انرژی داری؟", "single", [
            ("کم", {"short": 3, "light": 3, "calm": 2, "long": -2}),
            ("متوسط", {}),
            ("زیاد", {"energizing": 3, "body": 2, "outdoor": 2}),
        ], False),
        ("الان بیشتر دلت چی می‌خواد؟", "single", [
            ("آرامش", {"calm": 3, "mindful": 3}),
            ("سرگرمی", {"funny": 3, "escape": 3}),
            ("یه کار مفید", {"learning": 3, "focus": 3}),
            ("حرکت و بیرون رفتن", {"body": 3, "outdoor": 3}),
        ], False),
    ],
    [  # جعبه‌ی ۲: شرایط امروزت
        ("چقدر وقت داری؟", "single", [
            ("یه ربع", {"short": 3, "long": -3}),
            ("یکی دو ساعت", {}),
            ("امروز آزادم", {"long": 3}),
        ], False),
        ("با کی هستی؟", "single", [
            ("تنها", {"solo": 3, "indoor": 1}),
            ("با یه نفر نزدیک", {"romantic": 2, "comfort": 2, "social": 1}),
            ("با جمع دوستا", {"social": 3, "funny": 1, "outdoor": 1}),
        ], False),
        ("خونه‌ای یا بیرون؟", "single", [
            ("خونه می‌مونم", {"indoor": 3, "outdoor": -2}),
            ("بیرون می‌رم", {"outdoor": 3, "social": 1}),
            ("فرقی نداره", {}),
        ], False),
    ],
]
DAILY = [
    (box_index * DAILY_BOX_SPAN + row, *question)
    for box_index, box in enumerate(DAILY_BOXES)
    for row, question in enumerate(box)
]

# سؤال‌های پروفایل — فقط در صفحه‌ی پروفایل («بهتر بشناسیمت»)، هر وقت کاربر خواست.
# پاسخ‌ها با وزن نصف به حافظه‌ی تگ کاربر اضافه می‌شوند (engine.learn_from_answers).
PROFILE = [
    ("معمولاً کِی وقت آزاد داری؟", "single", [
        ("صبح زود", {"energizing": 2, "body": 2}),
        ("وسط روز", {"short": 2, "light": 2}),
        ("عصر", {"social": 2, "outdoor": 2}),
        ("آخر شب", {"calm": 2, "indoor": 2, "reflective": 1}),
    ], False),
    ("برای بیرون رفتن چقدر خرج می‌کنی؟", "single", [
        ("تقریباً هیچی", {"indoor": 2, "solo": 1, "outdoor": -1}),
        ("کم", {"outdoor": 1, "short": 1}),
        ("معمولی", {"social": 2, "outdoor": 2}),
        ("خرج می‌کنم", {"social": 3, "outdoor": 3, "adventure": 1}),
    ], False),
    ("تفریح ایده‌آلت با کیه؟", "single", [
        ("تنها", {"solo": 3, "reflective": 1}),
        ("با یه نفر نزدیک", {"romantic": 2, "comfort": 2}),
        ("با جمع دوستا", {"social": 3, "funny": 1}),
        ("با خانواده", {"family": 3, "comfort": 1}),
    ], True),
    ("کدوم رسانه رو بیشتر ترجیح می‌دی؟", "multi", [
        ("تصویری (فیلم و سریال)", {"escape": 2, "long": 1}),
        ("متن (کتاب و مقاله)", {"thoughtful": 2, "learning": 2}),
        ("صوتی (پادکست)", {"learning": 2, "light": 2}),
        ("تعاملی (بازی)", {"focus": 2, "light": 2}),
    ], True),
    ("چه موضوع‌هایی بیشتر کنجکاوت می‌کنن؟", "multi", [
        ("علم و فناوری", {"science": 3, "learning": 1}),
        ("تاریخ", {"history": 3}),
        ("هنر و موسیقی", {"art": 3, "creative": 1}),
        ("روان‌شناسی", {"reflective": 3, "mindful": 2}),
        ("طبیعت", {"outdoor": 2, "documentary": 2}),
    ], True),
    ("بعد از یه روز سخت چی بیشتر بهت می‌چسبه؟", "single", [
        ("یه چیز خنده‌دار", {"funny": 3, "light": 2}),
        ("یه کار آروم و ساکت", {"calm": 3, "mindful": 2}),
        ("حرکت و ورزش", {"body": 3, "energizing": 2}),
        ("حرف زدن با یه دوست", {"social": 3, "comfort": 2}),
    ], True),
]

# منبع, تقویم, ماه, روز, عنوان, نقل‌قول, گوینده, [تگ‌ها], اولویت
#
# «پیشنهاد روز» از همین جدول تغذیه می‌شود. سه منبع:
#   iran     -> تقویم شمسی
#   national -> روزهای جهانی به سبک nationaldaycalendar.com (تقویم میلادی) — content/national_days.py
#   admin    -> دستور مدیر؛ اینجا seed نمی‌شود و از پنل ادمین ساخته می‌شود
# مدیر می‌تواند روی هر مناسبت، آیتم‌های مشخصی را «قفل» کند تا حتماً پیشنهاد شوند.
IRAN, NATIONAL = "iran", "national"
JALALI, GREGORIAN = "jalali", "gregorian"

OCCASIONS = [
    # --- تقویم ایرانی (شمسی) ---
    (IRAN, JALALI, 1, 1, "نوروز", "هر روز نو، فرصتی تازه برای شروع دوباره است.", "", ["hopeful", "family", "social"], 5),
    (IRAN, JALALI, 1, 13, "سیزده‌بدر — روز طبیعت", "بهترین درمان یک ذهن خسته، یک ساعت پیاده‌روی است.", "", ["outdoor", "body", "social"], 5),
    (IRAN, JALALI, 2, 1, "روز بزرگداشت سعدی", "بنی‌آدم اعضای یک پیکرند / که در آفرینش ز یک گوهرند", "سعدی", ["art", "thoughtful"], 3),
    (IRAN, JALALI, 2, 25, "روز بزرگداشت فردوسی", "بسی رنج بردم در این سال سی / عجم زنده کردم بدین پارسی", "فردوسی", ["history", "art"], 3),
    (IRAN, JALALI, 6, 21, "روز ملی سینما", "سینما یعنی بیست‌وچهار بار حقیقت در ثانیه.", "ژان‌لوک گدار", ["escape", "art"], 4),
    (IRAN, JALALI, 6, 27, "روز شعر و ادب فارسی", "", "", ["art", "reflective"], 3),
    (IRAN, JALALI, 7, 8, "روز بزرگداشت مولوی", "بنشین بر لب جوی و گذر عمر ببین", "مولوی", ["reflective", "art"], 3),
    (IRAN, JALALI, 7, 20, "روز بزرگداشت حافظ", "بشنو این نی چون شکایت می‌کند / از جدایی‌ها حکایت می‌کند", "حافظ", ["art", "nostalgic"], 3),
    (IRAN, JALALI, 9, 16, "روز دانشجو", "", "", ["learning", "social"], 3),
    (IRAN, JALALI, 9, 30, "شب یلدا", "بلندترین شب سال، بهانه‌ای برای کنار هم بودن.", "", ["family", "nostalgic", "comfort", "social"], 6),
]

# روزهای جهانی: یک مناسبت برای هر روزِ سال، از content/national_days.py
OCCASIONS += [
    (NATIONAL, GREGORIAN, month, day, title, quote, author, tags, priority)
    for month, day, title, quote, author, tags, priority in NATIONAL_DAYS
]

# دسته, عنوان, زیرعنوان, توضیح, {تگ: وزن}, شهر, مدت
ITEMS = [
    # --- کتاب (دنباله‌دار: تا تمام نشده، کتاب جدید پیشنهاد نمی‌شود) ---
    ("book", "ملت عشق", "الیف شافاک", "", {"emotional": 3, "romantic": 2, "hopeful": 2}, None, None),
    ("book", "بیشعوری", "خاویر کرمنت", "", {"funny": 3, "light": 2}, None, None),
    ("book", "کافه‌ای در انتهای دنیا", "جان استرلکی", "", {"reflective": 3, "hopeful": 3, "short": 2}, None, None),
    ("book", "مغز آندرو", "ای. ال. دکتروف", "", {"thoughtful": 3, "science": 2}, None, None),
    ("book", "قدرت عادت", "چارلز داهیگ", "", {"learning": 3, "motivational": 3}, None, None),
    ("book", "انسان در جستجوی معنا", "ویکتور فرانکل", "", {"hopeful": 3, "reflective": 3, "heavy": 2}, None, None),
    ("book", "چهار میثاق", "دون میگوئل روئیز", "", {"mindful": 3, "calm": 2, "short": 2}, None, None),
    ("book", "کیمیاگر", "پائولو کوئلیو", "", {"adventure": 2, "hopeful": 3, "short": 2}, None, None),
    ("book", "سووشون", "سیمین دانشور", "", {"history": 3, "emotional": 2}, None, None),
    ("book", "بوف کور", "صادق هدایت", "", {"dark": 3, "heavy": 3, "thoughtful": 3}, None, None),
    ("book", "هنر ظریف بی‌خیالی", "مارک منسون", "", {"funny": 2, "motivational": 3, "light": 2}, None, None),
    ("book", "اثر مرکب", "دارن هاردی", "", {"motivational": 3, "learning": 2}, None, None),
    ("book", "شدن", "میشل اوباما", "", {"motivational": 3, "history": 2, "emotional": 2}, None, None),
    ("book", "سپیده‌دم یک زن", "کالین مک‌کالو", "", {"romantic": 3, "emotional": 3}, None, None),
    ("book", "زندگی در پیش رو", "رومن گاری", "", {"emotional": 3, "hopeful": 2, "short": 2}, None, None),

    # --- پادکست ---
    ("podcast", "چنل‌بی", "روایت و داستان", "", {"light": 3, "escape": 2, "short": 2}, None, 40),
    ("podcast", "رادیو مرز", "علمی و تحلیلی", "", {"learning": 3, "science": 3}, None, 45),
    ("podcast", "بی‌پلاس", "خلاصه کتاب", "", {"learning": 3, "short": 2, "motivational": 2}, None, 30),
    ("podcast", "دگرگون", "روان‌شناسی", "", {"reflective": 3, "mindful": 2, "learning": 2}, None, 35),
    ("podcast", "رادیو کارنکن", "کار و کسب‌وکار", "", {"learning": 3, "motivational": 2, "focus": 2}, None, 40),
    ("podcast", "پادکست تاریخ", "روایت تاریخی", "", {"history": 3, "learning": 2, "long": 2}, None, 60),

    # --- مقاله ---
    ("article", "چرا خواب کافی مهم‌ترین کار امروز توست", "", "", {"learning": 2, "short": 3, "mindful": 2}, None, 8),
    ("article", "تکنیک پومودورو در ۵ دقیقه", "", "", {"focus": 3, "short": 3, "learning": 2}, None, 5),
    ("article", "چطور از فرسودگی ذهنی بیرون بیاییم", "", "", {"mindful": 3, "calm": 2, "short": 2}, None, 10),
    ("article", "قانون دو دقیقه برای شروع کارها", "", "", {"motivational": 3, "short": 3}, None, 6),

    # --- کافه و مکان (وابسته به شهر) ---
    ("cafe", "کافه‌ای دنج در ولیعصر", "تهران", "", {"social": 3, "comfort": 2, "outdoor": 1}, "tehran", 90),
    ("cafe", "پارک آب و آتش", "تهران", "", {"outdoor": 3, "social": 2, "body": 2}, "tehran", 120),
    ("cafe", "کتاب‌فروشی و کافه در انقلاب", "تهران", "", {"solo": 2, "thoughtful": 2, "comfort": 2}, "tehran", 90),
    ("cafe", "بام تهران", "تهران", "", {"outdoor": 3, "body": 3, "adventure": 2}, "tehran", 180),
    ("cafe", "قدم زدن روی سی‌وسه پل", "اصفهان", "", {"outdoor": 3, "nostalgic": 2, "calm": 2}, "isfahan", 90),
    ("cafe", "کافه‌ای در نقش جهان", "اصفهان", "", {"social": 3, "art": 2, "comfort": 2}, "isfahan", 90),
    ("cafe", "پیاده‌روی در چهارباغ", "اصفهان", "", {"outdoor": 3, "body": 2, "social": 1}, "isfahan", 60),
    ("cafe", "رستوران سنتی در بازار تهران", "تهران", "ناهار یا شام با حال‌وهوای قدیمی.", {"social": 3, "nostalgic": 2, "comfort": 2}, "tehran", 120),
    ("cafe", "شام با دوستا در جردن", "تهران", "", {"social": 3, "energizing": 2, "funny": 1}, "tehran", 150),
    ("cafe", "کافه‌ی بام‌دار در دربند", "تهران", "چای و منظره، بعدش یه پیاده‌روی کوتاه.", {"outdoor": 3, "social": 2, "calm": 2}, "tehran", 120),
    ("cafe", "رستوران کنار زاینده‌رود", "اصفهان", "", {"social": 3, "calm": 2, "outdoor": 2}, "isfahan", 120),
    ("cafe", "عصرانه در جلفا", "اصفهان", "کافه‌های محله‌ی ارامنه.", {"social": 3, "art": 2, "comfort": 2}, "isfahan", 90),

    # --- ورزش ---
    ("sport", "پیاده‌روی ۲۰ دقیقه‌ای", "", "بدون هدف، فقط راه رفتن.", {"body": 3, "outdoor": 3, "short": 3, "calm": 2}, None, 20),
    ("sport", "کشش صبحگاهی", "", "پنج حرکت ساده بعد از بیدار شدن.", {"body": 3, "short": 3, "energizing": 2}, None, 10),
    ("sport", "دویدن سبک", "", "", {"body": 3, "outdoor": 3, "energizing": 3}, None, 30),
    ("sport", "تمرین با وزن بدن در خانه", "", "", {"body": 3, "indoor": 2, "energizing": 2}, None, 25),
    ("sport", "یوگای شب", "", "", {"body": 2, "calm": 3, "mindful": 3}, None, 20),
    ("sport", "دوچرخه‌سواری", "", "", {"body": 3, "outdoor": 3, "adventure": 2}, None, 45),
    ("sport", "پیاده‌روی گروهی با دوستا", "", "یه مسیر ساده، چند نفر، بدون عجله.", {"social": 3, "outdoor": 3, "body": 2}, None, 60),

    # --- مدیتیشن ---
    ("meditation", "تنفس ۴-۷-۸", "", "چهار ثانیه دم، هفت ثانیه نگه، هشت ثانیه بازدم.", {"mindful": 3, "calm": 3, "short": 3}, None, 5),
    ("meditation", "اسکن بدن", "", "", {"mindful": 3, "calm": 3, "reflective": 2}, None, 15),
    ("meditation", "مدیتیشن صوتی ۱۰ دقیقه‌ای", "", "", {"mindful": 3, "calm": 3, "short": 2}, None, 10),
    ("meditation", "پیاده‌روی ذهن‌آگاهانه", "", "", {"mindful": 3, "outdoor": 2, "body": 2}, None, 20),
    ("meditation", "تمرین شکرگزاری", "", "سه چیز که امروز بابتش ممنونی.", {"mindful": 2, "hopeful": 3, "short": 3}, None, 5),

    # --- نوشتن ---
    ("writing", "امروز چه چیزی حالت را عوض کرد؟", "", "", {"reflective": 3, "creative": 2, "short": 3}, None, 10),
    ("writing", "نامه‌ای به خودت پنج سال بعد", "", "", {"reflective": 3, "creative": 3, "hopeful": 2}, None, 20),
    ("writing", "سه چیزی که این هفته یاد گرفتی", "", "", {"reflective": 2, "learning": 2, "short": 3}, None, 10),
    ("writing", "چیزی که مدت‌هاست نگفته‌ای", "", "", {"reflective": 3, "emotional": 3}, None, 15),
    ("writing", "توصیف یک روز عالی از نگاه خودت", "", "", {"creative": 3, "hopeful": 3}, None, 15),

    # --- بازی ---
    ("game", "جدول یا بازی کلمات", "", "", {"focus": 2, "short": 3, "light": 2}, None, 15),
    ("game", "شطرنج آنلاین", "", "", {"focus": 3, "thoughtful": 3}, None, 20),
    ("game", "یک بازی موبایلی سبک", "", "", {"light": 3, "escape": 2, "short": 3}, None, 15),
    ("game", "بازی رومیزی با دوستان", "", "", {"social": 3, "funny": 2}, None, 60),
    ("game", "شب بازی و پیتزا", "", "دورهمی خونگی با یه بازی گروهی.", {"social": 3, "funny": 2, "indoor": 2, "comfort": 1}, None, 120),
]


class Command(BaseCommand):
    help = "ساخت دیتای پایه حالینو"

    @transaction.atomic
    def handle(self, *args, **options):
        verbosity = options.get("verbosity", 1)

        for name, slug, supported in CITIES:
            City.objects.get_or_create(
                slug=slug, defaults={"name": name, "is_supported": supported}
            )

        tags = {}
        for slug, name in TAGS.items():
            tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
            tags[slug] = tag

        categories = {}
        for slug, name, icon, color, order, is_serial, needs_city in CATEGORIES:
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "icon": icon,
                    "color": color,
                    "order": order,
                    "is_serial": is_serial,
                    "needs_city": needs_city,
                },
            )
            categories[slug] = category

        for order, (name, face, emoji, color, energy, valence, mood_tags) in enumerate(MOODS):
            mood, _ = Mood.objects.update_or_create(
                name=name,
                defaults={
                    "face": face,
                    "emoji": emoji,
                    "color": color,
                    "energy": energy,
                    "valence": valence,
                    "order": order,
                },
            )
            MoodTag.objects.filter(mood=mood).delete()
            MoodTag.objects.bulk_create(
                [
                    MoodTag(mood=mood, tag=tags[slug], weight=weight)
                    for slug, weight in mood_tags.items()
                ]
            )

        bundles = (
            (Question.ONBOARDING, ONBOARDING),
            (Question.DAILY, DAILY),
            (Question.PROFILE, PROFILE),
        )
        for scope, bundle in bundles:
            for index, row in enumerate(bundle):
                # سؤال‌های روزانه order صریح (جعبه) دارند؛ بقیه به ترتیب فهرست
                order, (text, kind, question_options, allows_other) = (
                    (row[0], row[1:]) if scope == Question.DAILY else (index, row)
                )
                question, _ = Question.objects.update_or_create(
                    scope=scope,
                    text=text,
                    defaults={
                        "kind": kind,
                        "order": order,
                        "is_active": True,
                        "allows_other": allows_other,
                    },
                )
                for option_order, (option_text, option_tags) in enumerate(question_options):
                    option, _ = QuestionOption.objects.update_or_create(
                        question=question,
                        text=option_text,
                        defaults={"order": option_order},
                    )
                    OptionTag.objects.filter(option=option).delete()
                    OptionTag.objects.bulk_create(
                        [
                            OptionTag(option=option, tag=tags[slug], weight=weight)
                            for slug, weight in option_tags.items()
                        ]
                    )

        # مناسبت‌های تکرارشونده بازسازی می‌شوند؛ دستور مدیر (source=admin یا
        # مناسبتی که سال دارد) دست‌نخورده می‌ماند.
        Occasion.objects.filter(
            source__in=[Occasion.IRAN, Occasion.NATIONAL], year__isnull=True
        ).delete()
        for source, calendar, month, day, title, quote, author, occasion_tags, priority in OCCASIONS:
            occasion = Occasion.objects.create(
                source=source,
                calendar=calendar,
                month=month,
                day=day,
                title=title,
                quote=quote,
                quote_author=author,
                priority=priority,
            )
            occasion.tags.set([tags[slug] for slug in occasion_tags])

        cities = {city.slug: city for city in City.objects.all()}
        for cat_slug, title, subtitle, description, item_tags, city_slug, duration in ITEMS:
            item, _ = Item.objects.update_or_create(
                category=categories[cat_slug],
                title=title,
                defaults={
                    "subtitle": subtitle,
                    "description": description,
                    "city": cities.get(city_slug) if city_slug else None,
                    "duration_minutes": duration,
                    "is_active": True,
                },
            )
            ItemTag.objects.filter(item=item).delete()
            ItemTag.objects.bulk_create(
                [
                    ItemTag(item=item, tag=tags[slug], weight=weight)
                    for slug, weight in item_tags.items()
                ]
            )

        if verbosity:
            self.stdout.write(
                self.style.SUCCESS(
                    f"شهر: {City.objects.count()} | تگ: {Tag.objects.count()} | "
                    f"دسته: {Category.objects.count()} | مود: {Mood.objects.count()} | "
                    f"سؤال: {Question.objects.count()} | مناسبت: {Occasion.objects.count()} | "
                    f"آیتم: {Item.objects.count()}"
                )
            )

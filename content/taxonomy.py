"""
واژگان تگ حالینو و قواعد نگاشت.

این فایل تنها جایی است که «معنی» در سیستم تعریف می‌شود. موتور پیشنهاد
هیچ دانشی از فیلم یا کتاب یا کافه ندارد؛ فقط تگ می‌شناسد.
"""

# slug -> نام فارسی
TAGS = {
    "calm": "آرام‌کننده",
    "energizing": "انرژی‌بخش",
    "uplifting": "روحیه‌بخش",
    "focus": "تمرکز",
    "social": "اجتماعی",
    "solo": "تنهایی",
    "outdoor": "بیرون از خانه",
    "indoor": "خانگی",
    "short": "کوتاه",
    "long": "طولانی",
    "creative": "خلاقانه",
    "learning": "یادگیری",
    "nostalgic": "نوستالژیک",
    "funny": "خنده‌دار",
    "emotional": "احساسی",
    "thrilling": "هیجان‌انگیز",
    "thoughtful": "فکری",
    "light": "سبک",
    "heavy": "سنگین",
    "motivational": "انگیزشی",
    "romantic": "عاشقانه",
    "dark": "تلخ",
    "hopeful": "امیدوارکننده",
    "body": "حرکت بدنی",
    "mindful": "ذهن‌آگاهی",
    "reflective": "درون‌نگر",
    "escape": "فرار از روزمرگی",
    "comfort": "دلگرم‌کننده",
    "adventure": "ماجراجویانه",
    "art": "هنری",
    "science": "علمی",
    "history": "تاریخی",
    "family": "خانوادگی",
    "animation": "انیمیشن",
    "fantasy": "فانتزی",
    "documentary": "مستند",
}

# ژانر IMDb -> تگ‌های حالینو با وزن ۱ تا ۵
GENRE_TAGS = {
    "drama": {"emotional": 3, "thoughtful": 2},
    "crime": {"thrilling": 3, "dark": 2},
    "action": {"thrilling": 3, "energizing": 2},
    "adventure": {"adventure": 3, "escape": 2},
    "comedy": {"funny": 3, "light": 3},
    "romance": {"romantic": 3, "emotional": 2},
    "thriller": {"thrilling": 3, "dark": 1},
    "scifi": {"escape": 3, "thoughtful": 2, "science": 2},
    "fantasy": {"fantasy": 3, "escape": 3},
    "animation": {"animation": 3, "light": 2, "family": 1},
    "war": {"heavy": 3, "history": 2, "emotional": 2},
    "western": {"adventure": 2, "nostalgic": 1},
    "mystery": {"thoughtful": 3, "thrilling": 2},
    "biography": {"learning": 2, "history": 2, "motivational": 2},
    "history": {"history": 3, "learning": 2},
    "horror": {"thrilling": 3, "dark": 3},
    "family": {"family": 3, "comfort": 2},
    "music": {"art": 3, "uplifting": 2},
    "sport": {"motivational": 3, "body": 1},
    "documentary": {"documentary": 3, "learning": 3, "science": 2},
}

# تگ‌هایی که صرفاً به‌خاطر نوع محتوا اضافه می‌شوند
KIND_TAGS = {
    "film": {"escape": 2, "indoor": 1, "long": 1},
    "series": {"escape": 2, "indoor": 1, "long": 3},
}

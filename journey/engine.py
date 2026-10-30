"""
موتور پیشنهاد حالینو — Rule-Based، بدون یادگیری ماشین.

ایده در یک خط: پروفایل کاربر، مود امروز و هر آیتم، همه به شکل «بردار تگ» بیان
می‌شوند؛ امتیاز هر آیتم برابر ضرب داخلی بردار آیتم در بردار کاربر است.

سه قانونی که بیرون از این فرمول اعمال می‌شوند:
  ۱. گیت شهری — دسته‌های وابسته به شهر فقط برای شهرهای پشتیبانی‌شده.
  ۲. قانون دنباله‌دار — تا کتاب/سریال فعلی تمام نشده، از آن دسته آیتم جدید نده.
  ۳. ضد تکرار — آیتمی که در N روز گذشته پیشنهاد شده دوباره نیاید.
"""

import random
from datetime import timedelta

from django.conf import settings
from django.db.models import Q

from content.models import Item, ItemTag, Occasion, Tag

from . import ml
from .jalali import to_jalali
from .models import (
    Answer,
    DailyRecommendation,
    MoodEntry,
    MoodTag,
    OptionTag,
    Question,
    UserItemStatus,
    UserTagAffinity,
)

# چقدر هر منبع در بردار نهایی لایه دوم وزن دارد
W_PROFILE_IN_MOOD_LAYER = 0.5
W_MOOD = 1.0
W_DAILY_ANSWERS = 0.75
W_MOOD_HISTORY = 0.5  # بردار مودهای ۷ روز اخیر (با decay)
MOOD_HISTORY_DAYS = 7
MOOD_HISTORY_DECAY = 0.7  # هر روز فاصله، ۰٫۷ برابر

# «پیشنهاد روز»: آیتم مناسبت — ربط به مناسبت اول، سلیقه‌ی کاربر دوم
W_OCCASION_PICK = 5.0
W_PROFILE_IN_OCCASION_PICK = 0.5

# «متناسب با حالت»: ۳ اسلات پایه (settings) + برای هر «نیاز امروز» یک اسلات تضمینی
MOOD_EXTRA_MAX = 3
SCREEN_CATEGORY_SLUGS = ("film", "series")

# «حافظه‌ی کاربر»: پاسخ‌های پروفایل و روزانه چقدر به UserTagAffinity اضافه می‌شوند
# (آنبوردینگ با وزن کامل؛ روزانه کم‌تر تا پروفایل را غرق نکند)
W_LEARN = {Question.ONBOARDING: 1.0, Question.PROFILE: 0.5, Question.DAILY: 0.25}

# تغییر وزن تگ‌ها بر اساس بازخورد کاربر
FEEDBACK_DELTA = {
    UserItemStatus.DONE: 0.8,
    UserItemStatus.IN_PROGRESS: 0.3,
    UserItemStatus.SKIPPED: -1.5,
}
RATING_BONUS = {5: 0.8, 4: 0.4, 3: 0.0, 2: -0.4, 1: -0.8}


# ---------------------------------------------------------------- پروفایل


def _answer_deltas(answers):
    """
    {tag_id: delta} برای فهرستی از Answer: وزن تگ گزینه × ضریب scope سؤال.
    پاسخ «مورد دیگه» (option خالی) فقط ذخیره می‌شود و وزنی ندارد.
    """
    # یک گزینه ممکن است چند بار (روزهای مختلف) انتخاب شده باشد؛ ضریب‌ها جمع می‌شوند
    factor_by_option = {}
    for answer in answers:
        if answer.option_id is None:
            continue
        factor = W_LEARN.get(answer.question.scope, 0.0)
        factor_by_option[answer.option_id] = factor_by_option.get(answer.option_id, 0.0) + factor
    deltas = {}
    for option_tag in OptionTag.objects.filter(option_id__in=list(factor_by_option)):
        share = option_tag.weight * factor_by_option[option_tag.option_id]
        deltas[option_tag.tag_id] = deltas.get(option_tag.tag_id, 0.0) + share
    return deltas


def learn_from_answers(user, answers):
    """
    حافظه‌ی کاربر: هر پاسخ (پروفایل یا روزانه) با وزن OptionTag.weight × ضریب scope
    به UserTagAffinity اضافه می‌شود (upsert). همان چیزی که rebuild_affinity از صفر
    می‌سازد، اینجا افزایشی انجام می‌شود.
    """
    deltas = _answer_deltas(answers)
    if not deltas:
        return {}
    existing = {
        row.tag_id: row for row in UserTagAffinity.objects.filter(user=user, tag_id__in=list(deltas))
    }
    to_create, to_update = [], []
    for tag_id, delta in deltas.items():
        row = existing.get(tag_id)
        if row is None:
            to_create.append(UserTagAffinity(user=user, tag_id=tag_id, weight=round(delta, 3)))
        else:
            row.weight = round(row.weight + delta, 3)
            to_update.append(row)
    UserTagAffinity.objects.bulk_create(to_create)
    UserTagAffinity.objects.bulk_update(to_update, ["weight"])
    return deltas


def rebuild_affinity(user):
    """
    پروفایل تگ‌محور کاربر را از صفر می‌سازد: پاسخ‌های آنبوردینگ (وزن کامل) +
    پاسخ‌های پروفایل و روزانه (حافظه‌ی کاربر، با ضریب W_LEARN) + بازخوردها.
    خروجی تست اولیه یک برچسب مبهم نیست؛ چند ردیف (تگ، وزن) است که موتور می‌خورد.
    """
    weights = _answer_deltas(
        Answer.objects.filter(user=user, option__isnull=False).select_related("question")
    )

    statuses = UserItemStatus.objects.filter(user=user).select_related("item")
    for status in statuses:
        delta = FEEDBACK_DELTA.get(status.status, 0.0)
        if status.rating:
            delta += RATING_BONUS.get(status.rating, 0.0)
        if not delta:
            continue
        for item_tag in ItemTag.objects.filter(item_id=status.item_id):
            share = delta * (item_tag.weight / 3.0)
            weights[item_tag.tag_id] = weights.get(item_tag.tag_id, 0.0) + share

    UserTagAffinity.objects.filter(user=user).delete()
    UserTagAffinity.objects.bulk_create(
        [
            UserTagAffinity(user=user, tag_id=tag_id, weight=round(value, 3))
            for tag_id, value in weights.items()
        ]
    )
    return weights


def profile_vector(user):
    return {
        row.tag_id: row.weight
        for row in UserTagAffinity.objects.filter(user=user)
    }


def mood_vector(mood):
    return {row.tag_id: float(row.weight) for row in MoodTag.objects.filter(mood=mood)}


def mood_history_vector(user, date):
    """
    بردار مودهای ۷ روز قبل از date (خود امروز جدا و با وزن کامل حساب می‌شود):
    Σ mood_vector × 0.7^روزهای_گذشته — حال‌های اخیر کاربر هم در پیشنهاد اثر دارند.
    """
    since = date - timedelta(days=MOOD_HISTORY_DAYS)
    entries = MoodEntry.objects.filter(user=user, date__gte=since, date__lt=date).select_related("mood")
    pairs = [
        (mood_vector(entry.mood), MOOD_HISTORY_DECAY ** (date - entry.date).days)
        for entry in entries
    ]
    return _combine(*pairs)


def daily_answer_vector(user, date):
    option_ids = list(
        Answer.objects.filter(
            user=user, date=date, question__scope=Question.DAILY
        ).values_list("option_id", flat=True)
    )
    vector = {}
    for option_tag in OptionTag.objects.filter(option_id__in=option_ids):
        vector[option_tag.tag_id] = vector.get(option_tag.tag_id, 0.0) + option_tag.weight
    return vector


def _combine(*pairs):
    """(بردار، ضریب) ها را در هم ادغام می‌کند."""
    out = {}
    for vector, factor in pairs:
        for tag_id, value in vector.items():
            out[tag_id] = out.get(tag_id, 0.0) + value * factor
    return out


# ---------------------------------------------------------------- کاندیدها


def blocked_serial_categories(user):
    """دسته‌هایی که کاربر در آن‌ها یک آیتم نیمه‌تمام دارد (کتاب در حال مطالعه…)."""
    return set(
        UserItemStatus.objects.filter(
            user=user, status=UserItemStatus.IN_PROGRESS, item__category__is_serial=True
        ).values_list("item__category_id", flat=True)
    )


def active_serial_items(user):
    """همان آیتم‌های نیمه‌تمام — برای بلوک «در حال مطالعه» در صفحه امروز."""
    return (
        UserItemStatus.objects.filter(user=user, status=UserItemStatus.IN_PROGRESS)
        .select_related("item", "item__category")
        .order_by("-updated_at")
    )


def candidate_items(user, date, exclude_ids=(), relax=0):
    """
    relax=0 → همه قوانین. relax=1 → قانون ضد تکرار برداشته می‌شود.
    relax=2 → آیتم‌های تمام‌شده هم برمی‌گردند. (فقط وقتی استخر خالی شد)
    """
    qs = Item.objects.filter(is_active=True).select_related("category")

    # ۱. گیت شهری
    if user.can_see_places:
        qs = qs.filter(Q(category__needs_city=False) | Q(city=user.city))
    else:
        qs = qs.filter(category__needs_city=False)

    # ۲. قانون دنباله‌دار
    blocked = blocked_serial_categories(user)
    if blocked:
        qs = qs.exclude(category_id__in=blocked)

    # آیتم‌هایی که کاربر رد کرده هرگز برنمی‌گردند
    skipped = UserItemStatus.objects.filter(
        user=user, status=UserItemStatus.SKIPPED
    ).values_list("item_id", flat=True)
    qs = qs.exclude(id__in=list(skipped))

    if relax < 2:
        done = UserItemStatus.objects.filter(
            user=user, status=UserItemStatus.DONE
        ).values_list("item_id", flat=True)
        qs = qs.exclude(id__in=list(done))

    # ۳. ضد تکرار
    if relax < 1:
        since = date - timedelta(days=settings.HALINO_REPEAT_COOLDOWN_DAYS)
        recent = DailyRecommendation.objects.filter(
            user=user, date__gte=since
        ).values_list("item_id", flat=True)
        qs = qs.exclude(id__in=list(recent))

    if exclude_ids:
        qs = qs.exclude(id__in=list(exclude_ids))
    return qs


def _score_items(items, vector, seed):
    """امتیاز = ضرب داخلی بردار آیتم در بردار کاربر، با کمی نویز برای تنوع."""
    rng = random.Random(seed)
    item_ids = [item.id for item in items]
    tag_map = {}
    for item_tag in ItemTag.objects.filter(item_id__in=item_ids):
        tag_map.setdefault(item_tag.item_id, []).append((item_tag.tag_id, item_tag.weight))

    scored = []
    for item in items:
        score = 0.0
        for tag_id, weight in tag_map.get(item.id, ()):
            score += weight * vector.get(tag_id, 0.0)
        scored.append((score + rng.uniform(0, 0.4), item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored


def _pick_diverse(scored, slots, used_categories=()):
    """حداکثر یک آیتم از هر دسته (دسته‌های از قبل انتخاب‌شده هم حساب می‌شوند)، تا سقف slots تا."""
    chosen, used_categories = [], set(used_categories)
    for score, item in scored:
        if item.category_id in used_categories:
            continue
        chosen.append((score, item))
        used_categories.add(item.category_id)
        if len(chosen) >= slots:
            break
    if len(chosen) < slots:  # اگر دسته‌ها کم بودند، تکرار دسته را می‌پذیریم
        for score, item in scored:
            if any(item.id == picked.id for _, picked in chosen):
                continue
            chosen.append((score, item))
            if len(chosen) >= slots:
                break
    return chosen


def _select(user, date, vector, slots, exclude_ids, rerank=None, used_categories=()):
    """
    با استخر تنگ شروع می‌کند و اگر چیزی پیدا نشد، قوانین را مرحله‌به‌مرحله شل می‌کند.
    rerank (اختیاری): قلاب مدل ML که فهرست امتیازخورده را دوباره مرتب می‌کند —
    فقط ترتیب را عوض می‌کند، نه استخر کاندیدها و نه قوانین.
    used_categories: دسته‌های آیتم‌های تضمینی قبلی، تا تنوع دسته حفظ شود.
    """
    for relax in (0, 1, 2):
        items = list(candidate_items(user, date, exclude_ids, relax=relax)[:400])
        if len(items) >= slots or (items and relax == 2):
            scored = _score_items(items, vector, seed=f"{user.pk}-{date}-{relax}")
            if rerank is not None:
                scored = rerank(scored)
            return _pick_diverse(scored, slots, used_categories)
    return []


# ---------------------------------------------------------------- مناسبت


def occasions_for(date):
    """
    مناسبت‌های امروز از هر سه منبع: تقویم ایرانی (شمسی)، روزهای جهانی (میلادی)
    و دستور مدیر. مناسبت‌های تکرارشونده سال ندارند؛ دستور یک‌باره مدیر دارد.
    """
    jy, jm, jd = to_jalali(date)
    jalali_match = Q(calendar=Occasion.JALALI, month=jm, day=jd) & (
        Q(year__isnull=True) | Q(year=jy)
    )
    gregorian_match = Q(calendar=Occasion.GREGORIAN, month=date.month, day=date.day) & (
        Q(year__isnull=True) | Q(year=date.year)
    )
    return list(
        Occasion.objects.filter(is_active=True)
        .filter(jalali_match | gregorian_match)
        .prefetch_related("tags", "pinned_items__category")
        # اولویت بالاتر اول؛ در تساوی، «admin» الفبایی قبل از iran و national است
        .order_by("-priority", "source")
    )


def occasion_for(date):
    """مناسبت اصلی امروز — همانی که روی بنر صفحه امروز می‌نشیند."""
    occasions = occasions_for(date)
    return occasions[0] if occasions else None


# ------------------------------------------------------- کافه و دورهمی

# پیشنهاد «برو بیرون» فقط وقتی معنی دارد که خودِ کاربر آدمش باشد
COMPANY_TAG_SLUGS = ("social", "outdoor")


def wants_company(user):
    """آیا از شناخت ما از کاربر برمی‌آید که کافه یا دورهمی به کارش می‌آید؟"""
    if not user.can_see_places:
        return False
    weights = UserTagAffinity.objects.filter(
        user=user, tag__slug__in=COMPANY_TAG_SLUGS
    ).values_list("weight", flat=True)
    return sum(weights) > 0


def _company_pick(user, date, vector, exclude_ids):
    """
    بهترین «جا یا جمع» برای امروز: مکان‌های شهر (کافه، رستوران، پارک) یا آیتم‌های
    اجتماعی (دورهمی). پیاده‌روی تنها بیرون از خانه اینجا نمی‌آید — آن را موتور عادی می‌آورد.
    """
    items = list(
        candidate_items(user, date, exclude_ids)
        .filter(Q(category__needs_city=True) | Q(tags__slug="social"))
        .distinct()[:150]
    )
    if not items:
        return None
    scored = _score_items(items, vector, seed=f"company-{user.pk}-{date}")
    return scored[0] if scored else None


def _screen_pick(user, date, vector, exclude_ids):
    """بهترین فیلم یا سریال برای امروز — با همان بردار، پس وقتِ کم سریال را پایین می‌آورد."""
    items = list(
        candidate_items(user, date, exclude_ids)
        .filter(category__slug__in=SCREEN_CATEGORY_SLUGS)[:300]
    )
    if not items:
        return None
    scored = _score_items(items, vector, seed=f"screen-{user.pk}-{date}")
    return scored[0] if scored else None


# ------------------------------------------------------- نیازهای امروز


def today_needs(user, mood_entry):
    """
    «امروز چه چیزی به کار کاربر می‌آید؟» فقط از مود و جواب‌های امروز (نه پروفایل):
      company → دلش بیرون رفتن/جمع می‌خواهد و شهرش پشتیبانی می‌شود (کافه/رستوران/دورهمی)
      screen  → سرگرمی می‌خواهد و وقتش کم نیست (فیلم/سریال)
      more    → امروز آزاد است؛ یک پیشنهاد بیشتر
    هر نیاز یک اسلات به «متناسب با حالت» اضافه می‌کند (۳ پایه تا ۳ + MOOD_EXTRA_MAX).
    """
    need = _combine(
        (mood_vector(mood_entry.mood), 1.0),
        (daily_answer_vector(user, mood_entry.date), 1.0),
    )
    ids = dict(Tag.objects.filter(slug__in=("social", "outdoor", "escape", "long")).values_list("slug", "id"))

    def weight(slug):
        return need.get(ids.get(slug), 0.0)

    needs = []
    if user.can_see_places and weight("social") + weight("outdoor") > 0:
        needs.append("company")
    if weight("escape") > 0 and weight("long") >= 0:
        needs.append("screen")
    if weight("long") > 0:
        needs.append("more")
    return needs[:MOOD_EXTRA_MAX]


def _occasion_pick(user, date, occasion, exclude_ids):
    """
    آیتم «به مناسبتِ» امروز: باید دست‌کم یکی از تگ‌های مناسبت را داشته باشد؛ رتبه‌بندی
    اول با ربط به مناسبت (تگ‌های مناسبت × W_OCCASION_PICK) و بعد با سلیقه‌ی کاربر —
    یعنی روز کتاب، کتابی که به او می‌خورد؛ نه چیزی که فقط به سلیقه‌اش می‌خورد.
    """
    tag_ids = [tag.id for tag in occasion.tags.all()]
    if not tag_ids:
        return None
    items = list(
        candidate_items(user, date, exclude_ids).filter(tags__in=tag_ids).distinct()[:300]
    )
    if not items:
        return None
    vector = _combine(
        ({tag_id: 1.0 for tag_id in tag_ids}, W_OCCASION_PICK),
        (profile_vector(user), W_PROFILE_IN_OCCASION_PICK),
    )
    scored = _score_items(items, vector, seed=f"occasion-{user.pk}-{date}")
    return scored[0] if scored else None


# ---------------------------------------------------------------- تولید پیشنهاد


def build_day_layer(user, date):
    """
    «پیشنهاد روز» — مستقل از مود، بر دو پایه: شناخت کلی ما از کاربر + مناسبت امروز.
      ۱. دستور مدیر (آیتم‌های قفل‌شده روی مناسبت) — بی‌قید‌وشرط می‌آیند
      ۲. مناسبت اصلی امروز (تقویم ایرانی / روزهای جهانی / ادمین، به ترتیب اولویت):
         یک آیتم تضمینی که به مناسبت ربط دارد، و تگ‌های مناسبت روی بقیه هم وزن می‌گیرند
      ۳. شناخت ما از کاربر — و اگر اهلش باشد، یک کافه یا دورهمی

    یک بار در روز ساخته و ذخیره می‌شود؛ رفرش صفحه عوضش نمی‌کند.
    """
    existing = DailyRecommendation.objects.filter(
        user=user, date=date, source=DailyRecommendation.PROFILE
    ).select_related("item", "item__category", "occasion")
    if existing.exists():
        return list(existing)

    occasions = occasions_for(date)
    primary = occasions[0] if occasions else None

    vector = profile_vector(user)
    for occasion in occasions:
        for tag in occasion.tags.all():
            vector[tag.id] = vector.get(tag.id, 0.0) + 3.0

    slots = settings.HALINO_PROFILE_SLOTS
    blocked = set(
        UserItemStatus.objects.filter(
            user=user, status=UserItemStatus.SKIPPED
        ).values_list("item_id", flat=True)
    )

    chosen, used = [], set()
    linked = {}  # item_id -> مناسبتی که این آیتم «به مناسبتِ» آن آمده

    # ۱. دستور مدیر — از فیلتر موتور رد نمی‌شود، فقط «نمی‌خوام» کاربر را محترم می‌شمارد
    for occasion in occasions:
        for item in occasion.pinned_items.all():
            if item.id in used or item.id in blocked or not item.is_active:
                continue
            chosen.append((99.0, item))
            used.add(item.id)
            linked[item.id] = occasion
            if len(chosen) >= slots:
                break

    # ۲. آیتمِ مناسبت — اگر مدیر چیزی قفل نکرده، خودمان یکی مرتبط با مناسبت اصلی می‌آوریم
    if primary is not None and len(chosen) < slots and not linked:
        pick = _occasion_pick(user, date, primary, used)
        if pick:
            chosen.append(pick)
            used.add(pick[1].id)
            linked[pick[1].id] = primary

    # ۳. کافه یا دورهمی
    if len(chosen) < slots and wants_company(user):
        pick = _company_pick(user, date, vector, used)
        if pick:
            chosen.append(pick)
            used.add(pick[1].id)

    # ۴. بقیه جاها با موتور (پروفایل + بوست تگ‌های مناسبت)
    if len(chosen) < slots:
        chosen.extend(
            _select(
                user, date, vector, slots - len(chosen), exclude_ids=used,
                used_categories={item.category_id for _, item in chosen},
            )
        )

    rows = [
        DailyRecommendation(
            user=user,
            date=date,
            item=item,
            source=DailyRecommendation.PROFILE,
            occasion=linked.get(item.id),
            position=index,
            score=round(score, 3),
        )
        for index, (score, item) in enumerate(chosen[:slots])
    ]
    DailyRecommendation.objects.bulk_create(rows, ignore_conflicts=True)
    return list(
        DailyRecommendation.objects.filter(
            user=user, date=date, source=DailyRecommendation.PROFILE
        ).select_related("item", "item__category", "occasion")
    )


# نام قدیمی، برای اینکه چیزی نشکند
build_profile_layer = build_day_layer


def build_mood_layer(user, mood_entry):
    """
    لایه دوم — بر اساس مود + پاسخ سؤال‌های روز + مودهای ۷ روز اخیر (با decay).
    تعداد پویا: ۳ پایه + یک اسلات برای هر نیاز امروز (today_needs).
    زیر لایه اول اضافه می‌شود، جایگزینش نمی‌شود. اگر کاربر مودش را عوض کند،
    این لایه دوباره ساخته می‌شود ولی لایه اول دست‌نخورده می‌ماند.
    """
    date = mood_entry.date
    DailyRecommendation.objects.filter(
        user=user, date=date, source=DailyRecommendation.MOOD
    ).delete()

    vector = _combine(
        (profile_vector(user), W_PROFILE_IN_MOOD_LAYER),
        (mood_vector(mood_entry.mood), W_MOOD),
        (daily_answer_vector(user, date), W_DAILY_ANSWERS),
        (mood_history_vector(user, date), W_MOOD_HISTORY),
    )

    used = set(
        DailyRecommendation.objects.filter(user=user, date=date).values_list(
            "item_id", flat=True
        )
    )

    # نیازهای امروز: هر کدام یک اسلات اضافه با آیتم تضمینی (کافه/دورهمی، فیلم/سریال)
    needs = today_needs(user, mood_entry)
    picked = []
    for need in needs:
        pick = None
        if need == "company":
            pick = _company_pick(user, date, vector, used)
        elif need == "screen":
            pick = _screen_pick(user, date, vector, used)
        if pick:
            picked.append(pick)
            used.add(pick[1].id)

    slots = settings.HALINO_MOOD_SLOTS + len(needs)
    if slots > len(picked):
        picked.extend(
            _select(
                user, date, vector, slots - len(picked), exclude_ids=used,
                rerank=ml.reranker(user, mood_entry.mood),  # فقط این پنل؛ با داده کم None است
                used_categories={item.category_id for _, item in picked},
            )
        )

    rows = [
        DailyRecommendation(
            user=user,
            date=date,
            item=item,
            source=DailyRecommendation.MOOD,
            mood_entry=mood_entry,
            position=index,
            score=round(score, 3),
        )
        for index, (score, item) in enumerate(picked)
    ]
    DailyRecommendation.objects.bulk_create(rows, ignore_conflicts=True)
    return list(
        DailyRecommendation.objects.filter(
            user=user, date=date, source=DailyRecommendation.MOOD
        ).select_related("item", "item__category")
    )


def apply_feedback(user, item, status, rating=None):
    """ثبت اکشن کاربر روی یک آیتم و به‌روزرسانی پروفایل تگ‌محور او."""
    row, _ = UserItemStatus.objects.update_or_create(
        user=user, item=item, defaults={"status": status, "rating": rating}
    )
    if status == UserItemStatus.DONE:
        # «بعد از یک بازه طولانی بگو این را ریویو کن»
        row.review_after = row.updated_at.date() + timedelta(days=90)
        row.save(update_fields=["review_after"])
    rebuild_affinity(user)
    return row

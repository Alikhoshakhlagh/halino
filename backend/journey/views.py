import random
from collections import Counter
from datetime import date as date_cls

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import City
from content.models import Category, Item

from . import engine
from .jalali import (
    MONTH_NAMES,
    WEEKDAY_NAMES,
    jalali_month_length,
    jalali_to_gregorian,
    jalali_weekday,
    to_farsi_digits,
    to_jalali,
)
from .models import (
    Answer,
    DailyRecommendation,
    Mood,
    MoodEntry,
    Question,
    UserItemStatus,
)


def _today():
    return timezone.localdate()


# ------------------------------------------------------------- آنبوردینگ


OTHER = "other"  # مقدار چیپ «مورد دیگه…» در فرم‌ها


def _questions(scope):
    return list(
        Question.objects.filter(scope=scope, is_active=True)
        .prefetch_related("options")
        .order_by("order")
    )


def _daily_boxes():
    """سؤال‌های روز، گروه‌شده در جعبه‌ها: [(عنوان جعبه, [سؤال‌ها]), ...]"""
    boxes = []
    for question in _questions(Question.DAILY):
        if not boxes or boxes[-1][2] != question.box:
            boxes.append((question.box_title, [], question.box))
        boxes[-1][1].append(question)
    return [(title, questions) for title, questions, _box in boxes]


def _save_answers(user, questions, rows, date=None):
    """
    پاسخ‌های قبلی همین سؤال‌ها را با ردیف‌های تازه جایگزین می‌کند و حافظه‌ی تگ کاربر را
    به‌روز می‌کند: بار اول افزایشی (learn_from_answers)، در ویرایش بازسازی کامل تا
    وزن‌های قبلی دو بار حساب نشوند.
    """
    old = Answer.objects.filter(user=user, question__in=questions, date=date)
    had_old = old.exists()
    old.delete()
    Answer.objects.bulk_create(rows, ignore_conflicts=True)
    if had_old:
        engine.rebuild_affinity(user)
    else:
        engine.learn_from_answers(user, rows)


def _collect_answers(request, questions, date=None):
    """
    پاسخ‌های POST را به ردیف‌های Answer (ذخیره‌نشده) تبدیل می‌کند.
    «مورد دیگه» = گزینه‌ی خالی + free_text. برمی‌گرداند: (rows, missing)
    که missing سؤال‌هایی است که پاسخ معتبر ندارند.
    """
    rows, missing = [], []
    for question in questions:
        picked = request.POST.getlist(f"q{question.id}")
        options_by_id = {str(option.id): option for option in question.options.all()}
        # برای نمایش دوباره‌ی فرم در صورت خطا
        question.selected = {value for value in picked if value in options_by_id}
        question.other_text = request.POST.get(f"q{question.id}_other", "").strip()[:120]
        wants_other = question.allows_other and OTHER in picked

        question_rows = [
            Answer(user=request.user, question=question, option=options_by_id[value], date=date)
            for value in picked
            if value in options_by_id
        ]
        if question.kind == Question.SINGLE:
            question_rows = question_rows[:1]
        if wants_other and question.other_text:
            question_rows.append(
                Answer(
                    user=request.user,
                    question=question,
                    option=None,
                    free_text=question.other_text,
                    date=date,
                )
            )
        if not question_rows:
            missing.append(question)
        rows.extend(question_rows)
    return rows, missing


@login_required
def onboarding_view(request):
    """تست اولیه. خروجی‌اش مستقیماً به بردار تگ‌های کاربر تبدیل می‌شود."""
    # سؤال‌های اولیه فقط یک بار پرسیده می‌شوند
    if request.user.onboarding_done:
        return redirect("today")

    questions = _questions(Question.ONBOARDING)
    start_step = 0

    if request.method == "POST":
        request.user.display_name = request.POST.get("display_name", "").strip()[:64]
        city_id = request.POST.get("city") or None
        request.user.city = City.objects.filter(pk=city_id).first() if city_id else None

        rows, missing = _collect_answers(request, questions)
        if missing:
            # بدون پاسخ کامل، آنبوردینگ تمام نمی‌شود
            request.user.save(update_fields=["display_name", "city"])
            start_step = questions.index(missing[0]) + 1  # مرحله‌ی صفر اسم و شهر است
            messages.error(request, "برای هر سؤال یکی از گزینه‌ها رو انتخاب کن.")
        else:
            Answer.objects.filter(
                user=request.user, question__scope=Question.ONBOARDING
            ).delete()
            Answer.objects.bulk_create(rows, ignore_conflicts=True)

            request.user.onboarding_done = True
            request.user.save(update_fields=["display_name", "city", "onboarding_done"])
            engine.rebuild_affinity(request.user)

            # پیشنهادهای امروز باید با پروفایل تازه دوباره ساخته شوند
            DailyRecommendation.objects.filter(user=request.user, date=_today()).delete()
            messages.success(request, "پروفایلت ساخته شد.")
            return redirect("today")

    return render(
        request,
        "journey/onboarding.html",
        {
            "questions": questions,
            "cities": City.objects.all(),
            "nav": "today",
            "start_step": start_step,
        },
    )


# ------------------------------------------------------------- صفحه امروز


@login_required
def today_view(request):
    if not request.user.onboarding_done:
        return redirect("onboarding")

    today = _today()
    day_rows = engine.build_day_layer(request.user, today)

    mood_entry = (
        MoodEntry.objects.filter(user=request.user, date=today)
        .select_related("mood")
        .first()
    )
    mood_rows = []
    if mood_entry:
        mood_rows = list(
            DailyRecommendation.objects.filter(
                user=request.user, date=today, source=DailyRecommendation.MOOD
            ).select_related("item", "item__category")
        )
        if not mood_rows:
            mood_rows = engine.build_mood_layer(request.user, mood_entry)

    # پنل «متناسب با حالت» فقط وقتی معنی دارد که کاربر مود را ثبت کرده باشد
    answered_daily = Answer.objects.filter(
        user=request.user, date=today, question__scope=Question.DAILY
    ).exists()

    hour = timezone.localtime().hour
    if hour < 12:
        greeting = "صبح بخیر"
    elif hour < 18:
        greeting = "ظهرت بخیر"
    else:
        greeting = "شبت بخیر"

    occasion = engine.occasion_for(today)
    hero_occasion = _hero_occasion(request.user, today)
    jy, jm, jd = to_jalali(today)

    # مودهای اصلی = شش تای اول به ترتیب order؛ بقیه زیر «بیشتر»
    moods = list(Mood.objects.all())
    main_moods, more_moods = moods[:MAIN_MOODS], moods[MAIN_MOODS:]

    daily_boxes = _daily_boxes()

    context = {
        "nav": "today",
        "greeting": greeting,
        "today": {
            "day": to_farsi_digits(jd),
            "weekday": WEEKDAY_NAMES[jalali_weekday(today)],
            "month": MONTH_NAMES[jm - 1],
        },
        "today_iso": today.isoformat(),
        "occasion": occasion,
        "hero_occasion": hero_occasion,
        "hero_color": _occasion_color(hero_occasion),
        "hero_icon": HERO_ICONS.get(hero_occasion.source, "sparkles") if hero_occasion else "",
        "main_moods": main_moods,
        "more_moods": more_moods,
        "mood_entry": mood_entry,
        "just_logged": request.GET.get("logged") == "1",
        "answered_daily": answered_daily,
        "daily_boxes": daily_boxes,
        "day_rows": day_rows,
        "mood_rows": mood_rows,
        "reading": engine.active_serial_items(request.user),
    }
    return render(request, "journey/today.html", context)


MAIN_MOODS = 6


# مناسبتِ هیرو: از میان مناسبت‌های امروز، آنی که تگ‌هایش بیشترین هم‌پوشانی را با
# شناخت ما از کاربر دارد؛ در تساوی، اولویت بالاتر. هیچ عددی به کاربر نشان داده نمی‌شود.
HERO_ICONS = {"iran": "sun", "national": "globe", "admin": "sparkles"}
SOURCE_COLORS = {"iran": "#34D399", "national": "#4CC9F0", "admin": "#7C5CFF"}


def _hero_occasion(user, date):
    occasions = engine.occasions_for(date)
    if not occasions:
        return None
    vector = engine.profile_vector(user)

    def overlap(occasion):
        return sum(max(vector.get(tag.id, 0.0), 0.0) for tag in occasion.tags.all())

    return max(occasions, key=lambda o: (overlap(o), o.priority))


def _occasion_color(occasion):
    """رنگ زمینه‌ی مناسبت: دسته‌ی اولین آیتم قفل‌شده، وگرنه رنگ منبع."""
    if occasion is None:
        return ""
    pinned = occasion.pinned_items.all()[:1]
    if pinned:
        return pinned[0].category.color
    return SOURCE_COLORS.get(occasion.source, "#7C5CFF")


@login_required
@require_POST
def set_mood_view(request):
    """ثبت یا ویرایش مود امروز. لایه اول دست‌نخورده می‌ماند، لایه دوم بازسازی می‌شود."""
    mood = get_object_or_404(Mood, pk=request.POST.get("mood"))
    today = _today()
    entry, _ = MoodEntry.objects.update_or_create(
        user=request.user,
        date=today,
        defaults={"mood": mood, "note": request.POST.get("note", "")[:200]},
    )
    engine.build_mood_layer(request.user, entry)

    # مستقیم به دو سؤال روز (پاپ‌آپ «ثبت شد» همان‌جا یک ثانیه می‌ماند)؛
    # اگر امروز قبلاً جواب داده، برگشت به امروز با پاپ‌آپ تأیید
    answered = Answer.objects.filter(
        user=request.user, date=today, question__scope=Question.DAILY
    ).exists()
    if answered or not _questions(Question.DAILY):
        return redirect(f"{reverse('today')}?logged=1")
    return redirect(f"{reverse('daily_questions')}?logged=1")


@login_required
def daily_questions_view(request):
    """سؤال‌های روز — اختیاری. رد کردنش هیچ چیزی را خراب نمی‌کند."""
    today = _today()
    entry = MoodEntry.objects.filter(user=request.user, date=today).first()
    if entry is None:
        return redirect("today")

    boxes = _daily_boxes()
    questions = [question for _title, group in boxes for question in group]

    if request.method == "POST":
        rows, _missing = _collect_answers(request, questions, date=today)
        if rows:
            _save_answers(request.user, questions, rows, date=today)
        engine.build_mood_layer(request.user, entry)  # پاسخ‌ها روی لایه دوم اثر دارند
        return redirect("today")

    return render(
        request,
        "journey/daily_questions.html",
        {
            "boxes": boxes,
            "entry": entry,
            "nav": "today",
            "today_iso": today.isoformat(),
            "just_logged": request.GET.get("logged") == "1",
        },
    )


# ------------------------------------------------------------- تقویم


@login_required
def calendar_view(request):
    jy_now, jm_now, _ = to_jalali(_today())
    try:
        jy = int(request.GET.get("y", jy_now))
        jm = int(request.GET.get("m", jm_now))
    except ValueError:
        jy, jm = jy_now, jm_now
    if not 1 <= jm <= 12:
        jm = jm_now

    length = jalali_month_length(jy, jm)
    first_date = date_cls(*jalali_to_gregorian(jy, jm, 1))
    last_date = date_cls(*jalali_to_gregorian(jy, jm, length))

    entries = {
        entry.date: entry
        for entry in MoodEntry.objects.filter(
            user=request.user, date__gte=first_date, date__lte=last_date
        ).select_related("mood")
    }

    cells = [None] * jalali_weekday(first_date)
    for day in range(1, length + 1):
        gdate = date_cls(*jalali_to_gregorian(jy, jm, day))
        entry = entries.get(gdate)
        cells.append(
            {
                "day": to_farsi_digits(day),
                "entry": entry,
                "is_today": gdate == _today(),
                "is_future": gdate > _today(),
            }
        )

    values = list(entries.values())

    # --- گزارش ماهانه: شیشه مود، راهنما، نمودار نوسان ---------------------
    counter = Counter(entry.mood_id for entry in values)
    moods_by_id = {mood.id: mood for mood in Mood.objects.all()}
    legend = [
        {"mood": moods_by_id[mood_id], "n": n} for mood_id, n in counter.most_common()
    ]
    dominant = legend[0]["mood"] if legend else None

    # هر روز ثبت‌شده یک توپ در شیشه. ترتیب را به‌هم می‌ریزیم تا طبیعی به نظر برسد،
    # ولی با seed ثابت تا با هر رفرش جابه‌جا نشود.
    balls = [entry.mood for entry in values]
    random.Random(f"{request.user.pk}-{jy}-{jm}").shuffle(balls)

    # فقط شمارش و پوشش — میانگین انرژی/خوشایندی داده‌ی داخلی است و نمایش داده نمی‌شود
    stats = {
        "count": len(values),
        "coverage": to_farsi_digits(round(len(values) * 100 / length)) if length else "۰",
    }

    prev_y, prev_m = (jy - 1, 12) if jm == 1 else (jy, jm - 1)
    next_y, next_m = (jy + 1, 1) if jm == 12 else (jy, jm + 1)

    return render(
        request,
        "journey/calendar.html",
        {
            "nav": "calendar",
            "cells": cells,
            "month_name": MONTH_NAMES[jm - 1],
            "year_label": to_farsi_digits(jy),
            "stats": stats,
            "legend": legend,
            "dominant": dominant,
            "balls": balls,
            "chart": _mood_chart(entries, jy, jm, length),
            "prev": {"y": prev_y, "m": prev_m},
            "next": {"y": next_y, "m": next_m},
        },
    )


# هندسه نمودار نوسان مود — در ویو حساب می‌شود تا تمپلیت فقط بکشد.
# محور روزها راست‌به‌چپ است: روز ۱ سمت راست، آخرین روز سمت چپ.
CHART_W, CHART_H = 320, 158
CHART_TOP, CHART_BOTTOM = 16, 34
PLOT_LEFT, PLOT_RIGHT = 12, CHART_W - 44
AXIS_X = CHART_W - 30
FACE_SIZE = 20


def _chart_y(valence):
    span = CHART_H - CHART_TOP - CHART_BOTTOM
    return CHART_TOP + (2 - valence) * span / 4


def _mood_chart(entries, jy, jm, length):
    """
    محور عمودی: خوشایندی از ۲+ (بالا) تا ۲- (پایین).
    هر روز ثبت‌شده یک نقطه به رنگ مود همان روز، و خط شکسته بین نقطه‌ها.
    """
    step = (PLOT_RIGHT - PLOT_LEFT) / max(length - 1, 1)

    # نماینده هر سطح خوشایندی، برای چهره‌های کنار محور
    representative = {}
    for mood in Mood.objects.all():
        representative.setdefault(mood.valence, mood)

    rows = []
    for valence in (2, 1, 0, -1, -2):
        y = _chart_y(valence)
        rows.append(
            {
                "y": round(y, 2),
                "face_y": round(y - FACE_SIZE / 2, 2),
                "mood": representative.get(valence),
                "valence": valence,
            }
        )

    points = []
    for day in range(1, length + 1):
        entry = entries.get(date_cls(*jalali_to_gregorian(jy, jm, day)))
        if entry is None:
            continue
        points.append(
            {
                "x": round(PLOT_RIGHT - (day - 1) * step, 2),
                "y": round(_chart_y(entry.mood.valence), 2),
                "color": entry.mood.color,
                "day": day,
            }
        )
    points.sort(key=lambda p: p["x"])

    labels = [
        {"day": to_farsi_digits(day), "x": round(PLOT_RIGHT - (day - 1) * step, 2)}
        for day in range(1, length + 1, 4)
    ]

    return {
        "width": CHART_W,
        "height": CHART_H,
        "left": PLOT_LEFT,
        "right": PLOT_RIGHT + 6,
        "axis_x": AXIS_X,
        "face_size": FACE_SIZE,
        "rows": rows,
        "points": points,
        "labels": labels,
        "baseline": round(CHART_H - CHART_BOTTOM + 18, 2),
        "polyline": " ".join(f"{p['x']},{p['y']}" for p in points),
    }


# ------------------------------------------------------------- دسته‌بندی


def _visible_categories(user):
    qs = Category.objects.all()
    if not user.can_see_places:
        qs = qs.filter(needs_city=False)
    # annotate با GROUP BY ترتیب پیش‌فرض Meta را حذف می‌کند، پس صریح مرتب می‌کنیم
    return qs.annotate(n=Count("items")).order_by("order", "name")


@login_required
def category_list_view(request):
    return render(
        request,
        "journey/category_list.html",
        {"nav": "category", "categories": _visible_categories(request.user)},
    )


@login_required
def category_detail_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if category.needs_city and not request.user.can_see_places:
        raise Http404("این دسته برای شهر شما فعال نیست.")

    items = Item.objects.filter(category=category, is_active=True)
    if category.needs_city:
        items = items.filter(city=request.user.city)

    statuses = {
        row.item_id: row
        for row in UserItemStatus.objects.filter(user=request.user, item__in=items)
    }
    rows = [(item, statuses.get(item.id)) for item in items[:300]]

    return render(
        request,
        "journey/category_detail.html",
        {"nav": "category", "category": category, "rows": rows},
    )


@login_required
def item_detail_view(request, pk):
    item = get_object_or_404(Item.objects.select_related("category", "city"), pk=pk)
    status = UserItemStatus.objects.filter(user=request.user, item=item).first()
    # چیپ‌های صفحه: پررنگ‌ترین تگ‌های خود آیتم (نه چیزی از پروفایل کاربر)
    tags = list(item.tags.order_by("-itemtag__weight", "name")[:4])
    return render(
        request,
        "journey/item_detail.html",
        {"nav": "category", "item": item, "status": status, "tags": tags},
    )


@login_required
@require_POST
def item_action_view(request, pk):
    """بازخورد یک‌کلیکه: انجام دادم / نمی‌خوام / شروع کردم / امتیاز."""
    item = get_object_or_404(Item, pk=pk)
    action = request.POST.get("action")
    rating = request.POST.get("rating") or None

    mapping = {
        "done": UserItemStatus.DONE,
        "skip": UserItemStatus.SKIPPED,
        "progress": UserItemStatus.IN_PROGRESS,
        "reset": UserItemStatus.NOT_STARTED,
    }
    if action not in mapping:
        raise Http404("اکشن نامعتبر")

    if mapping[action] == UserItemStatus.IN_PROGRESS and not item.category.is_serial:
        messages.error(request, "این دسته وضعیت «در حال انجام» ندارد.")
        return redirect(request.POST.get("next") or "today")

    engine.apply_feedback(
        request.user,
        item,
        mapping[action],
        rating=int(rating) if rating and rating.isdigit() else None,
    )
    messages.success(request, "ثبت شد.")
    return redirect(request.POST.get("next") or "today")


# ------------------------------------------------------------- پروفایل


@login_required
def profile_view(request):
    if request.method == "POST" and request.POST.get("form") == "question":
        # «بهتر بشناسیمت»: هر کارت سؤال فرم خودش را می‌فرستد
        question = get_object_or_404(
            Question, pk=request.POST.get("question"), scope=Question.PROFILE, is_active=True
        )
        rows, missing = _collect_answers(request, [question])
        if missing:
            messages.error(request, "یکی از گزینه‌ها رو انتخاب کن.")
        else:
            _save_answers(request.user, [question], rows)
            # لایه‌ی «متناسب با حالت» امروز با حافظه‌ی تازه دوباره ساخته می‌شود
            entry = MoodEntry.objects.filter(user=request.user, date=_today()).first()
            if entry:
                engine.build_mood_layer(request.user, entry)
            messages.success(request, "ثبت شد.")
        return redirect("profile")

    if request.method == "POST":
        request.user.display_name = request.POST.get("display_name", "").strip()[:64]
        city_id = request.POST.get("city") or None
        request.user.city = City.objects.filter(pk=city_id).first() if city_id else None
        request.user.save(update_fields=["display_name", "city"])
        messages.success(request, "پروفایل به‌روز شد.")
        return redirect("profile")

    # صفحه پروفایل فقط اکشن و تنظیمات است؛ هیچ داده‌ی داخلی (تمایل تگ، آمار) نمی‌رود
    skipped = UserItemStatus.objects.filter(
        user=request.user, status=UserItemStatus.SKIPPED
    ).select_related("item", "item__category")

    # فقط سؤال‌های scope=profile؛ جواب‌داده‌شده‌ها با تیک و متن پاسخ جمع می‌شوند
    questions = _questions(Question.PROFILE)
    answers = Answer.objects.filter(
        user=request.user, question__in=questions, date=None
    ).select_related("option")
    by_question = {}
    for answer in answers:
        by_question.setdefault(answer.question_id, []).append(answer)
    for question in questions:
        picked = by_question.get(question.id, [])
        question.selected = {str(a.option_id) for a in picked if a.option_id}
        question.other_text = next((a.free_text for a in picked if a.option_id is None), "")
        question.answered = [a.option.text if a.option_id else a.free_text for a in picked]

    return render(
        request,
        "journey/profile.html",
        {
            "nav": "profile",
            "cities": City.objects.all(),
            "skipped": skipped,
            "questions": questions,
        },
    )

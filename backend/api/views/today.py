from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from journey import engine
from journey.jalali import MONTH_NAMES, WEEKDAY_NAMES, jalali_weekday, to_jalali
from journey.models import (
    Answer,
    DailyRecommendation,
    Mood,
    MoodEntry,
    Question,
    UserItemStatus,
)

from ..answers import get_questions
from ..serializers import ItemSerializer, MoodSerializer, OccasionSerializer

def get_greeting():
    hour = timezone.localtime().hour
    if hour < 12:
        return "صبح بخیر"
    if hour < 18:
        return "ظهرت بخیر"
    return "شبت بخیر"


def pick_main_occasion(user, date):
    occasions = engine.occasions_for(date)
    if not occasions:
        return None
    vector = engine.profile_vector(user)

    def overlap(occasion):
        return sum(max(vector.get(tag.id, 0.0), 0.0) for tag in occasion.tags.all())

    return max(occasions, key=lambda occasion: (overlap(occasion), occasion.priority))


def recommendation_list(user, rows):
    statuses = dict(
        UserItemStatus.objects.filter(
            user=user, item__in=[row.item_id for row in rows]
        ).values_list("item_id", "status")
    )

    data = []
    for row in rows:
        status = statuses.get(row.item_id)
        if status == UserItemStatus.SKIPPED:
            continue
        data.append(
            {
                "item": ItemSerializer(row.item).data,
                "because": row.occasion.title if row.occasion_id else "",
                "is_done": status == UserItemStatus.DONE,
            }
        )
    return data


def has_answered_daily(user, date):
    return Answer.objects.filter(
        user=user, date=date, question__scope=Question.DAILY
    ).exists()


@api_view(["GET"])
def today_view(request):
    user = request.user
    if not user.onboarding_done:
        return Response({"onboarding_required": True})

    today = timezone.localdate()
    day_rows = engine.build_day_layer(user, today)

    mood_entry = MoodEntry.objects.filter(user=user, date=today).select_related("mood").first()
    mood_rows = []
    if mood_entry:
        mood_rows = list(
            DailyRecommendation.objects.filter(
                user=user, date=today, source=DailyRecommendation.MOOD
            ).select_related("item", "item__category", "item__city", "occasion")
        )
        if not mood_rows:
            mood_rows = engine.build_mood_layer(user, mood_entry)

    occasion = pick_main_occasion(user, today)
    jalali_year, jalali_month, jalali_day = to_jalali(today)

    return Response(
        {
            "greeting": get_greeting(),
            "display_name": user.display_name,
            "today_iso": today.isoformat(),
            "date": {
                "day": jalali_day,
                "weekday": WEEKDAY_NAMES[jalali_weekday(today)],
                "month": MONTH_NAMES[jalali_month - 1],
                "year": jalali_year,
            },
            "occasion": OccasionSerializer(occasion).data if occasion else None,
            "moods": MoodSerializer(Mood.objects.all(), many=True).data,
            "mood": MoodSerializer(mood_entry.mood).data if mood_entry else None,
            "answered_daily": has_answered_daily(user, today),
            "in_progress": [
                ItemSerializer(row.item).data for row in engine.active_serial_items(user)
            ],
            "mood_items": recommendation_list(user, mood_rows),
            "day_items": recommendation_list(user, day_rows),
        }
    )


@api_view(["POST"])
def set_mood_view(request):
    mood_id = str(request.data.get("mood", ""))
    mood = get_object_or_404(Mood, pk=mood_id) if mood_id.isdigit() else None
    if mood is None:
        return Response({"detail": "این حال پیدا نشد."}, status=404)

    today = timezone.localdate()
    entry, _ = MoodEntry.objects.update_or_create(
        user=request.user,
        date=today,
        defaults={"mood": mood, "note": str(request.data.get("note", ""))[:200]},
    )
    engine.build_mood_layer(request.user, entry)

    ask_questions = bool(get_questions(Question.DAILY)) and not has_answered_daily(
        request.user, today
    )
    return Response({"mood": MoodSerializer(mood).data, "ask_questions": ask_questions})

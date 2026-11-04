import random
from collections import Counter
from datetime import date as date_cls

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from journey.jalali import (
    MONTH_NAMES,
    jalali_month_length,
    jalali_to_gregorian,
    jalali_weekday,
    to_jalali,
)
from journey.models import Mood, MoodEntry

from ..serializers import MoodSerializer


def get_requested_month(request, today):
    current_year, current_month, _ = to_jalali(today)
    try:
        year = int(request.query_params.get("y", current_year))
        month = int(request.query_params.get("m", current_month))
    except ValueError:
        return current_year, current_month
    if not 1 <= month <= 12:
        month = current_month
    return year, month


@api_view(["GET"])
def calendar_view(request):
    today = timezone.localdate()
    year, month = get_requested_month(request, today)
    length = jalali_month_length(year, month)
    first_date = date_cls(*jalali_to_gregorian(year, month, 1))
    last_date = date_cls(*jalali_to_gregorian(year, month, length))

    entries = {
        entry.date: entry
        for entry in MoodEntry.objects.filter(
            user=request.user, date__gte=first_date, date__lte=last_date
        ).select_related("mood")
    }

    days = []
    for day in range(1, length + 1):
        current_date = date_cls(*jalali_to_gregorian(year, month, day))
        entry = entries.get(current_date)
        days.append(
            {
                "day": day,
                "mood": MoodSerializer(entry.mood).data if entry else None,
                "is_today": current_date == today,
                "is_future": current_date > today,
            }
        )

    moods_by_id = {mood.id: mood for mood in Mood.objects.all()}
    counter = Counter(entry.mood_id for entry in entries.values())
    legend = [
        {"mood": MoodSerializer(moods_by_id[mood_id]).data, "count": count}
        for mood_id, count in counter.most_common()
    ]

    balls = [entry.mood for entry in entries.values()]
    random.Random(f"{request.user.pk}-{year}-{month}").shuffle(balls)

    chart_faces = {}
    for mood in moods_by_id.values():
        chart_faces.setdefault(mood.valence, MoodSerializer(mood).data)

    previous_month = {"y": year - 1, "m": 12} if month == 1 else {"y": year, "m": month - 1}
    next_month = {"y": year + 1, "m": 1} if month == 12 else {"y": year, "m": month + 1}

    return Response(
        {
            "year": year,
            "month": month,
            "month_name": MONTH_NAMES[month - 1],
            "first_weekday": jalali_weekday(first_date),
            "days": days,
            "legend": legend,
            "dominant": legend[0]["mood"] if legend else None,
            "balls": MoodSerializer(balls, many=True).data,
            "chart_faces": chart_faces,
            "count": len(entries),
            "coverage": round(len(entries) * 100 / length),
            "previous": previous_month,
            "next": next_month,
        }
    )

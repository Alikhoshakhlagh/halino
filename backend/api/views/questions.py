from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts.models import City
from journey import engine
from journey.models import Answer, DailyRecommendation, MoodEntry, Question

from ..answers import build_answers, get_daily_boxes, get_questions, save_answers
from ..serializers import CitySerializer, MoodSerializer, QuestionSerializer


def save_name_and_city(user, data):
    user.display_name = str(data.get("display_name", "")).strip()[:64]
    city_id = str(data.get("city") or "")
    user.city = City.objects.filter(pk=city_id).first() if city_id.isdigit() else None


@api_view(["GET", "POST"])
def onboarding_view(request):
    user = request.user
    if user.onboarding_done:
        return Response({"done": True})

    questions = get_questions(Question.ONBOARDING)

    if request.method == "GET":
        return Response(
            {
                "done": False,
                "display_name": user.display_name,
                "city": user.city_id,
                "cities": CitySerializer(City.objects.all(), many=True).data,
                "questions": QuestionSerializer(questions, many=True).data,
            }
        )

    save_name_and_city(user, request.data)
    rows, missing = build_answers(user, questions, request.data.get("answers", {}))
    if missing:
        user.save(update_fields=["display_name", "city"])
        return Response(
            {
                "detail": "برای هر سؤال یکی از گزینه‌ها رو انتخاب کن.",
                "missing_question": missing[0].id,
            },
            status=400,
        )

    Answer.objects.filter(user=user, question__scope=Question.ONBOARDING).delete()
    Answer.objects.bulk_create(rows, ignore_conflicts=True)
    user.onboarding_done = True
    user.save(update_fields=["display_name", "city", "onboarding_done"])
    engine.rebuild_affinity(user)
    DailyRecommendation.objects.filter(user=user, date=timezone.localdate()).delete()
    return Response({"done": True})


@api_view(["GET", "POST"])
def daily_questions_view(request):
    today = timezone.localdate()
    entry = MoodEntry.objects.filter(user=request.user, date=today).select_related("mood").first()
    if entry is None:
        return Response({"detail": "اول حال امروزت رو ثبت کن."}, status=404)

    boxes = get_daily_boxes()

    if request.method == "GET":
        return Response(
            {
                "mood": MoodSerializer(entry.mood).data,
                "boxes": [
                    {
                        "title": box["title"],
                        "questions": QuestionSerializer(box["questions"], many=True).data,
                    }
                    for box in boxes
                ],
            }
        )

    questions = [question for box in boxes for question in box["questions"]]
    rows, _ = build_answers(request.user, questions, request.data.get("answers", {}), date=today)
    if rows:
        save_answers(request.user, questions, rows, date=today)
    engine.build_mood_layer(request.user, entry)
    return Response({"saved": True})

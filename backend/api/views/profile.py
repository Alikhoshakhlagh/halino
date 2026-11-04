from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts.models import City
from journey import engine
from journey.models import Answer, MoodEntry, Question, UserItemStatus

from ..answers import build_answers, get_questions, save_answers
from ..serializers import CitySerializer, ItemSerializer, QuestionSerializer
from .questions import save_name_and_city


def profile_questions_data(user):
    questions = get_questions(Question.PROFILE)
    answers = Answer.objects.filter(
        user=user, question__in=questions, date=None
    ).select_related("option")

    answers_by_question = {}
    for answer in answers:
        answers_by_question.setdefault(answer.question_id, []).append(answer)

    data = []
    for question in questions:
        picked = answers_by_question.get(question.id, [])
        row = QuestionSerializer(question).data
        row["selected"] = [answer.option_id for answer in picked if answer.option_id]
        row["other_text"] = next((a.free_text for a in picked if a.option_id is None), "")
        row["answered"] = [a.option.text if a.option_id else a.free_text for a in picked]
        data.append(row)
    return data


@api_view(["GET", "PATCH"])
def profile_view(request):
    user = request.user

    if request.method == "PATCH":
        save_name_and_city(user, request.data)
        user.save(update_fields=["display_name", "city"])
        return Response({"detail": "پروفایل به‌روز شد."})

    skipped = UserItemStatus.objects.filter(
        user=user, status=UserItemStatus.SKIPPED
    ).select_related("item", "item__category", "item__city")

    return Response(
        {
            "display_name": user.display_name,
            "phone": user.phone,
            "city": user.city_id,
            "cities": CitySerializer(City.objects.all(), many=True).data,
            "questions": profile_questions_data(user),
            "skipped": [ItemSerializer(row.item).data for row in skipped],
        }
    )


@api_view(["POST"])
def profile_question_view(request, pk):
    question = get_object_or_404(Question, pk=pk, scope=Question.PROFILE, is_active=True)
    answers = {str(question.id): request.data}
    rows, missing = build_answers(request.user, [question], answers)
    if missing:
        return Response({"detail": "یکی از گزینه‌ها رو انتخاب کن."}, status=400)

    save_answers(request.user, [question], rows)
    entry = MoodEntry.objects.filter(user=request.user, date=timezone.localdate()).first()
    if entry:
        engine.build_mood_layer(request.user, entry)
    return Response({"detail": "ثبت شد."})

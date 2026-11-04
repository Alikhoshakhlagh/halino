from journey import engine
from journey.models import Answer, Question


def get_questions(scope):
    return list(
        Question.objects.filter(scope=scope, is_active=True)
        .prefetch_related("options")
        .order_by("order")
    )


def get_daily_boxes():
    boxes = []
    for question in get_questions(Question.DAILY):
        if not boxes or boxes[-1]["number"] != question.box:
            boxes.append({"number": question.box, "title": question.box_title, "questions": []})
        boxes[-1]["questions"].append(question)
    return boxes


def build_answers(user, questions, answers, date=None):
    rows = []
    missing = []
    if not isinstance(answers, dict):
        answers = {}

    for question in questions:
        answer = answers.get(str(question.id))
        if not isinstance(answer, dict):
            answer = {}

        options = answer.get("options")
        picked = [str(option_id) for option_id in options] if isinstance(options, list) else []
        other_text = str(answer.get("other", "")).strip()[:120]

        question_rows = []
        for option in question.options.all():
            if str(option.id) in picked:
                question_rows.append(
                    Answer(user=user, question=question, option=option, date=date)
                )
        if question.kind == Question.SINGLE:
            question_rows = question_rows[:1]
        if question.allows_other and other_text:
            question_rows.append(
                Answer(user=user, question=question, option=None, free_text=other_text, date=date)
            )

        if not question_rows:
            missing.append(question)
        rows.extend(question_rows)
    return rows, missing


def save_answers(user, questions, rows, date=None):
    old_answers = Answer.objects.filter(user=user, question__in=questions, date=date)
    had_old_answers = old_answers.exists()
    old_answers.delete()
    Answer.objects.bulk_create(rows, ignore_conflicts=True)
    if had_old_answers:
        engine.rebuild_affinity(user)
    else:
        engine.learn_from_answers(user, rows)

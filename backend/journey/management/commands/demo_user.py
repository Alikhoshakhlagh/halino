import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import City, User
from content.models import Item
from journey import engine
from journey.models import Answer, Mood, MoodEntry, Question, UserItemStatus

DEMO_PHONE = "09121234567"
DEMO_NAME = "سارا"
DEMO_CITY = "tehran"

MOOD_DAYS = 120
MOOD_FILL_CHANCE = 0.85
EMPTY_RECENT_DAYS = (2, 5, 9)
DAILY_ANSWER_CHANCE = 0.6
DONE_ITEMS = 45
SKIPPED_ITEMS = 10
IN_PROGRESS_CATEGORIES = ("book", "series")

MOOD_WEIGHTS = {
    "calm": 5,
    "happy": 4,
    "focused": 3,
    "tired": 3,
    "bored": 2,
    "longing": 2,
    "anxious": 2,
    "sad": 1,
    "angry": 1,
}


class Command(BaseCommand):
    help = "ساخت کاربر نمونه با داده‌ی فیک و فعالیت زیاد (فقط برای دمو)"

    def add_arguments(self, parser):
        parser.add_argument("--phone", default=DEMO_PHONE)

    @transaction.atomic
    def handle(self, *args, **options):
        if not Mood.objects.exists():
            self.stderr.write("اول دستور seed_base را اجرا کن.")
            return

        self.rng = random.Random(1405)
        self.today = timezone.localdate()

        User.objects.filter(phone=options["phone"]).delete()
        self.user = User.objects.create_user(
            phone=options["phone"],
            display_name=DEMO_NAME,
            city=City.objects.filter(slug=DEMO_CITY).first(),
            onboarding_done=True,
        )

        self.create_profile_answers()
        mood_count = self.create_moods()
        status_count = self.create_item_statuses()
        engine.rebuild_affinity(self.user)

        self.stdout.write(
            f"کاربر {self.user.phone} ساخته شد: {mood_count} روز حال و {status_count} آیتم."
        )

    def pick_options(self, question):
        options = list(question.options.all())
        if question.kind == Question.SINGLE:
            return [self.rng.choice(options)]
        return self.rng.sample(options, min(2, len(options)))

    def create_answers(self, questions, date=None):
        rows = []
        for question in questions:
            for option in self.pick_options(question):
                rows.append(Answer(user=self.user, question=question, option=option, date=date))
        Answer.objects.bulk_create(rows)

    def get_questions(self, scope):
        return list(
            Question.objects.filter(scope=scope, is_active=True).prefetch_related("options")
        )

    def create_profile_answers(self):
        self.create_answers(self.get_questions(Question.ONBOARDING))
        self.create_answers(self.get_questions(Question.PROFILE))

    def create_moods(self):
        moods = list(Mood.objects.all())
        weights = [MOOD_WEIGHTS.get(mood.face, 1) for mood in moods]
        daily_questions = self.get_questions(Question.DAILY)

        entries = []
        for days_ago in range(1, MOOD_DAYS + 1):
            if days_ago in EMPTY_RECENT_DAYS or self.rng.random() > MOOD_FILL_CHANCE:
                continue
            date = self.today - timedelta(days=days_ago)
            mood = self.rng.choices(moods, weights=weights)[0]
            entries.append(MoodEntry(user=self.user, date=date, mood=mood))
            if self.rng.random() < DAILY_ANSWER_CHANCE:
                self.create_answers(daily_questions, date=date)

        MoodEntry.objects.bulk_create(entries)
        return len(entries)

    def create_item_statuses(self):
        items = list(
            Item.objects.filter(is_active=True)
            .filter(Q(category__needs_city=False) | Q(city=self.user.city))
            .select_related("category")
        )
        self.rng.shuffle(items)

        rows = []
        used = set()
        for slug in IN_PROGRESS_CATEGORIES:
            item = next((item for item in items if item.category.slug == slug), None)
            if item:
                rows.append(UserItemStatus(user=self.user, item=item, status=UserItemStatus.IN_PROGRESS))
                used.add(item.id)

        others = [item for item in items if item.id not in used]
        for item in others[:DONE_ITEMS]:
            rating = self.rng.choice([None, 3, 4, 4, 5, 5])
            rows.append(UserItemStatus(user=self.user, item=item, status=UserItemStatus.DONE, rating=rating))
        for item in others[DONE_ITEMS:DONE_ITEMS + SKIPPED_ITEMS]:
            rows.append(UserItemStatus(user=self.user, item=item, status=UserItemStatus.SKIPPED))

        UserItemStatus.objects.bulk_create(rows)
        return len(rows)

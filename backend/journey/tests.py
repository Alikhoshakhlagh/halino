"""
تست‌های حالینو — قوانین اصلی موتور و صفحه امروز.

    python manage.py test
"""

from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase

from accounts.models import City, User
from content.models import Category, Item, Occasion, Tag

from . import engine, ml
from .jalali import (
    format_jalali,
    gregorian_to_jalali,
    is_jalali_leap,
    jalali_month_length,
    jalali_to_gregorian,
)
from .models import (
    Answer,
    DailyRecommendation,
    Mood,
    MoodEntry,
    Question,
    UserItemStatus,
    UserTagAffinity,
)


class JalaliTests(TestCase):
    def test_known_dates(self):
        self.assertEqual(gregorian_to_jalali(2026, 9, 3), (1405, 6, 12))
        self.assertEqual(gregorian_to_jalali(2026, 3, 21), (1405, 1, 1))
        self.assertEqual(jalali_to_gregorian(1405, 1, 1), (2026, 3, 21))

    def test_round_trip(self):
        for gy in (2024, 2025, 2026):
            for gm in range(1, 13):
                for gd in (1, 15, 28):
                    self.assertEqual(
                        jalali_to_gregorian(*gregorian_to_jalali(gy, gm, gd)),
                        (gy, gm, gd),
                    )

    def test_month_lengths(self):
        self.assertEqual(jalali_month_length(1405, 1), 31)
        self.assertEqual(jalali_month_length(1405, 7), 30)
        self.assertIn(jalali_month_length(1405, 12), (29, 30))
        self.assertEqual(is_jalali_leap(1403), True)

    def test_format(self):
        self.assertEqual(format_jalali(date(2026, 9, 3)), "۱۲ شهریور ۱۴۰۵")


class EngineTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_base", verbosity=0)
        call_command("import_titles", verbosity=0)

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000000", city=City.objects.get(slug="tehran")
        )
        self.today = date(2026, 9, 3)

    def _answer_onboarding(self):
        rows = []
        for question in Question.objects.filter(scope=Question.ONBOARDING):
            option = question.options.first()
            rows.append(Answer(user=self.user, question=question, option=option))
        Answer.objects.bulk_create(rows)
        engine.rebuild_affinity(self.user)

    def test_affinity_is_built_from_answers(self):
        self._answer_onboarding()
        self.assertTrue(self.user.affinities.exists())

    def test_day_layer_is_stable_within_a_day(self):
        self._answer_onboarding()
        first = engine.build_day_layer(self.user, self.today)
        second = engine.build_day_layer(self.user, self.today)
        self.assertEqual([r.item_id for r in first], [r.item_id for r in second])
        self.assertEqual(len(first), 3)

    def test_mood_layer_adds_and_does_not_replace(self):
        self._answer_onboarding()
        profile_rows = engine.build_day_layer(self.user, self.today)
        entry = MoodEntry.objects.create(
            user=self.user, date=self.today, mood=Mood.objects.get(name="غمگین")
        )
        mood_rows = engine.build_mood_layer(self.user, entry)

        self.assertTrue(mood_rows)
        # لایه اول دست‌نخورده مانده
        self.assertEqual(
            DailyRecommendation.objects.filter(
                user=self.user, date=self.today, source=DailyRecommendation.PROFILE
            ).count(),
            len(profile_rows),
        )
        # هیچ آیتمی در هر دو لایه تکرار نشده
        profile_ids = {r.item_id for r in profile_rows}
        self.assertFalse(profile_ids & {r.item_id for r in mood_rows})

    def test_serial_rule_blocks_new_book(self):
        """تا کتاب در حال مطالعه تمام نشده، هیچ کتابی پیشنهاد نمی‌شود."""
        self._answer_onboarding()
        book_category = Category.objects.get(slug="book")
        book = Item.objects.filter(category=book_category).first()
        UserItemStatus.objects.create(
            user=self.user, item=book, status=UserItemStatus.IN_PROGRESS
        )

        candidates = engine.candidate_items(self.user, self.today)
        self.assertFalse(candidates.filter(category=book_category).exists())
        self.assertIn(book_category.id, engine.blocked_serial_categories(self.user))

    def test_skipped_items_never_return(self):
        self._answer_onboarding()
        item = Item.objects.filter(category__slug="film").first()
        engine.apply_feedback(self.user, item, UserItemStatus.SKIPPED)
        self.assertFalse(
            engine.candidate_items(self.user, self.today).filter(id=item.id).exists()
        )

    def test_city_gate(self):
        """کاربر شهر پشتیبانی‌نشده نباید هیچ آیتم مکان‌محوری بگیرد."""
        self.user.city = City.objects.get(slug="mashhad")
        self.user.save()
        self.assertFalse(
            engine.candidate_items(self.user, self.today)
            .filter(category__needs_city=True)
            .exists()
        )

        self.user.city = City.objects.get(slug="tehran")
        self.user.save()
        self.assertTrue(
            engine.candidate_items(self.user, self.today)
            .filter(category__needs_city=True)
            .exists()
        )

    def test_anti_repeat(self):
        self._answer_onboarding()
        rows = engine.build_day_layer(self.user, self.today)
        recommended = {r.item_id for r in rows}
        tomorrow_pool = set(
            engine.candidate_items(self.user, self.today).values_list("id", flat=True)
        )
        self.assertFalse(recommended & tomorrow_pool)

    def test_occasions_come_from_both_calendars(self):
        """روز جهانی با تاریخ میلادی و مناسبت ایرانی با تاریخ شمسی پیدا می‌شوند."""
        target = date(2026, 4, 23)  # روز جهانی کتاب
        titles = [o.title for o in engine.occasions_for(target)]
        self.assertIn("روز جهانی کتاب", titles)

        nowruz = date(*jalali_to_gregorian(1405, 1, 1))
        self.assertIn("نوروز", [o.title for o in engine.occasions_for(nowruz)])

    def test_admin_directive_wins_and_pins_items(self):
        """دستور مدیر بالاترین اولویت را دارد و آیتمش حتماً پیشنهاد می‌شود."""
        self._answer_onboarding()
        item = Item.objects.filter(category__slug="meditation").first()
        _, jm, jd = gregorian_to_jalali(self.today.year, self.today.month, self.today.day)
        directive = Occasion.objects.create(
            source=Occasion.ADMIN, calendar=Occasion.JALALI,
            month=jm, day=jd, title="انتخاب سردبیر", priority=50,
        )
        directive.pinned_items.add(item)

        self.assertEqual(engine.occasion_for(self.today).title, "انتخاب سردبیر")
        rows = engine.build_day_layer(self.user, self.today)
        self.assertIn(item.id, [row.item_id for row in rows])

    def test_company_suggestion_needs_a_social_profile(self):
        """کافه/دورهمی فقط برای کاربری که اهلش است و شهرش پشتیبانی می‌شود."""
        self.assertFalse(engine.wants_company(self.user))  # هنوز پروفایلی ندارد

        social = Tag.objects.get(slug="social")
        UserTagAffinity.objects.create(user=self.user, tag=social, weight=4.0)
        self.assertTrue(engine.wants_company(self.user))

        rows = engine.build_day_layer(self.user, self.today)
        categories = {row.item.category.slug for row in rows}
        self.assertIn("cafe", categories)

        # همان کاربر در شهر پشتیبانی‌نشده نباید پیشنهاد مکان بگیرد
        self.user.city = City.objects.get(slug="mashhad")
        self.user.save()
        self.assertFalse(engine.wants_company(self.user))

    def test_feedback_moves_affinity(self):
        self._answer_onboarding()
        item = Item.objects.filter(category__slug="film").first()
        tag_id = item.tags.first().id
        before = self.user.affinities.filter(tag_id=tag_id).first()
        before_weight = before.weight if before else 0.0

        engine.apply_feedback(self.user, item, UserItemStatus.DONE, rating=5)
        after = self.user.affinities.get(tag_id=tag_id)
        self.assertGreater(after.weight, before_weight)


class MLTests(TestCase):
    """Naive Bayes ساده‌ی journey/ml.py — فقط بازچینش بخش «متناسب با حالت»."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_base", verbosity=0)
        call_command("import_titles", verbosity=0)

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000009", city=City.objects.get(slug="tehran")
        )
        self.mood = Mood.objects.get(name="آرام")

    def _feedback(self, items, status):
        for item in items:
            UserItemStatus.objects.create(user=self.user, item=item, status=status)

    def test_below_threshold_keeps_rule_order(self):
        """با کمتر از ۱۰ بازخورد، مدل ساخته نمی‌شود و ترتیب قاعده‌محور می‌ماند."""
        calm = list(Item.objects.filter(tags__slug="calm").distinct()[:4])
        thrill = list(Item.objects.filter(tags__slug="thrilling").distinct()[:4])
        self._feedback(calm, UserItemStatus.DONE)
        self._feedback(thrill, UserItemStatus.SKIPPED)  # ۸ ردیف < ۱۰
        self.assertIsNone(ml.reranker(self.user, self.mood))

    def test_reranker_learns_from_feedback(self):
        """کاربری که آرام‌ها را انجام داده و هیجانی‌ها را رد کرده، آرام را بالاتر می‌بیند."""
        calm_items = list(
            Item.objects.filter(tags__slug="calm").exclude(tags__slug="thrilling").distinct()[:6]
        )
        thrill_items = list(
            Item.objects.filter(tags__slug="thrilling").exclude(tags__slug="calm").distinct()[:6]
        )
        self._feedback(calm_items[:5], UserItemStatus.DONE)
        self._feedback(thrill_items[:5], UserItemStatus.SKIPPED)  # ۱۰ ردیف = آستانه

        rerank = ml.reranker(self.user, self.mood)
        self.assertIsNotNone(rerank)

        # دو آیتم دیده‌نشده با امتیاز قاعده‌محور برابر؛ فقط مدل تعیین‌کننده است
        unseen_calm, unseen_thrill = calm_items[5], thrill_items[5]
        ranked = rerank([(1.0, unseen_thrill), (1.0, unseen_calm)])
        self.assertEqual(ranked[0][1].id, unseen_calm.id)


class MemoryTests(TestCase):
    """فاز ۲: حافظه‌ی کاربر (learn_from_answers) و تاریخچه‌ی مود در لایه‌ی دوم."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_base", verbosity=0)
        call_command("import_titles", verbosity=0)

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000010", city=City.objects.get(slug="tehran")
        )
        self.today = date(2026, 9, 3)

    def _profile_answer(self, question):
        option = question.options.exclude(optiontag=None).first()
        return Answer(user=self.user, question=question, option=option), option

    def test_learn_from_answers_upserts_half_weight(self):
        question = Question.objects.filter(scope=Question.PROFILE).first()
        answer, option = self._profile_answer(question)
        Answer.objects.bulk_create([answer])

        engine.learn_from_answers(self.user, [answer])
        for option_tag in option.optiontag_set.all():
            row = UserTagAffinity.objects.get(user=self.user, tag_id=option_tag.tag_id)
            self.assertAlmostEqual(row.weight, option_tag.weight * 0.5)

        # دوباره یاد گرفتن، upsert است نه ردیف جدید
        engine.learn_from_answers(self.user, [answer])
        first = option.optiontag_set.first()
        row = UserTagAffinity.objects.get(user=self.user, tag_id=first.tag_id)
        self.assertAlmostEqual(row.weight, first.weight * 1.0)
        self.assertEqual(
            UserTagAffinity.objects.filter(user=self.user, tag_id=first.tag_id).count(), 1
        )

    def test_daily_answers_learn_with_quarter_weight_and_free_text_has_none(self):
        question = Question.objects.filter(scope=Question.DAILY).first()
        option = question.options.exclude(optiontag=None).first()
        rows = [
            Answer(user=self.user, question=question, option=option, date=self.today),
            Answer(user=self.user, question=question, option=None, free_text="یه چیز دیگه", date=self.today),
        ]
        deltas = engine.learn_from_answers(self.user, rows)
        tag = option.optiontag_set.first()
        self.assertAlmostEqual(deltas[tag.tag_id], tag.weight * 0.25)
        # پاسخ آزاد هیچ تگی اضافه نکرده
        self.assertEqual(set(deltas), {t.tag_id for t in option.optiontag_set.all()})

    def test_rebuild_affinity_keeps_learned_answers(self):
        """بازسازی کامل (بعد از بازخورد) همان وزن‌های افزایشی را برمی‌گرداند."""
        question = Question.objects.filter(scope=Question.PROFILE).first()
        answer, option = self._profile_answer(question)
        Answer.objects.bulk_create([answer])
        engine.learn_from_answers(self.user, [answer])
        before = dict(UserTagAffinity.objects.filter(user=self.user).values_list("tag_id", "weight"))

        engine.rebuild_affinity(self.user)
        after = dict(UserTagAffinity.objects.filter(user=self.user).values_list("tag_id", "weight"))
        self.assertEqual(before, after)

    def test_mood_history_vector_decays_and_excludes_today(self):
        calm, sad = Mood.objects.get(name="آرام"), Mood.objects.get(name="غمگین")
        MoodEntry.objects.create(user=self.user, date=self.today, mood=sad)
        MoodEntry.objects.create(user=self.user, date=self.today - timedelta(days=1), mood=calm)
        MoodEntry.objects.create(user=self.user, date=self.today - timedelta(days=3), mood=calm)
        MoodEntry.objects.create(user=self.user, date=self.today - timedelta(days=9), mood=calm)

        vector = engine.mood_history_vector(self.user, self.today)
        calm_tag = Tag.objects.get(slug="calm")
        weight = engine.mood_vector(calm)[calm_tag.id]
        self.assertAlmostEqual(vector[calm_tag.id], weight * (0.7 ** 1 + 0.7 ** 3))
        # مود امروز (غمگین: hopeful) و مود ۹ روز پیش در تاریخچه نیستند
        self.assertNotIn(Tag.objects.get(slug="hopeful").id, vector)

    def test_mood_layer_uses_history(self):
        """حال‌های قبلی روی «متناسب با حالت» اثر دارند: با تاریخچه‌ی آرام، آیتم آرام بالا می‌آید."""
        calm, focused = Mood.objects.get(name="آرام"), Mood.objects.get(name="متمرکز")
        entry = MoodEntry.objects.create(user=self.user, date=self.today, mood=focused)
        without = [r.item_id for r in engine.build_mood_layer(self.user, entry)]

        for days in (1, 2, 3):
            MoodEntry.objects.create(
                user=self.user, date=self.today - timedelta(days=days), mood=calm
            )
        with_history = [r.item_id for r in engine.build_mood_layer(self.user, entry)]
        self.assertTrue(without and with_history)
        self.assertNotEqual(without, with_history)


class DayLayerTests(TestCase):
    """پیشنهاد روز = شناخت کلی از کاربر + مناسبت روز (تقویم کامل، آیتم تضمینی «به مناسبتِ»)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_base", verbosity=0)
        call_command("import_titles", verbosity=0)

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000040", city=City.objects.get(slug="tehran")
        )
        self.today = date(2026, 9, 3)

    def test_calendar_covers_every_day_of_the_year(self):
        """هر روزِ سال میلادی دست‌کم یک روز جهانی دارد (سال کبیسه، شامل ۲۹ فوریه)."""
        import calendar

        have = set(
            Occasion.objects.filter(calendar=Occasion.GREGORIAN, year__isnull=True)
            .values_list("month", "day")
        )
        for month in range(1, 13):
            for day in range(1, calendar.monthrange(2024, month)[1] + 1):
                self.assertIn((month, day), have, f"{month}/{day} بدون مناسبت")

    def test_first_card_is_linked_to_the_days_occasion(self):
        """آیتم اول «به مناسبتِ» مناسبت اصلی روز است و یکی از تگ‌های مناسبت را دارد."""
        calm = Tag.objects.get(slug="calm")
        _, jm, jd = gregorian_to_jalali(self.today.year, self.today.month, self.today.day)
        occasion = Occasion.objects.create(
            source=Occasion.IRAN, calendar=Occasion.JALALI, month=jm, day=jd,
            title="روز آرامش تست", priority=90,
        )
        occasion.tags.add(calm)

        rows = engine.build_day_layer(self.user, self.today)
        self.assertEqual(rows[0].occasion_id, occasion.id)
        self.assertTrue(rows[0].item.tags.filter(id=calm.id).exists())
        self.assertTrue(all(row.occasion_id is None for row in rows[1:]))

    def test_occasion_pick_follows_user_taste(self):
        """بین آیتم‌های مرتبط با مناسبت، سلیقه‌ی کاربر تصمیم می‌گیرد."""
        _, jm, jd = gregorian_to_jalali(self.today.year, self.today.month, self.today.day)
        occasion = Occasion.objects.create(
            source=Occasion.IRAN, calendar=Occasion.JALALI, month=jm, day=jd,
            title="روز کتاب تست", priority=90,
        )
        occasion.tags.add(Tag.objects.get(slug="thoughtful"))

        # کاربری که عاشق چیزهای خنده‌دار است
        UserTagAffinity.objects.create(user=self.user, tag=Tag.objects.get(slug="funny"), weight=6.0)
        rows = engine.build_day_layer(self.user, self.today)
        first = rows[0].item
        self.assertTrue(first.tags.filter(slug="thoughtful").exists())
        # بین thoughtful ها، یک آیتم funny اگر باشد بالاتر است
        funny_and_thoughtful = engine.candidate_items(self.user, self.today).filter(
            tags__slug="thoughtful"
        ).filter(tags__slug="funny").exists()
        if funny_and_thoughtful:
            self.assertTrue(first.tags.filter(slug="funny").exists())

    def test_without_any_occasion_day_layer_is_profile_only(self):
        Occasion.objects.all().delete()
        UserTagAffinity.objects.create(user=self.user, tag=Tag.objects.get(slug="calm"), weight=5.0)
        rows = engine.build_day_layer(self.user, self.today)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row.occasion_id is None for row in rows))


class NeedSlotTests(TestCase):
    """«متناسب با حالت» پویا: ۳ پایه + یک اسلات تضمینی برای هر نیاز امروز."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_base", verbosity=0)
        call_command("import_titles", verbosity=0)

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09120000030", city=City.objects.get(slug="tehran")
        )
        self.today = date(2026, 9, 3)

    def _entry(self, name):
        return MoodEntry.objects.create(
            user=self.user, date=self.today, mood=Mood.objects.get(name=name)
        )

    def _answer(self, question_text, option_text):
        question = Question.objects.get(scope=Question.DAILY, text=question_text)
        option = question.options.get(text=option_text)
        Answer.objects.create(user=self.user, question=question, option=option, date=self.today)

    def test_no_needs_keeps_three(self):
        entry = self._entry("خسته")  # نه بیرون، نه سرگرمی، نه وقت زیاد
        self.assertEqual(engine.today_needs(self.user, entry), [])
        self.assertEqual(len(engine.build_mood_layer(self.user, entry)), 3)

    def test_wanting_out_adds_a_place_or_gathering(self):
        entry = self._entry("سرحال")  # social + outdoor
        self.assertIn("company", engine.today_needs(self.user, entry))
        rows = engine.build_mood_layer(self.user, entry)
        self.assertGreaterEqual(len(rows), 4)
        first = rows[0].item
        self.assertTrue(
            first.category.needs_city
            or first.tags.filter(slug__in=engine.COMPANY_TAG_SLUGS).exists()
        )

    def test_no_place_for_unsupported_city(self):
        self.user.city = City.objects.get(slug="mashhad")
        self.user.save()
        entry = self._entry("سرحال")
        self.assertNotIn("company", engine.today_needs(self.user, entry))

    def test_wanting_fun_adds_a_film_or_series(self):
        entry = self._entry("بی‌حوصله")  # escape
        self.assertIn("screen", engine.today_needs(self.user, entry))
        rows = engine.build_mood_layer(self.user, entry)
        slugs = [row.item.category.slug for row in rows]
        self.assertTrue(set(slugs) & set(engine.SCREEN_CATEGORY_SLUGS))

    def test_answers_change_needs_and_count(self):
        """جواب‌های روز مستقیماً روی نیازها و تعداد اثر دارند."""
        entry = self._entry("خسته")
        self._answer("چقدر وقت داری؟", "امروز آزادم")
        self._answer("خونه‌ای یا بیرون؟", "بیرون می‌رم")
        needs = engine.today_needs(self.user, entry)
        self.assertIn("more", needs)
        self.assertIn("company", needs)
        rows = engine.build_mood_layer(self.user, entry)
        self.assertEqual(len(rows), 3 + len(needs))

    def test_short_time_blocks_film(self):
        entry = self._entry("بی‌حوصله")
        self._answer("چقدر وقت داری؟", "یه ربع")  # long منفی
        self.assertNotIn("screen", engine.today_needs(self.user, entry))

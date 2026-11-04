from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import City, OTPCode, User
from content.models import Category, Item
from journey.models import Answer, Mood, MoodEntry, Question, UserItemStatus


class ApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_base", verbosity=0)

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="09120000000",
            display_name="سارا",
            city=City.objects.get(slug="tehran"),
            onboarding_done=True,
        )
        self.client.force_authenticate(self.user)


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_login_then_verify_returns_tokens(self):
        response = self.client.post("/api/auth/login/", {"phone": "۰۹۱۲۱۱۱۲۲۳۳"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["phone"], "09121112233")

        code = OTPCode.objects.get(phone="09121112233", is_used=False).code
        self.assertEqual(response.data["dev_code"], code)

        response = self.client.post(
            "/api/auth/verify/", {"phone": "09121112233", "code": code}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertFalse(response.data["onboarding_done"])
        self.assertTrue(User.objects.filter(phone="09121112233").exists())

    def test_invalid_phone(self):
        response = self.client.post("/api/auth/login/", {"phone": "123"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.data)

    def test_wrong_code_is_counted(self):
        self.client.post("/api/auth/login/", {"phone": "09121112244"}, format="json")
        otp = OTPCode.objects.get(phone="09121112244", is_used=False)
        wrong_code = "000000" if otp.code != "000000" else "111111"

        response = self.client.post(
            "/api/auth/verify/", {"phone": "09121112244", "code": wrong_code}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 1)

    def test_expired_code(self):
        response = self.client.post(
            "/api/auth/verify/", {"phone": "09129999999", "code": "123456"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.data["expired"])

    def test_pages_need_login(self):
        self.assertEqual(self.client.get("/api/today/").status_code, 401)


class TodayTests(ApiTestCase):
    def test_new_user_must_do_onboarding(self):
        self.user.onboarding_done = False
        self.user.save()
        response = self.client.get("/api/today/")
        self.assertTrue(response.data["onboarding_required"])

    def test_today_without_mood(self):
        response = self.client.get("/api/today/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["mood"])
        self.assertEqual(response.data["mood_items"], [])
        self.assertEqual(len(response.data["main_moods"]), 6)
        self.assertTrue(response.data["day_items"])

    def test_set_mood_builds_mood_items(self):
        mood = Mood.objects.first()
        response = self.client.post("/api/mood/", {"mood": mood.id}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ask_questions"])

        response = self.client.get("/api/today/")
        self.assertEqual(response.data["mood"]["id"], mood.id)
        self.assertTrue(response.data["mood_items"])

    def test_done_item_is_marked_and_skipped_item_is_hidden(self):
        rows = self.client.get("/api/today/").data["day_items"]
        done_id = rows[0]["item"]["id"]
        skipped_id = rows[1]["item"]["id"]
        self.client.post(f"/api/items/{done_id}/action/", {"action": "done"}, format="json")
        self.client.post(f"/api/items/{skipped_id}/action/", {"action": "skip"}, format="json")

        rows = self.client.get("/api/today/").data["day_items"]
        ids = [row["item"]["id"] for row in rows]
        self.assertNotIn(skipped_id, ids)
        self.assertTrue(next(row for row in rows if row["item"]["id"] == done_id)["is_done"])

    def test_daily_questions_need_mood(self):
        self.assertEqual(self.client.get("/api/daily-questions/").status_code, 404)

    def test_daily_questions_are_saved(self):
        self.client.post("/api/mood/", {"mood": Mood.objects.first().id}, format="json")
        data = self.client.get("/api/daily-questions/").data
        question = data["boxes"][0]["questions"][0]
        option = question["options"][0]

        response = self.client.post(
            "/api/daily-questions/",
            {"answers": {str(question["id"]): {"options": [option["id"]]}}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Answer.objects.filter(user=self.user, option_id=option["id"]).exists()
        )
        self.assertTrue(self.client.get("/api/today/").data["answered_daily"])


class OnboardingTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user.onboarding_done = False
        self.user.save()

    def full_answers(self):
        answers = {}
        for question in Question.objects.filter(scope=Question.ONBOARDING, is_active=True):
            answers[str(question.id)] = {"options": [question.options.first().id]}
        return answers

    def test_incomplete_answers_do_not_finish(self):
        response = self.client.post("/api/onboarding/", {"answers": {}}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing_question", response.data)
        self.user.refresh_from_db()
        self.assertFalse(self.user.onboarding_done)

    def test_complete_answers_finish_and_save_name(self):
        response = self.client.post(
            "/api/onboarding/",
            {"display_name": "علی", "city": "", "answers": self.full_answers()},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.onboarding_done)
        self.assertEqual(self.user.display_name, "علی")
        self.assertIsNone(self.user.city)

    def test_other_answer_is_saved_as_free_text(self):
        question = Question.objects.filter(
            scope=Question.ONBOARDING, is_active=True, allows_other=True
        ).first()
        if question is None:
            self.skipTest("no question with other option")
        answers = self.full_answers()
        answers[str(question.id)] = {"options": [], "other": "متن آزاد"}
        response = self.client.post("/api/onboarding/", {"answers": answers}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Answer.objects.filter(question=question, option=None, free_text="متن آزاد").exists()
        )

    def test_finished_user_gets_done(self):
        self.user.onboarding_done = True
        self.user.save()
        self.assertTrue(self.client.get("/api/onboarding/").data["done"])


class CalendarTests(ApiTestCase):
    def test_calendar_shows_saved_mood(self):
        self.client.post("/api/mood/", {"mood": Mood.objects.first().id}, format="json")
        response = self.client.get("/api/calendar/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["balls"]), 1)
        self.assertEqual(response.data["dominant"]["id"], Mood.objects.first().id)
        today_cells = [day for day in response.data["days"] if day["is_today"]]
        self.assertEqual(today_cells[0]["mood"]["id"], Mood.objects.first().id)

    def test_month_navigation_wraps_year(self):
        response = self.client.get("/api/calendar/?y=1405&m=1")
        self.assertEqual(response.data["previous"], {"y": 1404, "m": 12})
        response = self.client.get("/api/calendar/?y=1405&m=12")
        self.assertEqual(response.data["next"], {"y": 1406, "m": 1})

    def test_bad_month_uses_current(self):
        self.assertEqual(self.client.get("/api/calendar/?m=abc").status_code, 200)


class CatalogTests(ApiTestCase):
    def test_city_gate_on_categories(self):
        slugs = [row["slug"] for row in self.client.get("/api/categories/").data["categories"]]
        self.assertIn("cafe", slugs)

        self.user.city = None
        self.user.save()
        slugs = [row["slug"] for row in self.client.get("/api/categories/").data["categories"]]
        self.assertNotIn("cafe", slugs)
        self.assertEqual(self.client.get("/api/categories/cafe/").status_code, 404)

    def test_category_detail_and_item(self):
        category = Category.objects.filter(needs_city=False, items__isnull=False).first()
        response = self.client.get(f"/api/categories/{category.slug}/")
        self.assertEqual(response.status_code, 200)
        item_id = response.data["items"][0]["id"]
        response = self.client.get(f"/api/items/{item_id}/")
        self.assertEqual(response.data["category"]["slug"], category.slug)
        self.assertIn("tags", response.data)

    def test_item_actions(self):
        item = Item.objects.filter(category__is_serial=False).first()
        response = self.client.post(
            f"/api/items/{item.id}/action/", {"action": "done", "rating": 5}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        row = UserItemStatus.objects.get(user=self.user, item=item)
        self.assertEqual(row.status, UserItemStatus.DONE)
        self.assertEqual(row.rating, 5)

        response = self.client.post(
            f"/api/items/{item.id}/action/", {"action": "progress"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(f"/api/items/{item.id}/action/", {"action": "x"}, format="json")
        self.assertEqual(response.status_code, 400)


class ProfileTests(ApiTestCase):
    def test_update_name_and_city(self):
        city = City.objects.exclude(slug="tehran").first()
        response = self.client.patch(
            "/api/profile/", {"display_name": "نیما", "city": city.id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "نیما")
        self.assertEqual(self.user.city, city)

    def test_profile_question_is_saved_and_shown(self):
        question = Question.objects.filter(scope=Question.PROFILE, is_active=True).first()
        option = question.options.first()
        response = self.client.post(
            f"/api/profile/questions/{question.id}/", {"options": [option.id]}, format="json"
        )
        self.assertEqual(response.status_code, 200)

        data = self.client.get("/api/profile/").data
        row = next(row for row in data["questions"] if row["id"] == question.id)
        self.assertEqual(row["selected"], [option.id])
        self.assertEqual(row["answered"], [option.text])

    def test_empty_profile_question_is_rejected(self):
        question = Question.objects.filter(scope=Question.PROFILE, is_active=True).first()
        response = self.client.post(
            f"/api/profile/questions/{question.id}/", {"options": []}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_skipped_items_are_listed(self):
        item = Item.objects.first()
        self.client.post(f"/api/items/{item.id}/action/", {"action": "skip"}, format="json")
        data = self.client.get("/api/profile/").data
        self.assertEqual(data["skipped"][0]["id"], item.id)

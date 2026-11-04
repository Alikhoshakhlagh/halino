from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import auth, calendar, catalog, profile, questions, today

urlpatterns = [
    path("auth/login/", auth.login_view),
    path("auth/verify/", auth.verify_view),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
    path("today/", today.today_view),
    path("mood/", today.set_mood_view),
    path("onboarding/", questions.onboarding_view),
    path("daily-questions/", questions.daily_questions_view),
    path("calendar/", calendar.calendar_view),
    path("categories/", catalog.category_list_view),
    path("categories/<slug:slug>/", catalog.category_detail_view),
    path("items/<int:pk>/", catalog.item_detail_view),
    path("items/<int:pk>/action/", catalog.item_action_view),
    path("profile/", profile.profile_view),
    path("profile/questions/<int:pk>/", profile.profile_question_view),
]

from django.urls import path

from . import views

urlpatterns = [
    path("", views.today_view, name="today"),
    path("onboarding/", views.onboarding_view, name="onboarding"),
    path("mood/", views.set_mood_view, name="set_mood"),
    path("daily-questions/", views.daily_questions_view, name="daily_questions"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("categories/", views.category_list_view, name="category_list"),
    path("categories/<slug:slug>/", views.category_detail_view, name="category_detail"),
    path("item/<int:pk>/", views.item_detail_view, name="item_detail"),
    path("item/<int:pk>/action/", views.item_action_view, name="item_action"),
    path("profile/", views.profile_view, name="profile"),
]

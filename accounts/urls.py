from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_view, name="verify"),
    path("logout/", views.logout_view, name="logout"),
]

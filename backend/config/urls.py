from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("auth/", include("accounts.urls")),
    path("", include("journey.urls")),
]

admin.site.site_header = "پنل مدیریت حالینو"
admin.site.site_title = "حالینو"
admin.site.index_title = "مدیریت محتوا و کاربران"

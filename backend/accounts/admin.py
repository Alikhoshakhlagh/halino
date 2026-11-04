from django.contrib import admin

from .models import City, OTPCode, User


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_supported")
    list_filter = ("is_supported",)
    list_editable = ("is_supported",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("phone", "display_name", "city", "onboarding_done", "date_joined")
    list_filter = ("onboarding_done", "city", "is_staff")
    search_fields = ("phone", "display_name")
    readonly_fields = ("date_joined", "last_login")
    fieldsets = (
        (None, {"fields": ("phone", "display_name", "city")}),
        ("وضعیت", {"fields": ("onboarding_done", "is_active", "is_staff", "is_superuser")}),
        ("تاریخ‌ها", {"fields": ("date_joined", "last_login")}),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "created_at", "expires_at", "attempts", "is_used")
    list_filter = ("is_used",)
    search_fields = ("phone",)

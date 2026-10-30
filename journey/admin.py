from django.contrib import admin

from .models import (
    Answer,
    DailyRecommendation,
    Mood,
    MoodEntry,
    MoodTag,
    Question,
    QuestionOption,
    OptionTag,
    UserItemStatus,
    UserTagAffinity,
)


class MoodTagInline(admin.TabularInline):
    model = MoodTag
    extra = 3
    autocomplete_fields = ("tag",)


@admin.register(Mood)
class MoodAdmin(admin.ModelAdmin):
    list_display = ("__str__", "face", "energy", "valence", "color", "order")
    list_editable = ("face", "energy", "valence", "order")
    inlines = [MoodTagInline]


@admin.register(MoodEntry)
class MoodEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "mood", "note")
    list_filter = ("mood", "date")
    search_fields = ("user__phone", "user__display_name")
    autocomplete_fields = ("user",)


class OptionTagInline(admin.TabularInline):
    model = OptionTag
    extra = 2
    autocomplete_fields = ("tag",)


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 3
    show_change_link = True


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "scope", "kind", "order", "is_active")
    list_filter = ("scope", "kind", "is_active")
    list_editable = ("order", "is_active")
    inlines = [QuestionOptionInline]


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ("text", "question", "order")
    list_filter = ("question__scope",)
    search_fields = ("text",)
    inlines = [OptionTagInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "option", "date")
    list_filter = ("question__scope", "date")
    autocomplete_fields = ("user",)


@admin.register(UserTagAffinity)
class UserTagAffinityAdmin(admin.ModelAdmin):
    list_display = ("user", "tag", "weight", "updated_at")
    list_filter = ("tag",)
    autocomplete_fields = ("user", "tag")


@admin.register(UserItemStatus)
class UserItemStatusAdmin(admin.ModelAdmin):
    list_display = ("user", "item", "status", "rating", "updated_at")
    list_filter = ("status", "item__category")
    autocomplete_fields = ("user", "item")


@admin.register(DailyRecommendation)
class DailyRecommendationAdmin(admin.ModelAdmin):
    """برای دیباگ موتور: می‌شود دید هر روز چه چیزی با چه امتیازی پیشنهاد شده."""

    list_display = ("user", "date", "item", "source", "position", "score", "occasion")
    list_filter = ("source", "date", "item__category")
    autocomplete_fields = ("user", "item")
    date_hierarchy = "date"

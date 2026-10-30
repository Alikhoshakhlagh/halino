from django.contrib import admin

from .models import Category, Item, ItemTag, Occasion, Tag


class ItemTagInline(admin.TabularInline):
    model = ItemTag
    extra = 3
    autocomplete_fields = ("tag",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "item_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="تعداد آیتم")
    def item_count(self, obj):
        return obj.items.count()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "color", "order", "is_serial", "needs_city", "item_count")
    list_editable = ("icon", "color", "order", "is_serial", "needs_city")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="تعداد آیتم")
    def item_count(self, obj):
        return obj.items.count()


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "city", "tag_list", "is_active")
    list_filter = ("category", "is_active", "city")
    search_fields = ("title", "subtitle", "description")
    list_editable = ("is_active",)
    inlines = [ItemTagInline]
    autocomplete_fields = ("city",)
    list_per_page = 50

    @admin.display(description="تگ‌ها")
    def tag_list(self, obj):
        return "، ".join(t.name for t in obj.tags.all()[:5])

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")


@admin.register(Occasion)
class OccasionAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "calendar", "month", "day", "year", "priority", "is_active")
    list_filter = ("source", "calendar", "is_active", "month")
    list_editable = ("priority", "is_active")
    search_fields = ("title", "quote")
    filter_horizontal = ("tags", "pinned_items")
    fieldsets = (
        (None, {"fields": ("title", "source", "is_active", "priority")}),
        (
            "تاریخ",
            {
                "fields": ("calendar", "month", "day", "year"),
                "description": "ماه و روز در همان تقویمی که انتخاب کرده‌ای. "
                "سال را فقط برای یک مناسبت یک‌باره پر کن.",
            },
        ),
        ("محتوا", {"fields": ("quote", "quote_author", "tags", "pinned_items")}),
    )

"""
وارد کردن فهرست فیلم و سریال از یک فایل JSON و تگ‌زدن خودکار بر اساس ژانر.

    python manage.py import_titles
    python manage.py import_titles --file mylist.json --clear

قالب هر ردیف:  {"t": "عنوان", "y": 1994, "k": "film|series", "g": ["drama", ...]}

اگر بعداً خواستی فهرست را عوض کنی، فقط فایل JSON را عوض کن — کد دست نمی‌خورد.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from content.models import Category, Item, ItemTag, Tag
from content.taxonomy import GENRE_TAGS, KIND_TAGS, TAGS

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "fixtures" / "top_titles.json"

CATEGORY_FOR_KIND = {
    "film": ("فیلم", "film", "", "#7C5CFF"),
    "series": ("سریال", "series", "", "#4CC9F0"),
}


class Command(BaseCommand):
    help = "وارد کردن فهرست برتر فیلم و سریال و تگ‌زدن خودکار"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_FILE))
        parser.add_argument(
            "--clear",
            action="store_true",
            help="اول همه آیتم‌های دسته فیلم و سریال را پاک کن",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            self.stderr.write(f"فایل پیدا نشد: {path}")
            return

        rows = json.loads(path.read_text(encoding="utf-8"))

        tags = {}
        for slug, name in TAGS.items():
            tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
            tags[slug] = tag

        categories = {}
        for kind, (name, slug, icon, color) in CATEGORY_FOR_KIND.items():
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "icon": icon,
                    "color": color,
                    # سریال دنباله‌دار است: تا یکی تمام نشده، سریال جدید پیشنهاد نمی‌شود
                    "is_serial": kind == "series",
                    "order": 1 if kind == "film" else 2,
                },
            )
            categories[kind] = category

        if options["clear"]:
            Item.objects.filter(category__in=categories.values()).delete()

        created = updated = 0
        for row in rows:
            kind = row.get("k", "film")
            category = categories.get(kind)
            if category is None:
                continue

            item, was_created = Item.objects.update_or_create(
                category=category,
                title=row["t"],
                defaults={
                    "subtitle": str(row.get("y", "")),
                    "meta": {"year": row.get("y"), "genres": row.get("g", [])},
                    "is_active": True,
                },
            )
            created += was_created
            updated += not was_created

            weights = dict(KIND_TAGS.get(kind, {}))
            for genre in row.get("g", []):
                for slug, weight in GENRE_TAGS.get(genre, {}).items():
                    weights[slug] = max(weights.get(slug, 0), weight)

            ItemTag.objects.filter(item=item).delete()
            ItemTag.objects.bulk_create(
                [
                    ItemTag(item=item, tag=tags[slug], weight=weight)
                    for slug, weight in weights.items()
                    if slug in tags
                ]
            )

        if options.get("verbosity", 1):
            self.stdout.write(
                self.style.SUCCESS(
                    f"{created} آیتم جدید، {updated} آیتم به‌روزرسانی شد. "
                    f"مجموع: {Item.objects.filter(category__in=categories.values()).count()}"
                )
            )

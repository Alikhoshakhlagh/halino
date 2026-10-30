"""
پر کردن یک ماه شمسی با مود تصادفی — فقط برای دمو و ارائه.

    python manage.py demo_moods 09121234567
    python manage.py demo_moods 09121234567 --year 1405 --month 5 --fill 80

هیچ‌جای منطق محصول از این استفاده نمی‌کند؛ صرفاً برای اینکه صفحه تقویم
موقع ارائه خالی نباشد.
"""

import random
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from journey.jalali import jalali_month_length, jalali_to_gregorian, to_jalali
from journey.models import Mood, MoodEntry


class Command(BaseCommand):
    help = "ساخت مود تصادفی برای یک ماه (فقط دمو)"

    def add_arguments(self, parser):
        parser.add_argument("phone")
        parser.add_argument("--year", type=int)
        parser.add_argument("--month", type=int)
        parser.add_argument("--fill", type=int, default=75, help="درصد روزهای پرشده")
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        user = User.objects.filter(phone=options["phone"]).first()
        if user is None:
            self.stderr.write(f"کاربری با شماره {options['phone']} پیدا نشد.")
            return

        today = timezone.localdate()
        jy_now, jm_now, _ = to_jalali(today)
        jy = options["year"] or jy_now
        jm = options["month"] or jm_now
        length = jalali_month_length(jy, jm)

        moods = list(Mood.objects.all())
        if not moods:
            self.stderr.write("اول seed_base را اجرا کن.")
            return

        # وزن‌دهی تا نتیجه شبیه یک ماه واقعی باشد، نه نویز یکنواخت
        weights = [4 if m.valence > 0 else 3 if m.valence == 0 else 2 for m in moods]

        first = date(*jalali_to_gregorian(jy, jm, 1))
        last = date(*jalali_to_gregorian(jy, jm, length))
        if options["clear"]:
            MoodEntry.objects.filter(user=user, date__gte=first, date__lte=last).delete()

        rng = random.Random(f"demo-{user.pk}-{jy}-{jm}")
        created = 0
        for day in range(1, length + 1):
            gdate = date(*jalali_to_gregorian(jy, jm, day))
            if gdate > today:
                break
            if rng.randint(1, 100) > options["fill"]:
                continue
            _, made = MoodEntry.objects.get_or_create(
                user=user, date=gdate, defaults={"mood": rng.choices(moods, weights)[0]}
            )
            created += made

        self.stdout.write(
            self.style.SUCCESS(f"{created} روز مود ساخته شد برای {jy}/{jm}.")
        )

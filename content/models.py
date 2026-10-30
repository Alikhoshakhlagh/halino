from django.core.exceptions import ValidationError
from django.db import models


class Tag(models.Model):
    """
    فضای معنایی مشترک بین آیتم، مود و پاسخ سؤال‌ها.
    موتور پیشنهاد فقط با همین جدول کار می‌کند — دسته‌بندی نقشی در تطبیق ندارد.
    """

    name = models.CharField("تگ", max_length=48, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = "تگ"
        verbose_name_plural = "تگ‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField("دسته", max_length=48, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField("آیکون", max_length=32, blank=True)
    # رنگ دسته در UI — کارت‌ها، تایل‌ها و نوار کناری از همین می‌آید
    color = models.CharField("رنگ", max_length=9, default="#7C5CFF")
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    # مصرفش طول می‌کشد (کتاب، سریال، دوره): تا تمام نشده، آیتم جدید پیشنهاد نمی‌شود
    is_serial = models.BooleanField("دنباله‌دار", default=False)
    # فقط برای شهرهای پشتیبانی‌شده فعال است (کافه، پارک، مکان گردشگری)
    needs_city = models.BooleanField("وابسته به شهر", default=False)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Item(models.Model):
    """هر چیزی که پیشنهاد می‌شود: فیلم، سریال، کتاب، پادکست، کافه، ورزش، نوشتن…"""

    category = models.ForeignKey(
        Category, verbose_name="دسته", related_name="items", on_delete=models.PROTECT
    )
    title = models.CharField("عنوان", max_length=160)
    subtitle = models.CharField("زیرعنوان", max_length=160, blank=True)
    description = models.TextField("توضیح", blank=True)
    image_url = models.URLField("تصویر", blank=True)
    external_url = models.URLField("لینک بیرونی", blank=True)

    city = models.ForeignKey(
        "accounts.City",
        verbose_name="شهر",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    duration_minutes = models.PositiveIntegerField("مدت (دقیقه)", null=True, blank=True)

    # سال، کارگردان، نویسنده و هر چیز خاصِ دسته
    meta = models.JSONField("اطلاعات تکمیلی", default=dict, blank=True)

    tags = models.ManyToManyField(Tag, through="ItemTag", related_name="items")
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "آیتم"
        verbose_name_plural = "آیتم‌ها"
        indexes = [models.Index(fields=["category", "is_active"])]
        ordering = ["category__order", "title"]

    def clean(self):
        if self.category_id and self.category.needs_city and not self.city_id:
            raise ValidationError({"city": "برای این دسته، شهر الزامی است."})

    def __str__(self):
        year = self.meta.get("year") if isinstance(self.meta, dict) else None
        return f"{self.title} ({year})" if year else self.title


class ItemTag(models.Model):
    item = models.ForeignKey(Item, verbose_name="آیتم", on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, verbose_name="تگ", on_delete=models.CASCADE)
    weight = models.PositiveSmallIntegerField("وزن", default=1)  # ۱ تا ۵

    class Meta:
        verbose_name = "تگ آیتم"
        verbose_name_plural = "تگ‌های آیتم"
        unique_together = ("item", "tag")

    def __str__(self):
        return f"{self.item_id} — {self.tag}"


class Occasion(models.Model):
    """
    مناسبت روز — پشتوانه «پیشنهاد روز».

    سه منبع دارد:
      ۱. تقویم ایرانی (شمسی) — نوروز، سیزده‌بدر، شب یلدا…
      ۲. روزهای جهانی (میلادی) — از nationaldaycalendar.com
      ۳. دستور مدیر — مناسبت دلخواه، با امکان قفل‌کردن آیتم‌های مشخص

    مناسبت‌های تکرارشونده سال ندارند. فقط دستور یک‌باره مدیر سال می‌گیرد.
    """

    JALALI, GREGORIAN = "jalali", "gregorian"
    CALENDAR_CHOICES = [(JALALI, "شمسی"), (GREGORIAN, "میلادی")]

    IRAN, NATIONAL, ADMIN = "iran", "national", "admin"
    SOURCE_CHOICES = [
        (IRAN, "تقویم ایرانی"),
        (NATIONAL, "روز جهانی"),
        (ADMIN, "دستور مدیر"),
    ]

    calendar = models.CharField(
        "تقویم", max_length=10, choices=CALENDAR_CHOICES, default=JALALI
    )
    source = models.CharField(
        "منبع", max_length=10, choices=SOURCE_CHOICES, default=IRAN, db_index=True
    )
    month = models.PositiveSmallIntegerField("ماه")
    day = models.PositiveSmallIntegerField("روز")
    # فقط برای دستور یک‌باره مدیر؛ خالی یعنی هر سال تکرار می‌شود
    year = models.PositiveSmallIntegerField("سال (اختیاری)", null=True, blank=True)

    title = models.CharField("عنوان", max_length=120)
    quote = models.TextField("نقل‌قول", blank=True)
    quote_author = models.CharField("گوینده", max_length=80, blank=True)

    tags = models.ManyToManyField(
        Tag, verbose_name="تگ‌ها", blank=True, related_name="occasions"
    )
    # دستور مدیر: این آیتم‌ها حتماً در پیشنهاد روز می‌آیند، بدون امتیازدهی موتور
    pinned_items = models.ManyToManyField(
        Item,
        verbose_name="آیتم‌های قفل‌شده",
        blank=True,
        related_name="pinned_occasions",
    )
    # وقتی چند مناسبت روی یک روز بیفتند، بالاترین اولویت اول نمایش داده می‌شود
    priority = models.SmallIntegerField("اولویت", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "مناسبت"
        verbose_name_plural = "مناسبت‌ها"
        unique_together = ("calendar", "month", "day", "year", "title")
        indexes = [models.Index(fields=["calendar", "month", "day"])]
        ordering = ["-priority", "month", "day"]

    def __str__(self):
        stamp = f"{self.year}/" if self.year else ""
        return f"{stamp}{self.month}/{self.day} — {self.title}"

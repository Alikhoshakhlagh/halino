from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Mood(models.Model):
    """
    مدل ترکیبی: کاربر از یک لیست ثابت انتخاب می‌کند،
    ولی هر مود مختصات عددی خودش را دارد تا نمودار و قوانین موتور عددی بمانند.
    """

    # کدام چهره از اسپرایت SVG برای این مود کشیده شود
    FACE_CHOICES = [
        ("happy", "خندان"),
        ("calm", "آرام"),
        ("focused", "مصمم"),
        ("tired", "چشم‌بسته"),
        ("bored", "بی‌حال"),
        ("longing", "دلتنگ"),
        ("anxious", "نگران"),
        ("sad", "ناراحت"),
        ("angry", "عصبانی"),
    ]

    name = models.CharField("مود", max_length=32, unique=True)
    face = models.CharField("چهره", max_length=16, choices=FACE_CHOICES, default="calm")
    emoji = models.CharField("ایموجی", max_length=8, blank=True)
    color = models.CharField("رنگ", max_length=9, blank=True)  # رنگ خانه تقویم
    energy = models.SmallIntegerField("انرژی")  # -۲ تا +۲
    valence = models.SmallIntegerField("خوشایندی")  # -۲ تا +۲
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    tags = models.ManyToManyField(
        "content.Tag", through="MoodTag", related_name="moods"
    )

    class Meta:
        verbose_name = "مود"
        verbose_name_plural = "مودها"
        ordering = ["order"]

    def __str__(self):
        return f"{self.emoji} {self.name}".strip()


class MoodTag(models.Model):
    mood = models.ForeignKey(Mood, verbose_name="مود", on_delete=models.CASCADE)
    tag = models.ForeignKey("content.Tag", verbose_name="تگ", on_delete=models.CASCADE)
    # وزن منفی یعنی این تگ در این مود سرکوب شود
    weight = models.SmallIntegerField("وزن", default=1)

    class Meta:
        verbose_name = "تگ مود"
        verbose_name_plural = "تگ‌های مود"
        unique_together = ("mood", "tag")


class MoodEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        related_name="mood_entries",
        on_delete=models.CASCADE,
    )
    date = models.DateField("تاریخ")  # میلادی ذخیره، شمسی نمایش
    mood = models.ForeignKey(Mood, verbose_name="مود", on_delete=models.PROTECT)
    note = models.CharField("یادداشت", max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ثبت مود"
        verbose_name_plural = "ثبت مودها"
        unique_together = ("user", "date")  # روزی یک بار، قابل ویرایش
        indexes = [models.Index(fields=["user", "date"])]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user} — {self.date} — {self.mood}"


# سؤال‌های روزانه در «جعبه» نمایش داده می‌شوند: جعبه = دهگانِ order (۰–۹ جعبه‌ی اول،
# ۱۰–۱۹ جعبه‌ی دوم). بدون فیلد جدید؛ سؤال تازه‌ی ادمین با order مناسب خودش جای می‌گیرد.
DAILY_BOX_SPAN = 10
DAILY_BOX_TITLES = ("حال امروزت", "شرایط امروزت")


class Question(models.Model):
    """یک مدل برای هر سه نوع سؤال — فقط scope فرق می‌کند."""

    ONBOARDING, DAILY, PROFILE = "onboarding", "daily", "profile"
    SCOPE_CHOICES = [
        (ONBOARDING, "سؤال اولیه"),
        (DAILY, "سؤال روزانه"),
        (PROFILE, "سؤال پروفایل"),
    ]
    SINGLE, MULTI = "single", "multi"
    KIND_CHOICES = [(SINGLE, "تک‌انتخابی"), (MULTI, "چندانتخابی")]

    scope = models.CharField("نوع", max_length=12, choices=SCOPE_CHOICES, db_index=True)
    kind = models.CharField("حالت", max_length=8, choices=KIND_CHOICES, default=SINGLE)
    text = models.CharField("متن سؤال", max_length=200)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    # چیپ آخر «مورد دیگه…» می‌شود و پاسخ آزاد کاربر در Answer.free_text می‌نشیند
    allows_other = models.BooleanField("گزینه‌ی «مورد دیگه»", default=False)

    class Meta:
        verbose_name = "سؤال"
        verbose_name_plural = "سؤال‌ها"
        ordering = ["scope", "order"]

    def __str__(self):
        return self.text

    @property
    def box(self):
        return self.order // DAILY_BOX_SPAN

    @property
    def box_title(self):
        return DAILY_BOX_TITLES[self.box] if self.box < len(DAILY_BOX_TITLES) else ""


class QuestionOption(models.Model):
    question = models.ForeignKey(
        Question, verbose_name="سؤال", related_name="options", on_delete=models.CASCADE
    )
    text = models.CharField("گزینه", max_length=120)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)
    tags = models.ManyToManyField(
        "content.Tag", through="OptionTag", related_name="options"
    )

    class Meta:
        verbose_name = "گزینه"
        verbose_name_plural = "گزینه‌ها"
        ordering = ["order"]

    def __str__(self):
        return self.text


class OptionTag(models.Model):
    """اینجاست که «تست شخصیت» به چیزی تبدیل می‌شود که موتور می‌تواند بخورد."""

    option = models.ForeignKey(
        QuestionOption, verbose_name="گزینه", on_delete=models.CASCADE
    )
    tag = models.ForeignKey("content.Tag", verbose_name="تگ", on_delete=models.CASCADE)
    weight = models.SmallIntegerField("وزن", default=1)

    class Meta:
        verbose_name = "تگ گزینه"
        verbose_name_plural = "تگ‌های گزینه"
        unique_together = ("option", "tag")


class Answer(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        related_name="answers",
        on_delete=models.CASCADE,
    )
    question = models.ForeignKey(Question, verbose_name="سؤال", on_delete=models.CASCADE)
    # خالی یعنی پاسخ «مورد دیگه» است و متنش در free_text ذخیره شده
    option = models.ForeignKey(
        QuestionOption,
        verbose_name="گزینه",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    free_text = models.CharField("پاسخ آزاد", max_length=120, blank=True)
    date = models.DateField("تاریخ", null=True, blank=True)  # فقط برای سؤال روزانه
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پاسخ"
        verbose_name_plural = "پاسخ‌ها"
        unique_together = ("user", "question", "option", "date")
        indexes = [models.Index(fields=["user", "date"])]


class UserTagAffinity(models.Model):
    """پروفایل قابل‌مصرف موتور. از پاسخ آنبوردینگ ساخته و با بازخورد به‌روز می‌شود."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        related_name="affinities",
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey("content.Tag", verbose_name="تگ", on_delete=models.CASCADE)
    weight = models.FloatField("وزن", default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تمایل کاربر"
        verbose_name_plural = "تمایل‌های کاربر"
        unique_together = ("user", "tag")
        indexes = [models.Index(fields=["user", "-weight"])]

    def __str__(self):
        return f"{self.user} — {self.tag}: {self.weight:.1f}"


class UserItemStatus(models.Model):
    NOT_STARTED, IN_PROGRESS, DONE, SKIPPED = (
        "not_started",
        "in_progress",
        "done",
        "skipped",
    )
    STATUS_CHOICES = [
        (NOT_STARTED, "شروع‌نشده"),
        (IN_PROGRESS, "در حال انجام"),
        (DONE, "تمام‌شده"),
        (SKIPPED, "دیگر پیشنهاد نده"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        related_name="item_statuses",
        on_delete=models.CASCADE,
    )
    item = models.ForeignKey(
        "content.Item",
        verbose_name="آیتم",
        related_name="user_statuses",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        "وضعیت", max_length=16, choices=STATUS_CHOICES, default=NOT_STARTED
    )
    rating = models.PositiveSmallIntegerField("امتیاز", null=True, blank=True)  # ۱ تا ۵
    review_after = models.DateField("یادآوری ریویو", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "وضعیت آیتم کاربر"
        verbose_name_plural = "وضعیت آیتم‌های کاربر"
        unique_together = ("user", "item")
        indexes = [models.Index(fields=["user", "status"])]

    def clean(self):
        # «در حال انجام» فقط برای دسته‌های دنباله‌دار (کتاب/سریال/دوره) معنی دارد.
        # فیلم فقط دیده/ندیده است — بدون ساختن جدول جدا برای هر نوع محتوا.
        if self.status == self.IN_PROGRESS and not self.item.category.is_serial:
            raise ValidationError(
                {"status": "وضعیت «در حال انجام» برای این دسته تعریف نشده است."}
            )

    def __str__(self):
        return f"{self.user} — {self.item} — {self.get_status_display()}"


class DailyRecommendation(models.Model):
    PROFILE, MOOD = "profile", "mood"
    SOURCE_CHOICES = [
        (PROFILE, "پیشنهاد روز — مناسبت و پروفایل"),
        (MOOD, "پیشنهاد حال — مود و سؤال‌های روز"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        related_name="recommendations",
        on_delete=models.CASCADE,
    )
    date = models.DateField("تاریخ")
    item = models.ForeignKey("content.Item", verbose_name="آیتم", on_delete=models.CASCADE)
    source = models.CharField("منبع", max_length=8, choices=SOURCE_CHOICES)
    # فقط برای ردیف‌های لایه دوم پر می‌شود
    mood_entry = models.ForeignKey(
        MoodEntry, verbose_name="مود روز", null=True, blank=True, on_delete=models.SET_NULL
    )
    occasion = models.ForeignKey(
        "content.Occasion",
        verbose_name="مناسبت",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    position = models.PositiveSmallIntegerField("جایگاه", default=0)
    score = models.FloatField("امتیاز موتور", default=0.0)

    class Meta:
        verbose_name = "پیشنهاد روز"
        verbose_name_plural = "پیشنهادهای روز"
        unique_together = ("user", "date", "item")
        indexes = [models.Index(fields=["user", "date", "source"])]
        ordering = ["source", "position"]

    def __str__(self):
        return f"{self.user} — {self.date} — {self.item}"

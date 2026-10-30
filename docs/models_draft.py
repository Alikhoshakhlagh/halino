"""
پیش‌نویس کامل مدل‌های حالینو.
هر بخش داخل فایل models.py اپ خودش می‌رود. اینجا یکجا آمده تا یک‌بار مرور شود.

settings.py:  AUTH_USER_MODEL = "accounts.User"   # قبل از اولین migrate
"""

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ============================================================
# accounts/models.py
# ============================================================

class City(models.Model):
    name = models.CharField("نام شهر", max_length=64, unique=True)
    slug = models.SlugField(unique=True)
    # فقط شهرهای پشتیبانی‌شده دسته‌های مکان‌محور (کافه، پارک) را می‌بینند
    is_supported = models.BooleanField("پشتیبانی‌شده", default=False)

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, phone, **extra):
        if not phone:
            raise ValueError("شماره موبایل الزامی است")
        user = self.model(phone=phone, **extra)
        user.set_unusable_password()  # ورود فقط با OTP
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        user = self.model(phone=phone, **extra)
        user.set_password(password)  # ادمین با رمز وارد می‌شود
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField("موبایل", max_length=15, unique=True)
    display_name = models.CharField("نام نمایشی", max_length=64, blank=True)
    city = models.ForeignKey(
        City, verbose_name="شهر", null=True, blank=True, on_delete=models.SET_NULL
    )
    onboarding_done = models.BooleanField("آنبوردینگ انجام شده", default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return self.display_name or self.phone


class OTPCode(models.Model):
    phone = models.CharField(max_length=15, db_index=True)
    code = models.CharField(max_length=6)  # در نسخه نهایی هش شود
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "کد یک‌بارمصرف"
        indexes = [models.Index(fields=["phone", "is_used"])]

    @property
    def is_valid(self):
        return not self.is_used and self.attempts < 5 and timezone.now() < self.expires_at


# ============================================================
# content/models.py
# ============================================================

class Tag(models.Model):
    """فضای معنایی مشترک بین آیتم، مود و پاسخ سؤال‌ها. قلب موتور پیشنهاد."""

    name = models.CharField("تگ", max_length=48, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = "تگ"
        verbose_name_plural = "تگ‌ها"

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField("دسته", max_length=48, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField("آیکون", max_length=32, blank=True)
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
    """هر چیزی که پیشنهاد می‌شود: فیلم، کتاب، پادکست، مقاله، کافه، فعالیت، تمرین نوشتن."""

    category = models.ForeignKey(Category, related_name="items", on_delete=models.PROTECT)
    title = models.CharField("عنوان", max_length=160)
    subtitle = models.CharField("زیرعنوان", max_length=160, blank=True)
    description = models.TextField("توضیح", blank=True)
    image_url = models.URLField(blank=True)
    external_url = models.URLField("لینک بیرونی", blank=True)

    # فقط برای دسته‌هایی که needs_city دارند
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    duration_minutes = models.PositiveIntegerField("مدت (دقیقه)", null=True, blank=True)

    # سال، کارگردان، نویسنده، امتیاز IMDb و هر چیز خاصِ دسته
    meta = models.JSONField("اطلاعات تکمیلی", default=dict, blank=True)

    tags = models.ManyToManyField(Tag, through="ItemTag", related_name="items")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "آیتم"
        verbose_name_plural = "آیتم‌ها"
        indexes = [models.Index(fields=["category", "is_active"])]

    def clean(self):
        if self.category_id and self.category.needs_city and not self.city_id:
            raise ValidationError({"city": "برای این دسته، شهر الزامی است."})

    def __str__(self):
        return self.title


class ItemTag(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    weight = models.PositiveSmallIntegerField("وزن", default=1)  # 1..5

    class Meta:
        unique_together = ("item", "tag")


class Occasion(models.Model):
    """مناسبت سالانه — سال ذخیره نمی‌شود چون هر سال تکرار می‌شود. ماه/روز شمسی."""

    month = models.PositiveSmallIntegerField("ماه")
    day = models.PositiveSmallIntegerField("روز")
    title = models.CharField("عنوان", max_length=120)
    quote = models.TextField("نقل‌قول", blank=True)
    quote_author = models.CharField("گوینده", max_length=80, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="occasions")

    class Meta:
        verbose_name = "مناسبت"
        verbose_name_plural = "مناسبت‌ها"
        unique_together = ("month", "day", "title")
        indexes = [models.Index(fields=["month", "day"])]

    def __str__(self):
        return f"{self.month}/{self.day} — {self.title}"


# ============================================================
# journey/models.py
# ============================================================

class Mood(models.Model):
    """
    مدل ترکیبی: کاربر از یک لیست ثابت انتخاب می‌کند،
    ولی هر مود مختصات عددی خودش را دارد تا نمودار و قوانین موتور عددی بمانند.
    """

    name = models.CharField("مود", max_length=32, unique=True)
    emoji = models.CharField(max_length=8, blank=True)
    color = models.CharField("رنگ", max_length=9, blank=True)  # رنگ خانه تقویم
    energy = models.SmallIntegerField("انرژی")      # -2 تا +2
    valence = models.SmallIntegerField("خوشایندی")  # -2 تا +2
    order = models.PositiveSmallIntegerField(default=0)

    tags = models.ManyToManyField(Tag, through="MoodTag", related_name="moods")

    class Meta:
        verbose_name = "مود"
        verbose_name_plural = "مودها"
        ordering = ["order"]

    def __str__(self):
        return f"{self.emoji} {self.name}".strip()


class MoodTag(models.Model):
    mood = models.ForeignKey(Mood, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    # وزن منفی یعنی این تگ در این مود سرکوب شود
    weight = models.SmallIntegerField("وزن", default=1)

    class Meta:
        unique_together = ("mood", "tag")


class MoodEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="mood_entries", on_delete=models.CASCADE
    )
    date = models.DateField("تاریخ")  # میلادی ذخیره، شمسی نمایش
    mood = models.ForeignKey(Mood, on_delete=models.PROTECT)
    note = models.CharField("یادداشت", max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ثبت مود"
        verbose_name_plural = "ثبت مودها"
        unique_together = ("user", "date")  # روزی یک بار، قابل ویرایش
        indexes = [models.Index(fields=["user", "date"])]


class Question(models.Model):
    """یک مدل برای هر دو نوع سؤال — فقط scope فرق می‌کند."""

    ONBOARDING, DAILY = "onboarding", "daily"
    SCOPE_CHOICES = [(ONBOARDING, "سؤال اولیه"), (DAILY, "سؤال روزانه")]
    SINGLE, MULTI = "single", "multi"
    KIND_CHOICES = [(SINGLE, "تک‌انتخابی"), (MULTI, "چندانتخابی")]

    scope = models.CharField(max_length=12, choices=SCOPE_CHOICES, db_index=True)
    kind = models.CharField(max_length=8, choices=KIND_CHOICES, default=SINGLE)
    text = models.CharField("متن سؤال", max_length=200)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "سؤال"
        verbose_name_plural = "سؤال‌ها"
        ordering = ["scope", "order"]

    def __str__(self):
        return self.text


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, related_name="options", on_delete=models.CASCADE)
    text = models.CharField("گزینه", max_length=120)
    order = models.PositiveSmallIntegerField(default=0)
    tags = models.ManyToManyField(Tag, through="OptionTag", related_name="options")

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text


class OptionTag(models.Model):
    """اینجاست که «تست شخصیت» به چیزی تبدیل می‌شود که موتور می‌تواند بخورد."""

    option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    weight = models.SmallIntegerField(default=1)

    class Meta:
        unique_together = ("option", "tag")


class Answer(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="answers", on_delete=models.CASCADE
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)  # فقط برای سؤال‌های روزانه
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پاسخ"
        unique_together = ("user", "question", "option", "date")
        indexes = [models.Index(fields=["user", "date"])]


class UserTagAffinity(models.Model):
    """پروفایل قابل‌مصرف موتور. از پاسخ آنبوردینگ ساخته و با بازخورد به‌روز می‌شود."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="affinities", on_delete=models.CASCADE
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    weight = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تمایل کاربر"
        unique_together = ("user", "tag")
        indexes = [models.Index(fields=["user", "-weight"])]


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
        settings.AUTH_USER_MODEL, related_name="item_statuses", on_delete=models.CASCADE
    )
    item = models.ForeignKey(Item, related_name="user_statuses", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=NOT_STARTED)
    rating = models.PositiveSmallIntegerField("امتیاز", null=True, blank=True)  # 1..5
    review_after = models.DateField("یادآوری ریویو", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "وضعیت آیتم کاربر"
        unique_together = ("user", "item")
        indexes = [models.Index(fields=["user", "status"])]

    def clean(self):
        # «در حال انجام» فقط برای دسته‌های دنباله‌دار (کتاب/سریال/دوره) معنی دارد.
        # فیلم فقط دیده/ندیده است — بدون ساختن جدول جدا.
        if self.status == self.IN_PROGRESS and not self.item.category.is_serial:
            raise ValidationError(
                {"status": "وضعیت «در حال انجام» برای این دسته تعریف نشده است."}
            )


class DailyRecommendation(models.Model):
    PROFILE, MOOD = "profile", "mood"
    SOURCE_CHOICES = [
        (PROFILE, "لایه اول — بر اساس پروفایل"),
        (MOOD, "لایه دوم — بر اساس مود"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="recommendations", on_delete=models.CASCADE
    )
    date = models.DateField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    source = models.CharField(max_length=8, choices=SOURCE_CHOICES)
    # فقط برای ردیف‌های لایه دوم پر می‌شود
    mood_entry = models.ForeignKey(
        MoodEntry, null=True, blank=True, on_delete=models.SET_NULL
    )
    occasion = models.ForeignKey(
        "content.Occasion", null=True, blank=True, on_delete=models.SET_NULL
    )
    position = models.PositiveSmallIntegerField(default=0)
    score = models.FloatField(default=0.0)  # برای دیباگ موتور

    class Meta:
        verbose_name = "پیشنهاد روز"
        verbose_name_plural = "پیشنهادهای روز"
        unique_together = ("user", "date", "item")
        indexes = [models.Index(fields=["user", "date", "source"])]
        ordering = ["source", "position"]

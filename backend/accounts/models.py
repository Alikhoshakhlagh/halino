import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class City(models.Model):
    name = models.CharField("نام شهر", max_length=64, unique=True)
    slug = models.SlugField(unique=True)
    # فقط شهرهای پشتیبانی‌شده دسته‌های مکان‌محور (کافه، پارک) را می‌بینند
    is_supported = models.BooleanField("پشتیبانی‌شده", default=False)

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"
        ordering = ["-is_supported", "name"]

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, phone, **extra):
        if not phone:
            raise ValueError("شماره موبایل الزامی است")
        user = self.model(phone=phone, **extra)
        user.set_unusable_password()  # ورود کاربر عادی فقط با OTP است
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra):
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
    is_active = models.BooleanField("فعال", default=True)
    is_staff = models.BooleanField("دسترسی ادمین", default=False)
    date_joined = models.DateTimeField("تاریخ عضویت", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return self.display_name or self.phone

    @property
    def can_see_places(self):
        """گیت شهری: دسته‌های وابسته به شهر فقط برای شهرهای پشتیبانی‌شده باز است."""
        return bool(self.city and self.city.is_supported)


class OTPCode(models.Model):
    phone = models.CharField("موبایل", max_length=15, db_index=True)
    code = models.CharField("کد", max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField("انقضا")
    attempts = models.PositiveSmallIntegerField("تعداد تلاش", default=0)
    is_used = models.BooleanField("مصرف‌شده", default=False)

    class Meta:
        verbose_name = "کد یک‌بارمصرف"
        verbose_name_plural = "کدهای یک‌بارمصرف"
        indexes = [models.Index(fields=["phone", "is_used"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone} — {self.code}"

    @property
    def is_valid(self):
        return (
            not self.is_used
            and self.attempts < settings.HALINO_OTP_MAX_ATTEMPTS
            and timezone.now() < self.expires_at
        )

    @classmethod
    def issue(cls, phone):
        """کد قبلی همان شماره را باطل و یک کد تازه صادر می‌کند."""
        cls.objects.filter(phone=phone, is_used=False).update(is_used=True)
        code = f"{random.randint(0, 999999):06d}"
        return cls.objects.create(
            phone=phone,
            code=code,
            expires_at=timezone.now()
            + timedelta(seconds=settings.HALINO_OTP_TTL_SECONDS),
        )

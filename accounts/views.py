from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import CodeForm, PhoneForm
from .models import OTPCode, User

SESSION_PHONE_KEY = "otp_phone"


def login_view(request):
    """مرحله ۱ — گرفتن شماره. صفحه ثبت‌نام جدا وجود ندارد."""
    if request.user.is_authenticated:
        return redirect("today")

    form = PhoneForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        otp = OTPCode.issue(phone)
        request.session[SESSION_PHONE_KEY] = phone

        if settings.HALINO_OTP_CONSOLE:
            # حالت توسعه: به‌جای پیامک، کد در کنسول و در پیام صفحه نمایش داده می‌شود
            print(f"[OTP] {phone} -> {otp.code}")
            messages.info(request, f"کد تست (حالت توسعه): {otp.code}")

        return redirect("verify")

    # چهره‌های مود برای اسپلش ورود — صرفاً تزئینی
    from journey.models import Mood

    return render(
        request, "accounts/login.html", {"form": form, "moods": Mood.objects.all()}
    )


def verify_view(request):
    """مرحله ۲ — تأیید کد. اینجاست که مسیر کاربر جدید و قدیمی از هم جدا می‌شود."""
    phone = request.session.get(SESSION_PHONE_KEY)
    if not phone:
        return redirect("login")

    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        otp = (
            OTPCode.objects.filter(phone=phone, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if otp is None or not otp.is_valid:
            messages.error(request, "کد منقضی شده است. دوباره تلاش کنید.")
            return redirect("login")

        if otp.code != form.cleaned_data["code"]:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            messages.error(request, "کد وارد شده درست نیست.")
        else:
            otp.is_used = True
            otp.save(update_fields=["is_used"])

            user, created = User.objects.get_or_create(phone=phone)
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
            login(request, user)
            request.session.pop(SESSION_PHONE_KEY, None)

            # کاربر جدید یا کسی که آنبوردینگ را تمام نکرده -> تست اولیه
            if not user.onboarding_done:
                return redirect("onboarding")
            return redirect("today")

    return render(request, "accounts/verify.html", {"form": form, "phone": phone})


def logout_view(request):
    logout(request)
    return redirect("login")

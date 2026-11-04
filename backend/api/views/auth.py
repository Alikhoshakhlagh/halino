from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.forms import CodeForm, PhoneForm, normalize_phone
from accounts.models import OTPCode, User


class RefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except User.DoesNotExist:
            return Response({"detail": "این حساب دیگه وجود نداره."}, status=401)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request):
    form = PhoneForm(request.data)
    if not form.is_valid():
        return Response({"phone": form.errors["phone"]}, status=400)

    phone = form.cleaned_data["phone"]
    otp = OTPCode.issue(phone)
    data = {"phone": phone}
    if settings.HALINO_OTP_CONSOLE:
        print(f"[OTP] {phone} -> {otp.code}")
        data["dev_code"] = otp.code
    return Response(data)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_view(request):
    phone = normalize_phone(str(request.data.get("phone", "")))
    form = CodeForm(request.data)
    if not form.is_valid():
        return Response({"code": form.errors["code"]}, status=400)

    otp = OTPCode.objects.filter(phone=phone, is_used=False).order_by("-created_at").first()
    if otp is None or not otp.is_valid:
        return Response({"detail": "کد منقضی شده است. دوباره تلاش کنید.", "expired": True}, status=400)

    if otp.code != form.cleaned_data["code"]:
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        return Response({"code": ["کد وارد شده درست نیست."]}, status=400)

    otp.is_used = True
    otp.save(update_fields=["is_used"])

    user, _ = User.objects.get_or_create(phone=phone)
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "onboarding_done": user.onboarding_done,
        }
    )

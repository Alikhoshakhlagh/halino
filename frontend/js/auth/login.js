const DECORATIVE_MOODS = [
  { name: "سرحال", face: "happy" },
  { name: "آرام", face: "calm" },
  { name: "دلتنگ", face: "longing" },
  { name: "خسته", face: "tired" },
];

if (isLoggedIn()) {
  window.location.href = "index.html";
}

const form = document.getElementById("login-form");
const phoneInput = document.getElementById("phone");
const phoneError = document.getElementById("phone-error");
const submitButton = form.querySelector("button[type=submit]");

document.getElementById("auth-faces").innerHTML = DECORATIVE_MOODS.map((mood) =>
  createFace(mood)
).join("");

function setPhoneError(message) {
  phoneError.textContent = message;
  phoneInput.classList.toggle("input--invalid", Boolean(message));
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setPhoneError("");
  submitButton.disabled = true;

  try {
    const data = await apiRequest(ENDPOINTS.login, "POST", { phone: phoneInput.value });
    sessionStorage.setItem("otp_phone", data.phone);
    if (data.dev_code) {
      sessionStorage.setItem("otp_dev_code", data.dev_code);
    }
    window.location.href = "verify.html";
  } catch (error) {
    if (error.data && error.data.phone) {
      setPhoneError(error.data.phone[0]);
    } else {
      setPhoneError("ارتباط با سرور برقرار نشد.");
    }
    phoneInput.focus();
    submitButton.disabled = false;
  }
});

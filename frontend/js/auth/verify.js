const phone = sessionStorage.getItem("otp_phone");
if (!phone) {
  window.location.href = "login.html";
}

const form = document.getElementById("verify-form");
const codeInput = document.getElementById("code");
const codeError = document.getElementById("code-error");
const submitButton = form.querySelector("button[type=submit]");
const devCodeBox = document.getElementById("dev-code");

document.getElementById("phone-text").textContent = toFarsiNumber(phone);

const devCode = sessionStorage.getItem("otp_dev_code");
if (devCode) {
  devCodeBox.textContent = `کد تست (حالت توسعه): ${toFarsiNumber(devCode)}`;
  devCodeBox.hidden = false;
}

function setCodeError(message) {
  codeError.textContent = message;
  codeInput.classList.toggle("input--invalid", Boolean(message));
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setCodeError("");
  submitButton.disabled = true;

  try {
    const data = await apiRequest(ENDPOINTS.verify, "POST", { phone, code: codeInput.value });
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    sessionStorage.removeItem("otp_phone");
    sessionStorage.removeItem("otp_dev_code");
    window.location.href = data.onboarding_done ? "index.html" : "onboarding.html";
  } catch (error) {
    if (error.data && error.data.expired) {
      setCodeError(error.data.detail);
    } else if (error.data && error.data.code) {
      setCodeError(error.data.code[0]);
    } else {
      setCodeError("ارتباط با سرور برقرار نشد.");
    }
    codeInput.focus();
    submitButton.disabled = false;
  }
});

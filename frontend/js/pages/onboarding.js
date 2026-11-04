requireLogin();

const form = document.getElementById("onboarding-form");
const stepsBox = document.getElementById("steps-box");
const progressBar = document.getElementById("steps-bar");
const counter = document.getElementById("steps-counter");
const previousButton = document.getElementById("previous-btn");
const nextButton = document.getElementById("next-btn");
const submitButton = document.getElementById("submit-btn");

let questions = [];
let currentStep = 0;

function createCityOptions(cities, selectedCity) {
  return cities
    .map((city) => {
      const note = city.is_supported ? "" : " (پیشنهاد مکان فعلاً فعال نیست)";
      const selected = city.id === selectedCity ? "selected" : "";
      return `<option value="${city.id}" ${selected}>${escapeHtml(city.name)}${note}</option>`;
    })
    .join("");
}

function createNameStep(data) {
  return `
    <section class="step" data-step tabindex="-1">
      <div>
        <h1 class="step__title">بذار بشناسیمت</h1>
        <p class="note">جواب‌های اینجا مشخص می‌کنن چه چیزهایی بهت پیشنهاد بشه. اسم و شهرت رو بعداً از پروفایل هم می‌تونی عوض کنی.</p>
      </div>
      <div class="field">
        <label class="label" for="display-name">اسمت</label>
        <input class="input" id="display-name" maxlength="64" autocomplete="given-name" value="${escapeHtml(data.display_name)}">
      </div>
      <div class="field">
        <label class="label" for="city">شهرت</label>
        <select class="input" id="city">
          <option value="">انتخاب کن</option>
          ${createCityOptions(data.cities, data.city)}
        </select>
      </div>
    </section>
  `;
}

function createQuestionStep(question) {
  const hint = question.kind === "multi" ? `<p class="note">هر چندتا که می‌خوای انتخاب کن.</p>` : "";
  return `
    <section class="step" data-step data-question="${question.id}" tabindex="-1" hidden>
      <div>
        <h1 class="step__title">${escapeHtml(question.text)}</h1>
        ${hint}
      </div>
      ${createChoiceList(question)}
    </section>
  `;
}

function getSteps() {
  return stepsBox.querySelectorAll("[data-step]");
}

function isStepValid(index) {
  if (index === 0) return true;

  const question = questions[index - 1];
  const answer = readQuestionAnswer(getSteps()[index], question);
  return answer.options.length > 0 || answer.other !== "";
}

function updateButtons() {
  const isValid = isStepValid(currentStep);
  nextButton.disabled = !isValid;
  submitButton.disabled = !isValid;
}

function showStep(index) {
  const steps = getSteps();
  steps.forEach((step, stepIndex) => {
    step.hidden = stepIndex !== index;
  });
  currentStep = index;

  const isLast = index === steps.length - 1;
  previousButton.hidden = index === 0;
  nextButton.hidden = isLast;
  submitButton.hidden = !isLast;

  progressBar.max = steps.length;
  progressBar.value = index + 1;
  counter.textContent = `${toFarsiNumber(index + 1)} از ${toFarsiNumber(steps.length)}`;

  updateButtons();
  steps[index].focus();
  window.scrollTo(0, 0);
}

function collectAnswers() {
  const answers = {};
  questions.forEach((question, index) => {
    answers[question.id] = readQuestionAnswer(getSteps()[index + 1], question);
  });
  return answers;
}

async function loadOnboarding() {
  try {
    const data = await apiRequest(ENDPOINTS.onboarding);
    if (data.done) {
      window.location.href = "index.html";
      return;
    }
    questions = data.questions;
    stepsBox.innerHTML = createNameStep(data) + questions.map(createQuestionStep).join("");
    form.hidden = false;
    showStep(0);
  } catch (error) {
    showPageError(stepsBox, loadOnboarding);
  }
}

previousButton.addEventListener("click", () => showStep(currentStep - 1));

nextButton.addEventListener("click", () => {
  if (isStepValid(currentStep)) {
    showStep(currentStep + 1);
  }
});

stepsBox.addEventListener("input", updateButtons);

stepsBox.addEventListener("change", (event) => {
  const step = getSteps()[currentStep];
  syncOtherInput(step);
  updateButtons();

  const isSingleChoice = event.target.type === "radio" && !event.target.hasAttribute("data-other");
  const isLast = currentStep === getSteps().length - 1;
  if (isSingleChoice && !isLast) {
    const stepIndex = currentStep;
    setTimeout(() => {
      if (currentStep === stepIndex) {
        showStep(stepIndex + 1);
      }
    }, 240);
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;

  try {
    await apiRequest(ENDPOINTS.onboarding, "POST", {
      display_name: document.getElementById("display-name").value,
      city: document.getElementById("city").value,
      answers: collectAnswers(),
    });
    window.location.href = "index.html";
  } catch (error) {
    if (error.data && error.data.missing_question) {
      showToast(error.data.detail, "error");
      const missingIndex = questions.findIndex((q) => q.id === error.data.missing_question);
      showStep(missingIndex + 1);
    } else {
      showToast("ثبت نشد. دوباره امتحان کن.", "error");
      submitButton.disabled = false;
    }
  }
});

loadOnboarding();

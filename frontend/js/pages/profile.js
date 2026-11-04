requireLogin();
renderTabbar("profile");

const page = document.getElementById("profile-page");
let questions = [];

function createHeader(data) {
  const initial = data.display_name ? data.display_name[0] : "ح";
  return `
    <header class="profile-head">
      <span class="avatar" aria-hidden="true">${escapeHtml(initial)}</span>
      <div>
        <h1 class="page-title">${escapeHtml(data.display_name || "دوست حالینو")}</h1>
        <p class="note">${toFarsiNumber(data.phone)}</p>
      </div>
    </header>
  `;
}

function createQuestionCard(question, isOpen) {
  const isAnswered = question.answered.length > 0;
  const answerText = isAnswered
    ? `<span class="fold__hint">${escapeHtml(question.answered.join("، "))}</span>`
    : "";
  const tick = isAnswered ? createIcon("check", "icon--small fold__tick") : "";

  return `
    <details class="fold" ${isOpen ? "open" : ""}>
      <summary class="fold__summary">
        ${tick}
        <span class="fold__text">
          <span>${escapeHtml(question.text)}</span>
          ${answerText}
        </span>
        ${createIcon("chevron-down", "icon--small fold__arrow")}
      </summary>
      <form class="fold__body" data-question-form="${question.id}">
        ${createChoiceList(question, "choice-list--compact")}
        <button type="submit" class="btn btn--primary">ثبت</button>
      </form>
    </details>
  `;
}

function createQuestions(data) {
  if (data.questions.length === 0) return "";

  const firstOpen = data.questions.find((question) => question.answered.length === 0);
  const cards = data.questions
    .map((question) => createQuestionCard(question, question === firstOpen))
    .join("");

  return `
    <section class="section">
      <div>
        <h2 class="section__title">بهتر بشناسیمت</h2>
        <p class="note">هر کدوم رو خواستی جواب بده؛ پیشنهادها دقیق‌تر می‌شن.</p>
      </div>
      <div class="fold-list">${cards}</div>
    </section>
  `;
}

function createCityOptions(data) {
  return data.cities
    .map((city) => {
      const note = city.is_supported ? "" : " (بدون پیشنهاد مکان)";
      const selected = city.id === data.city ? "selected" : "";
      return `<option value="${city.id}" ${selected}>${escapeHtml(city.name)}${note}</option>`;
    })
    .join("");
}

function createEditForm(data) {
  return `
    <details class="fold">
      <summary class="fold__summary">
        ${createIcon("sliders", "icon--small")}
        <span class="fold__text">ویرایش پروفایل</span>
        ${createIcon("chevron-down", "icon--small fold__arrow")}
      </summary>
      <form class="fold__body form" id="profile-form">
        <div class="field">
          <label class="label" for="display-name">اسمت</label>
          <input class="input" id="display-name" maxlength="64" value="${escapeHtml(data.display_name)}">
        </div>
        <div class="field">
          <label class="label" for="city">شهرت</label>
          <select class="input" id="city">
            <option value="">انتخاب کن</option>
            ${createCityOptions(data)}
          </select>
        </div>
        <button type="submit" class="btn btn--primary btn--block">ذخیره</button>
      </form>
    </details>
  `;
}

function createSkippedRow(item) {
  return `
    <div class="skipped-row" data-category="${escapeHtml(item.category.slug)}">
      <span class="item-row__icon">${createIcon(item.category.slug)}</span>
      <span class="skipped-row__title">${escapeHtml(item.title)}</span>
      <button type="button" class="btn btn--ghost" data-item="${item.id}" data-action="reset">برگردون</button>
    </div>
  `;
}

function createSkipped(data) {
  if (data.skipped.length === 0) return "";

  return `
    <details class="fold">
      <summary class="fold__summary">
        ${createIcon("eye-off", "icon--small")}
        <span class="fold__text">مواردی که گفتی پیشنهاد نده</span>
        ${createIcon("chevron-down", "icon--small fold__arrow")}
      </summary>
      <div class="fold__body">${data.skipped.map(createSkippedRow).join("")}</div>
    </details>
  `;
}

function renderProfile(data) {
  questions = data.questions;
  page.innerHTML = `
    ${createHeader(data)}
    ${createQuestions(data)}
    <section class="fold-list">
      ${createEditForm(data)}
      ${createSkipped(data)}
    </section>
    <button type="button" class="logout-btn" id="logout-btn">
      ${createIcon("log-out", "icon--small")} خروج از حساب
    </button>
  `;
}

async function loadProfile() {
  try {
    renderProfile(await apiRequest(ENDPOINTS.profile));
  } catch (error) {
    showPageError(page, loadProfile);
  }
}

async function saveProfile(form) {
  const submitButton = form.querySelector("button[type=submit]");
  submitButton.disabled = true;

  try {
    const data = await apiRequest(ENDPOINTS.profile, "PATCH", {
      display_name: document.getElementById("display-name").value,
      city: document.getElementById("city").value,
    });
    showToast(data.detail);
    loadProfile();
  } catch (error) {
    showToast("ذخیره نشد. دوباره امتحان کن.", "error");
    submitButton.disabled = false;
  }
}

async function saveQuestion(form) {
  const questionId = Number(form.dataset.questionForm);
  const question = questions.find((row) => row.id === questionId);
  const submitButton = form.querySelector("button[type=submit]");
  submitButton.disabled = true;

  try {
    const data = await apiRequest(
      `${ENDPOINTS.profile}questions/${questionId}/`,
      "POST",
      readQuestionAnswer(form, question)
    );
    showToast(data.detail);
    loadProfile();
  } catch (error) {
    const message = error.data && error.data.detail ? error.data.detail : "ثبت نشد. دوباره امتحان کن.";
    showToast(message, "error");
    submitButton.disabled = false;
  }
}

page.addEventListener("submit", (event) => {
  event.preventDefault();
  if (event.target.id === "profile-form") {
    saveProfile(event.target);
  } else {
    saveQuestion(event.target);
  }
});

page.addEventListener("change", (event) => {
  const form = event.target.closest("[data-question-form]");
  if (form && event.target.name) {
    syncOtherInput(form);
  }
});

page.addEventListener("click", (event) => {
  if (event.target.closest("#logout-btn")) {
    logout();
  }
});

listenToItemActions(loadProfile);
loadProfile();

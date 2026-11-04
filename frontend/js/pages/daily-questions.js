requireLogin();

const page = document.getElementById("questions-page");
let questions = [];

function createQuestion(question) {
  return `
    <fieldset class="question" data-question="${question.id}">
      <legend class="question__text">${escapeHtml(question.text)}</legend>
      ${createChoiceList(question, "choice-list--compact")}
    </fieldset>
  `;
}

function createBox(box) {
  return `
    <section class="panel">
      <h2 class="section__title">${escapeHtml(box.title)}</h2>
      ${box.questions.map(createQuestion).join("")}
    </section>
  `;
}

function renderQuestions(data) {
  questions = data.boxes.flatMap((box) => box.questions);

  page.innerHTML = `
    <header>
      <span class="section__eyebrow">چون امروز حالت ${escapeHtml(data.mood.name)}ه</span>
      <h1 class="page-title">چند سؤال کوتاه دربارهٔ امروز</h1>
      <p class="note">پیشنهادهای امروزت دقیق‌تر می‌شن.</p>
    </header>
    <form class="form" id="questions-form">
      ${data.boxes.map(createBox).join("")}
      <div class="form-actions">
        <button type="submit" class="btn btn--primary btn--block">ثبت</button>
        <a class="link" href="index.html">بعداً جواب می‌دم</a>
      </div>
    </form>
  `;
}

function collectAnswers() {
  const answers = {};
  questions.forEach((question) => {
    const container = page.querySelector(`[data-question="${question.id}"]`);
    answers[question.id] = readQuestionAnswer(container, question);
  });
  return answers;
}

async function loadQuestions() {
  try {
    const data = await apiRequest(ENDPOINTS.dailyQuestions);
    renderQuestions(data);
    if (sessionStorage.getItem("mood_just_saved")) {
      sessionStorage.removeItem("mood_just_saved");
      showToast("حال امروزت ثبت شد.");
    }
  } catch (error) {
    if (error.status === 404) {
      window.location.href = "index.html";
      return;
    }
    showPageError(page, loadQuestions);
  }
}

page.addEventListener("change", (event) => {
  if (event.target.type === "radio" || event.target.type === "checkbox") {
    syncOtherInput(event.target.closest("[data-question]"));
  }
});

page.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = event.target.querySelector("button[type=submit]");
  submitButton.disabled = true;

  try {
    await apiRequest(ENDPOINTS.dailyQuestions, "POST", { answers: collectAnswers() });
    window.location.href = "index.html";
  } catch (error) {
    showToast("ثبت نشد. دوباره امتحان کن.", "error");
    submitButton.disabled = false;
  }
});

loadQuestions();

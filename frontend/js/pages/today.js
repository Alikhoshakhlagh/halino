requireLogin();
renderTabbar("today");

const page = document.getElementById("today-page");
const moodSheet = createMoodSheet();
let todayData = null;

function createHeader(data) {
  const name = data.display_name ? `، ${escapeHtml(data.display_name)}` : "";
  const date = `${data.date.weekday}، ${toFarsiNumber(data.date.day)} ${data.date.month}`;
  const moodButton = data.mood
    ? `<button type="button" class="today-head__mood" data-open-mood aria-label="تغییر حال امروز">${createFace(data.mood)}</button>`
    : "";

  return `
    <header class="today-head">
      <div>
        <h1 class="today-head__title">${data.greeting}${name}</h1>
        <p class="note">${date}</p>
      </div>
      ${moodButton}
    </header>
  `;
}

function createOccasion(occasion) {
  if (!occasion) return "";

  const author = occasion.quote_author ? ` — ${escapeHtml(occasion.quote_author)}` : "";
  const quote = occasion.quote
    ? `<p class="note">«${escapeHtml(occasion.quote)}»${author}</p>`
    : "";

  return `
    <section class="occasion-card">
      <span class="section__eyebrow">${escapeHtml(occasion.source_label)}</span>
      <h2 class="occasion-card__title">${escapeHtml(occasion.title)}</h2>
      ${quote}
    </section>
  `;
}

function createMoodCard(data) {
  if (data.mood) return "";

  return `
    <section class="mood-card">
      <div>
        <h2 class="section__title">امروز چه حالی داری؟</h2>
        <p class="note">یکی رو انتخاب کن تا پیشنهادهای متناسب با همون حال باز بشه.</p>
      </div>
      ${createMoodPicker(data.moods, null)}
    </section>
  `;
}

function createQuestionsLink(data) {
  if (!data.mood || data.answered_daily) return "";

  return `
    <a class="questions-link" href="daily-questions.html">
      ${createIcon("help")}
      <span>چند سؤال کوتاه داری؛ جواب بده تا پیشنهادها دقیق‌تر بشن.</span>
      ${createIcon("chevron-left", "icon--small")}
    </a>
  `;
}

function createInProgress(items) {
  if (items.length === 0) return "";

  const rows = items.map((item) => createItemRow(item)).join("");
  return `
    <section class="section">
      <h2 class="section__title">در حال انجام</h2>
      <div class="item-list">${rows}</div>
    </section>
  `;
}

function createRecommendationRows(rows) {
  return rows.map((row) => createItemRow(row.item, row.because, row.is_done)).join("");
}

function createMoodItems(data) {
  if (!data.mood) return "";

  const rows = createRecommendationRows(data.mood_items);
  const content = rows
    ? `<div class="item-list">${rows}</div>`
    : `<p class="note">برای این حال چیز تازه‌ای نمونده. فردا دوباره سر بزن.</p>`;

  return `
    <section class="section">
      <div>
        <span class="section__eyebrow">چون امروز حالت ${escapeHtml(data.mood.name)}ه</span>
        <h2 class="section__title">متناسب با حالت</h2>
      </div>
      ${content}
    </section>
  `;
}

function createDayItems(data) {
  const rows = createRecommendationRows(data.day_items);
  const content = rows
    ? `<div class="item-list">${rows}</div>`
    : `<p class="note">فعلاً چیزی برای پیشنهاد پیدا نکردیم. از بخش دسته‌ها بگرد.</p>`;

  return `
    <section class="section">
      <div>
        <span class="section__eyebrow">بر اساس چیزهایی که دوست داری</span>
        <h2 class="section__title">پیشنهاد روز</h2>
      </div>
      ${content}
    </section>
  `;
}

function renderToday(data) {
  page.innerHTML = [
    createHeader(data),
    createMoodCard(data),
    createQuestionsLink(data),
    createOccasion(data.occasion),
    createInProgress(data.in_progress),
    createMoodItems(data),
    createDayItems(data),
  ].join("");

  todayData = data;
}

async function loadToday() {
  try {
    const data = await apiRequest(ENDPOINTS.today);
    if (data.onboarding_required) {
      window.location.href = "onboarding.html";
      return;
    }
    renderToday(data);
  } catch (error) {
    showPageError(page, loadToday);
  }
}

async function saveMood(form) {
  const submitButton = form.querySelector("button[type=submit]");
  const checked = form.querySelector("input[name=mood]:checked");
  submitButton.disabled = true;

  try {
    const data = await apiRequest(ENDPOINTS.mood, "POST", { mood: checked.value });
    moodSheet.close();
    if (data.ask_questions) {
      sessionStorage.setItem("mood_just_saved", "1");
      window.location.href = "daily-questions.html";
      return;
    }
    showToast("حال امروزت ثبت شد.");
    loadToday();
  } catch (error) {
    showToast("ثبت نشد. دوباره امتحان کن.", "error");
    submitButton.disabled = false;
  }
}

document.addEventListener("click", (event) => {
  if (event.target.closest("[data-open-mood]")) {
    openMoodSheet(moodSheet, "حال امروزت رو عوض می‌کنی؟", todayData.moods, todayData.mood);
  }
});

listenToItemActions(loadToday);
listenToMoodForms(saveMood);

loadToday();

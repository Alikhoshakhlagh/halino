requireLogin();
renderTabbar("calendar");

const page = document.getElementById("calendar-page");
const WEEK_DAYS = ["ش", "ی", "د", "س", "چ", "پ", "ج"];

function createMonthLink(month, iconName, label) {
  return `
    <a class="icon-btn" href="calendar.html?y=${month.y}&m=${month.m}" aria-label="${label}">
      ${createIcon(iconName, "icon--small")}
    </a>
  `;
}

function createHeader(data) {
  return `
    <header class="month-nav">
      <div>
        <span class="section__eyebrow">تقویم</span>
        <h1 class="page-title">${data.month_name} ${toFarsiNumber(data.year)}</h1>
      </div>
      <div class="month-nav__buttons">
        ${createMonthLink(data.previous, "chevron-right", "ماه قبل")}
        ${createMonthLink(data.next, "chevron-left", "ماه بعد")}
      </div>
    </header>
  `;
}

function createLegend(data) {
  if (data.legend.length === 0) {
    return `<p class="note">هر روز که حالت رو ثبت کنی، یه توپ به شیشه اضافه می‌شه.</p>`;
  }

  const rows = data.legend
    .map(
      (row) => `
        <li class="legend__row">
          ${createFace(row.mood, "small")}
          <span>${escapeHtml(row.mood.name)}</span>
          <span class="legend__count">×${toFarsiNumber(row.count)}</span>
        </li>
      `
    )
    .join("");
  return `<ul class="legend">${rows}</ul>`;
}

function createJar(balls) {
  const faces = balls.map((mood) => createFace(mood, "fill")).join("");
  return `
    <div class="jar" aria-hidden="true">
      <div class="jar__lid"></div>
      <div class="jar__glass">${faces}</div>
    </div>
  `;
}

function createReport(data) {
  const title = data.dominant
    ? `حال این ماهت بیشتر ${escapeHtml(data.dominant.name)} بوده`
    : "این ماه هنوز حالی ثبت نکردی";

  return `
    <section class="panel">
      <div>
        <span class="section__eyebrow">گزارش ماهانه</span>
        <h2 class="section__title">${title}</h2>
      </div>
      <div class="report">
        ${createLegend(data)}
        ${createJar(data.balls)}
      </div>
    </section>
  `;
}

function createDayCell(day) {
  const classes = ["calendar__cell"];
  if (day.is_today) classes.push("calendar__cell--today");
  if (day.is_future) classes.push("calendar__cell--future");

  const face = day.mood ? createFace(day.mood, "fill") : `<span class="calendar__empty"></span>`;
  const label = day.is_today ? `<span class="visually-hidden">امروز</span>` : "";
  return `
    <div class="${classes.join(" ")}">
      <span class="calendar__day">${toFarsiNumber(day.day)}${label}</span>
      ${face}
    </div>
  `;
}

function createCalendar(data) {
  const heads = WEEK_DAYS.map((name) => `<span class="calendar__head">${name}</span>`).join("");
  const blanks = `<span></span>`.repeat(data.first_weekday);
  const days = data.days.map(createDayCell).join("");

  return `
    <section class="panel">
      <div class="calendar">${heads}${blanks}${days}</div>
    </section>
  `;
}

function createChartSection(data) {
  const hasPoints = data.days.some((day) => day.mood);
  return `
    <section class="panel">
      <div>
        <span class="section__eyebrow">روند</span>
        <h2 class="section__title">نوسان حال در طول ماه</h2>
      </div>
      ${createMoodChart(data)}
      ${hasPoints ? "" : `<p class="note">وقتی چند روز حالت رو ثبت کنی، روند اینجا معلوم می‌شه.</p>`}
    </section>
  `;
}

function createStats(data) {
  const dominant = data.dominant ? createFace(data.dominant) : `<b class="stat__value">—</b>`;
  return `
    <section class="stats">
      <div class="stat">
        <b class="stat__value" id="stat-count">${toFarsiNumber(data.count)}</b>
        <span class="stat__label">روز ثبت‌شده</span>
      </div>
      <div class="stat">
        <b class="stat__value" id="stat-coverage">٪${toFarsiNumber(data.coverage)}</b>
        <span class="stat__label">پوشش ماه</span>
      </div>
      <div class="stat">
        ${dominant}
        <span class="stat__label">پرتکرارترین</span>
      </div>
    </section>
  `;
}

function getMonthQuery() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("y") && params.get("m")) {
    return `?y=${encodeURIComponent(params.get("y"))}&m=${encodeURIComponent(params.get("m"))}`;
  }
  return "";
}

async function loadCalendar() {
  try {
    const data = await apiRequest(ENDPOINTS.calendar + getMonthQuery());
    page.innerHTML = [
      createHeader(data),
      createReport(data),
      createCalendar(data),
      createChartSection(data),
      createStats(data),
    ].join("");
    animateCount(document.getElementById("stat-count"), data.count);
  } catch (error) {
    showPageError(page, loadCalendar);
  }
}

loadCalendar();

requireLogin();
renderTabbar("categories");

const page = document.getElementById("category-page");
const slug = new URLSearchParams(window.location.search).get("slug");

let categoryData = null;
let selectedCity = "";
let searchText = "";

function normalizeText(text) {
  return text
    .replaceAll("ي", "ی")
    .replaceAll("ك", "ک")
    .replaceAll("\u200c", " ")
    .toLowerCase()
    .trim();
}

function createRow(item) {
  const isDone = item.status === "done";
  return createItemRow(item, "", isDone, isDone ? "" : item.status_label);
}

function getCities() {
  const cities = categoryData.items.map((item) => item.city).filter(Boolean);
  return [...new Set(cities)];
}

function getVisibleItems() {
  const search = normalizeText(searchText);
  return categoryData.items.filter((item) => {
    const isInCity = !selectedCity || item.city === selectedCity;
    const text = normalizeText(`${item.title} ${item.subtitle}`);
    return isInCity && text.includes(search);
  });
}

function renderList() {
  const items = getVisibleItems();
  document.getElementById("item-count").textContent = `${toFarsiNumber(items.length)} مورد`;
  document.getElementById("item-list").innerHTML = items.length
    ? items.map(createRow).join("")
    : `<p class="note">چیزی با این مشخصات پیدا نشد.</p>`;
}

function createCityFilter(cities) {
  if (cities.length === 0) return "";

  const choices = cities
    .map(
      (city) => `
        <label class="choice">
          <input type="radio" name="city" value="${escapeHtml(city)}" ${city === selectedCity ? "checked" : ""}>
          <span>${escapeHtml(city)}</span>
        </label>
      `
    )
    .join("");
  return `<div class="choice-list choice-list--compact" role="radiogroup" aria-label="شهر">${choices}</div>`;
}

function renderPage() {
  const cities = getCities();
  if (!selectedCity && cities.length > 0) {
    selectedCity = cities.includes(categoryData.user_city) ? categoryData.user_city : cities[0];
  }

  page.innerHTML = `
    <header class="month-nav">
      <div>
        <h1 class="page-title">${escapeHtml(categoryData.category.name)}</h1>
        <p class="note" id="item-count"></p>
      </div>
      <a class="icon-btn" href="categories.html" aria-label="برگشت به دسته‌ها">${createIcon("chevron-left", "icon--small")}</a>
    </header>
    <section class="section">
      <label class="visually-hidden" for="search">جست‌وجو</label>
      <input class="input" type="search" id="search" placeholder="جست‌وجو توی ${escapeHtml(categoryData.category.name)}…" value="${escapeHtml(searchText)}">
      ${createCityFilter(cities)}
      <div class="item-list" id="item-list"></div>
    </section>
  `;
  renderList();
}

function showNotFound() {
  page.innerHTML = `
    <div class="page-error">
      <p>این دسته پیدا نشد یا برای شهر تو فعال نیست.</p>
      <a class="btn btn--ghost" href="categories.html">برگشت به دسته‌ها</a>
    </div>
  `;
}

async function loadCategory() {
  try {
    const isFirstLoad = categoryData === null;
    categoryData = await apiRequest(`${ENDPOINTS.categories}${encodeURIComponent(slug)}/`);
    document.title = `${categoryData.category.name} | حالینو`;

    if (isFirstLoad) {
      renderPage();
    } else {
      renderList();
    }
  } catch (error) {
    if (error.status === 404) {
      showNotFound();
    } else {
      showPageError(page, loadCategory);
    }
  }
}

page.addEventListener("input", (event) => {
  if (event.target.id === "search") {
    searchText = event.target.value;
    renderList();
  }
});

page.addEventListener("change", (event) => {
  if (event.target.name === "city") {
    selectedCity = event.target.value;
    renderList();
  }
});

listenToItemActions(loadCategory);
loadCategory();

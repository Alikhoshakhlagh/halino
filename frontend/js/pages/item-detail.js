requireLogin();
renderTabbar("categories");

const page = document.getElementById("item-page");
const itemId = new URLSearchParams(window.location.search).get("id");

function createBanner(item) {
  const art = item.image_url
    ? `<img class="item-banner__image" src="${escapeHtml(item.image_url)}" alt="">`
    : createIcon(item.category.slug, "item-banner__icon");

  return `
    <div class="item-banner" data-category="${escapeHtml(item.category.slug)}">
      <a class="icon-btn item-banner__back" href="category-detail.html?slug=${encodeURIComponent(item.category.slug)}" aria-label="برگشت به ${escapeHtml(item.category.name)}">
        ${createIcon("chevron-right", "icon--small")}
      </a>
      ${art}
    </div>
  `;
}

function createTags(tags) {
  if (tags.length === 0) return "";

  const chips = tags.map((tag) => `<li class="tag">${escapeHtml(tag)}</li>`).join("");
  return `<ul class="tags" aria-label="ژانر و حال‌وهوا">${chips}</ul>`;
}

function createMetaRow(iconName, text) {
  return `<li class="item-meta__row">${createIcon(iconName, "icon--small")}<span>${escapeHtml(text)}</span></li>`;
}

function createMeta(item) {
  const rows = [];
  if (item.city) rows.push(createMetaRow("map-pin", item.city));
  if (item.duration_minutes) {
    rows.push(createMetaRow("clock", `حدود ${toFarsiNumber(item.duration_minutes)} دقیقه`));
  }
  if (item.status_label) rows.push(createMetaRow("bookmark", item.status_label));

  return rows.length ? `<ul class="item-meta">${rows.join("")}</ul>` : "";
}

function createRatingOptions(currentRating) {
  let options = `<option value="">بدون امتیاز</option>`;
  for (let rating = 1; rating <= 5; rating++) {
    const selected = rating === currentRating ? "selected" : "";
    options += `<option value="${rating}" ${selected}>${toFarsiNumber(rating)} از ۵</option>`;
  }
  return options;
}

function createActions(item) {
  const progressButton = item.category.is_serial
    ? `<button type="button" class="btn btn--ghost" data-item-action="progress">شروع کردم</button>`
    : "";

  return `
    <section class="panel">
      <div class="field">
        <label class="label" for="rating">اگه انجامش دادی، چند می‌دی؟</label>
        <select class="input" id="rating">${createRatingOptions(item.rating)}</select>
      </div>
      <button type="button" class="btn btn--primary btn--block" data-item-action="done">
        ${createIcon("check", "icon--small")} انجام دادم
      </button>
      <div class="item-actions">
        ${progressButton}
        <button type="button" class="btn btn--ghost" data-item-action="skip">دیگه پیشنهاد نده</button>
      </div>
    </section>
  `;
}

function createDescription(description) {
  if (!description) return "";
  return `<p class="item-description">${escapeHtml(description)}</p>`;
}

function renderItem(item) {
  document.title = `${item.title} | حالینو`;
  const subtitle = item.subtitle ? `<p class="note">${escapeHtml(item.subtitle)}</p>` : "";

  page.innerHTML = `
    ${createBanner(item)}
    <section class="section">
      <div>
        <span class="section__eyebrow">${escapeHtml(item.category.name)}</span>
        <h1 class="page-title">${escapeHtml(item.title)}</h1>
        ${subtitle}
      </div>
      ${createTags(item.tags)}
      ${createDescription(item.description)}
      ${createMeta(item)}
    </section>
    ${createActions(item)}
  `;
}

function showNotFound() {
  page.innerHTML = `
    <div class="page-error">
      <p>این مورد پیدا نشد.</p>
      <a class="btn btn--ghost" href="categories.html">برگشت به دسته‌ها</a>
    </div>
  `;
}

async function loadItem() {
  try {
    const item = await apiRequest(`${ENDPOINTS.items}${encodeURIComponent(itemId)}/`);
    renderItem(item);
  } catch (error) {
    if (error.status === 404) {
      showNotFound();
    } else {
      showPageError(page, loadItem);
    }
  }
}

page.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-item-action]");
  if (!button) return;

  button.disabled = true;
  const rating = document.getElementById("rating").value;

  try {
    const data = await sendItemAction(itemId, button.dataset.itemAction, rating);
    showToast(data.detail);
    loadItem();
  } catch (error) {
    showToast("ثبت نشد. دوباره امتحان کن.", "error");
    button.disabled = false;
  }
});

loadItem();

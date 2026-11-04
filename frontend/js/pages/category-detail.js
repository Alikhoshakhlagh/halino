requireLogin();
renderTabbar("categories");

const page = document.getElementById("category-page");
const slug = new URLSearchParams(window.location.search).get("slug");

function createRow(item) {
  const isDone = item.status === "done";
  return createItemRow(item, "", isDone, isDone ? "" : item.status_label);
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
    const data = await apiRequest(`${ENDPOINTS.categories}${encodeURIComponent(slug)}/`);
    document.title = `${data.category.name} | حالینو`;

    const list = data.items.length
      ? `<section class="item-list">${data.items.map(createRow).join("")}</section>`
      : `<p class="note">هنوز چیزی توی این دسته ثبت نشده.</p>`;

    page.innerHTML = `
      <header class="month-nav">
        <div>
          <h1 class="page-title">${escapeHtml(data.category.name)}</h1>
          <p class="note">${toFarsiNumber(data.items.length)} مورد</p>
        </div>
        <a class="icon-btn" href="categories.html" aria-label="برگشت به دسته‌ها">${createIcon("chevron-left", "icon--small")}</a>
      </header>
      ${list}
    `;
  } catch (error) {
    if (error.status === 404) {
      showNotFound();
    } else {
      showPageError(page, loadCategory);
    }
  }
}

listenToItemActions(loadCategory);
loadCategory();

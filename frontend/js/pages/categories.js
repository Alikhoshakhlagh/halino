requireLogin();
renderTabbar("categories");

const page = document.getElementById("categories-page");

function createTile(category) {
  return `
    <a class="tile" data-category="${escapeHtml(category.slug)}" href="category-detail.html?slug=${encodeURIComponent(category.slug)}">
      <span class="tile__icon">${createIcon(category.slug)}</span>
      <span class="tile__name">${escapeHtml(category.name)}</span>
      <span class="tile__count">${toFarsiNumber(category.count)} مورد</span>
    </a>
  `;
}

async function loadCategories() {
  try {
    const data = await apiRequest(ENDPOINTS.categories);
    const cityNote = data.can_see_places
      ? ""
      : `<p class="note">دسته‌های مکان‌محور فعلاً فقط برای تهران و اصفهان فعالن. شهرت رو از پروفایل عوض کن.</p>`;

    page.innerHTML = `
      <header>
        <h1 class="page-title">دسته‌ها</h1>
        <p class="note">هر چیزی که می‌تونه حالت رو عوض کنه.</p>
      </header>
      <section class="tiles">${data.categories.map(createTile).join("")}</section>
      ${cityNote}
    `;
  } catch (error) {
    showPageError(page, loadCategories);
  }
}

loadCategories();

function createItemMeta(item, because) {
  const parts = [item.category.name];
  if (because) {
    parts.push(`به مناسبت ${because}`);
  }
  if (item.duration_minutes) {
    parts.push(`حدود ${toFarsiNumber(item.duration_minutes)} دقیقه`);
  }
  return parts.map(escapeHtml).join(" · ");
}

function createItemActions(item, isDone) {
  if (isDone) {
    return `<span class="item-row__badge">${createIcon("check", "icon--small")} انجام شد</span>`;
  }

  return `
    <button type="button" class="icon-btn item-row__done" data-item="${item.id}" data-action="done" aria-label="انجام دادم: ${escapeHtml(item.title)}">
      ${createIcon("check")}
    </button>
    <button type="button" class="icon-btn" data-item="${item.id}" data-action="skip" aria-label="نمی‌خوام: ${escapeHtml(item.title)}">
      ${createIcon("x")}
    </button>
  `;
}

function createItemRow(item, because = "", isDone = false) {
  return `
    <article class="item-row" data-category="${escapeHtml(item.category.slug)}">
      <span class="item-row__icon">${createIcon(item.category.slug)}</span>
      <div class="item-row__body">
        <a class="item-row__title" href="item-detail.html?id=${item.id}">${escapeHtml(item.title)}</a>
        <p class="item-row__meta">${createItemMeta(item, because)}</p>
      </div>
      <div class="item-row__actions">${createItemActions(item, isDone)}</div>
    </article>
  `;
}

async function sendItemAction(itemId, action) {
  return apiRequest(`${ENDPOINTS.items}${itemId}/action/`, "POST", { action });
}

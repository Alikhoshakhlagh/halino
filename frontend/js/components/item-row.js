function createItemMeta(item, because, statusLabel) {
  const parts = [item.category.name];
  if (item.subtitle) {
    parts.push(item.subtitle);
  }
  if (because) {
    parts.push(`به مناسبت ${because}`);
  }
  if (statusLabel) {
    parts.push(statusLabel);
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

function createItemRow(item, because = "", isDone = false, statusLabel = "") {
  return `
    <article class="item-row" data-category="${escapeHtml(item.category.slug)}">
      <span class="item-row__icon">${createIcon(item.category.slug)}</span>
      <div class="item-row__body">
        <a class="item-row__title" href="item-detail.html?id=${item.id}">${escapeHtml(item.title)}</a>
        <p class="item-row__meta">${createItemMeta(item, because, statusLabel)}</p>
      </div>
      <div class="item-row__actions">${createItemActions(item, isDone)}</div>
    </article>
  `;
}

function sendItemAction(itemId, action, rating = "") {
  return apiRequest(`${ENDPOINTS.items}${itemId}/action/`, "POST", { action, rating });
}

function listenToItemActions(onSaved) {
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;

    button.disabled = true;
    try {
      const data = await sendItemAction(button.dataset.item, button.dataset.action);
      showToast(data.detail);
      onSaved();
    } catch (error) {
      showToast("ثبت نشد. دوباره امتحان کن.", "error");
      button.disabled = false;
    }
  });
}

function createMoodChip(mood, currentMood) {
  const isChecked = currentMood && currentMood.id === mood.id;
  return `
    <label class="mood-chip">
      <input type="radio" name="mood" value="${mood.id}" ${isChecked ? "checked" : ""}>
      ${createFace(mood)}
      <span>${escapeHtml(mood.name)}</span>
    </label>
  `;
}

function createMoodPicker(mainMoods, moreMoods, currentMood) {
  const mainChips = mainMoods.map((mood) => createMoodChip(mood, currentMood)).join("");
  const moreChips = moreMoods.map((mood) => createMoodChip(mood, currentMood)).join("");
  const isMoreOpen = currentMood && moreMoods.some((mood) => mood.id === currentMood.id);

  return `
    <form class="mood-picker" data-mood-form>
      <div class="mood-grid">${mainChips}</div>
      <details class="mood-more" ${isMoreOpen ? "open" : ""}>
        <summary>بیشتر ${createIcon("chevron-down", "icon--small")}</summary>
        <div class="mood-grid">${moreChips}</div>
      </details>
      <button type="submit" class="btn btn--primary btn--block" ${currentMood ? "" : "disabled"}>
        ${currentMood ? "به‌روزرسانی حال امروز" : "ثبت حال امروز"}
      </button>
    </form>
  `;
}

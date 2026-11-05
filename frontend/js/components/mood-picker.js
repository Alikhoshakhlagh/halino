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

function listenToMoodForms(onSubmit) {
  document.addEventListener("change", (event) => {
    if (event.target.name === "mood") {
      event.target.form.querySelector("button[type=submit]").disabled = false;
    }
  });

  document.addEventListener("submit", (event) => {
    if (event.target.matches("[data-mood-form]")) {
      event.preventDefault();
      onSubmit(event.target);
    }
  });
}

function createMoodPicker(moods, currentMood) {
  const chips = moods.map((mood) => createMoodChip(mood, currentMood)).join("");

  return `
    <form class="mood-picker" data-mood-form>
      <div class="mood-grid">${chips}</div>
      <button type="submit" class="btn btn--primary btn--block" ${currentMood ? "" : "disabled"}>
        ${currentMood ? "تغییر حال" : "ثبت حال"}
      </button>
    </form>
  `;
}

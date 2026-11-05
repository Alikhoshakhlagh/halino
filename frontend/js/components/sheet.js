function createMoodSheet() {
  document.body.insertAdjacentHTML(
    "beforeend",
    `
      <dialog class="sheet" id="mood-sheet" aria-labelledby="mood-sheet-title">
        <div class="sheet__head">
          <h2 class="sheet__title" id="mood-sheet-title"></h2>
          <button type="button" class="icon-btn" data-close-sheet aria-label="بستن">${createIcon("x")}</button>
        </div>
        <div id="mood-sheet-body"></div>
      </dialog>
    `
  );

  const sheet = document.getElementById("mood-sheet");
  sheet.addEventListener("click", (event) => {
    if (event.target === sheet || event.target.closest("[data-close-sheet]")) {
      sheet.close();
    }
  });
  return sheet;
}

function openMoodSheet(sheet, title, moods, currentMood) {
  document.getElementById("mood-sheet-title").textContent = title;
  document.getElementById("mood-sheet-body").innerHTML = createMoodPicker(moods, currentMood);
  sheet.showModal();
}

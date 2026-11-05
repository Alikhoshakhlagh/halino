function createChoice(question, value, text, isChecked, extraAttribute = "") {
  const type = question.kind === "multi" ? "checkbox" : "radio";
  return `
    <label class="choice">
      <input type="${type}" name="q${question.id}" value="${value}" ${isChecked ? "checked" : ""} ${extraAttribute}>
      <span>${escapeHtml(text)}</span>
    </label>
  `;
}

function createOtherChoice(question) {
  const otherText = question.other_text || "";
  return `
    ${createChoice(question, "other", "مورد دیگه…", Boolean(otherText), "data-other")}
    <input class="input choice__other-input" type="text" maxlength="120" placeholder="بنویس…" aria-label="مورد دیگه" value="${escapeHtml(otherText)}" data-other-input ${otherText ? "" : "hidden"}>
  `;
}

function createChoiceList(question, extraClass = "") {
  const selected = question.selected || [];
  const options = question.options
    .map((option) => createChoice(question, option.id, option.text, selected.includes(option.id)))
    .join("");

  return `
    <div class="choice-list ${extraClass}">
      ${options}
      ${question.allows_other ? createOtherChoice(question) : ""}
    </div>
  `;
}

function applyAnswerDraft(question, answer) {
  if (!answer) return;

  question.selected = answer.options;
  question.other_text = answer.other;
}

function readQuestionAnswer(container, question) {
  const checked = container.querySelectorAll(`input[name="q${question.id}"]:checked`);
  const answer = { options: [], other: "" };

  checked.forEach((input) => {
    if (input.value === "other") {
      answer.other = container.querySelector("[data-other-input]").value.trim();
    } else {
      answer.options.push(Number(input.value));
    }
  });
  return answer;
}

function syncOtherInput(container) {
  const otherChoice = container.querySelector("[data-other]");
  const otherInput = container.querySelector("[data-other-input]");
  if (!otherChoice || !otherInput) return;

  otherInput.hidden = !otherChoice.checked;
  if (otherChoice.checked) {
    otherInput.focus();
  }
}

function createChoice(question, value, text, extraAttribute = "") {
  const type = question.kind === "multi" ? "checkbox" : "radio";
  return `
    <label class="choice">
      <input type="${type}" name="q${question.id}" value="${value}" ${extraAttribute}>
      <span>${escapeHtml(text)}</span>
    </label>
  `;
}

function createChoiceList(question) {
  const options = question.options
    .map((option) => createChoice(question, option.id, option.text))
    .join("");

  if (!question.allows_other) {
    return `<div class="choice-list">${options}</div>`;
  }

  return `
    <div class="choice-list">
      ${options}
      ${createChoice(question, "other", "مورد دیگه…", "data-other")}
      <input class="input choice__other-input" type="text" maxlength="120" placeholder="بنویس…" aria-label="مورد دیگه" data-other-input hidden>
    </div>
  `;
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
}

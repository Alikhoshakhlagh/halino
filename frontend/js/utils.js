function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function toFarsiNumber(value) {
  const digits = "۰۱۲۳۴۵۶۷۸۹";
  return String(value).replace(/\d/g, (digit) => digits[digit]);
}

function showToast(message, type = "success") {
  let box = document.querySelector(".toast-box");
  if (!box) {
    box = document.createElement("div");
    box.className = "toast-box";
    box.setAttribute("aria-live", "polite");
    document.body.appendChild(box);
  }

  const toast = document.createElement("p");
  toast.className = type === "error" ? "toast toast--error" : "toast";
  toast.textContent = message;
  box.appendChild(toast);

  setTimeout(() => toast.remove(), 3000);
}

function showPageError(container, retry) {
  container.innerHTML = `
    <div class="page-error">
      <p>ارتباط با سرور برقرار نشد.</p>
      <button type="button" class="btn btn--ghost" id="retry-btn">دوباره امتحان کن</button>
    </div>
  `;
  document.getElementById("retry-btn").addEventListener("click", retry);
}

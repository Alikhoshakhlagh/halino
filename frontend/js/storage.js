const STORAGE_PREFIX = "halino_";

function saveState(key, value) {
  try {
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value));
  } catch (error) {
    return;
  }
}

function loadState(key, fallback = null) {
  try {
    const value = localStorage.getItem(STORAGE_PREFIX + key);
    return value === null ? fallback : JSON.parse(value);
  } catch (error) {
    return fallback;
  }
}

function removeState(key) {
  try {
    localStorage.removeItem(STORAGE_PREFIX + key);
  } catch (error) {
    return;
  }
}

function clearAllState() {
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith(STORAGE_PREFIX))
      .forEach((key) => localStorage.removeItem(key));
  } catch (error) {
    return;
  }
}

function isPageReloaded() {
  const navigation = performance.getEntriesByType("navigation")[0];
  return Boolean(navigation) && navigation.type === "reload";
}

function getScrollKey() {
  return `scroll_${location.pathname}${location.search}`;
}

let isScrollRestored = false;

function restoreScroll() {
  if (isScrollRestored) return;
  isScrollRestored = true;

  if (isPageReloaded()) {
    window.scrollTo(0, loadState(getScrollKey(), 0));
  }
}

history.scrollRestoration = "manual";

if (isPageReloaded()) {
  document.documentElement.classList.add("is-reload");
}

window.addEventListener("pagehide", () => {
  saveState(getScrollKey(), window.scrollY);
});

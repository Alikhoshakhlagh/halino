const TABS = [
  { id: "today", href: "index.html", icon: "home", label: "امروز" },
  { id: "calendar", href: "calendar.html", icon: "calendar", label: "تقویم" },
  { id: "categories", href: "categories.html", icon: "grid", label: "دسته‌ها" },
  { id: "profile", href: "profile.html", icon: "user", label: "پروفایل" },
];

function renderTabbar(activeTab) {
  const placeholder = document.getElementById("tabbar-placeholder");

  const links = TABS.map((tab) => {
    const isActive = tab.id === activeTab;
    return `
      <a href="${tab.href}" class="tabbar__link ${isActive ? "tabbar__link--active" : ""}" ${isActive ? 'aria-current="page"' : ""}>
        ${createIcon(tab.icon)}
        ${tab.label}
      </a>
    `;
  }).join("");

  placeholder.innerHTML = `<nav class="tabbar" aria-label="ناوبری اصلی">${links}</nav>`;
}

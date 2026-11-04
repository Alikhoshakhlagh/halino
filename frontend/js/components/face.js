const FACES = {
  happy: '<circle cx="35" cy="42" r="5.5"/><circle cx="65" cy="42" r="5.5"/> <path d="M32 56 q18 20 36 0" fill="none" stroke-width="7" stroke-linecap="round"/>',
  calm: '<circle cx="35" cy="44" r="5"/><circle cx="65" cy="44" r="5"/> <path d="M42 61 q8 7 16 0" fill="none" stroke-width="6" stroke-linecap="round"/>',
  focused: '<path d="M27 34 h15" fill="none" stroke-width="6" stroke-linecap="round"/> <path d="M73 34 h-15" fill="none" stroke-width="6" stroke-linecap="round"/> <circle cx="35" cy="48" r="5"/><circle cx="65" cy="48" r="5"/> <path d="M41 65 h18" fill="none" stroke-width="6" stroke-linecap="round"/>',
  tired: '<path d="M27 44 q8 9 16 0" fill="none" stroke-width="6" stroke-linecap="round"/> <path d="M57 44 q8 9 16 0" fill="none" stroke-width="6" stroke-linecap="round"/> <path d="M43 64 h14" fill="none" stroke-width="6" stroke-linecap="round"/>',
  bored: '<path d="M28 44 h15" fill="none" stroke-width="6" stroke-linecap="round"/> <path d="M57 44 h15" fill="none" stroke-width="6" stroke-linecap="round"/> <path d="M40 63 h20" fill="none" stroke-width="6" stroke-linecap="round"/> <ellipse cx="24" cy="57" rx="7" ry="4.5" opacity=".3"/> <ellipse cx="76" cy="57" rx="7" ry="4.5" opacity=".3"/>',
  longing: '<circle cx="35" cy="43" r="5"/><circle cx="65" cy="43" r="5"/> <path d="M35 62 q7 -7 14 0 t14 0" fill="none" stroke-width="6" stroke-linecap="round"/> <ellipse cx="24" cy="56" rx="7" ry="4.5" opacity=".3"/> <ellipse cx="76" cy="56" rx="7" ry="4.5" opacity=".3"/>',
  anxious: '<path d="M26 34 q9 -7 17 -2" fill="none" stroke-width="5.5" stroke-linecap="round"/> <path d="M74 34 q-9 -7 -17 -2" fill="none" stroke-width="5.5" stroke-linecap="round"/> <circle cx="35" cy="49" r="5"/><circle cx="65" cy="49" r="5"/> <path d="M34 69 q16 -12 32 0" fill="none" stroke-width="6.5" stroke-linecap="round"/>',
  sad: '<circle cx="35" cy="44" r="5.5"/><circle cx="65" cy="44" r="5.5"/> <path d="M34 69 q16 -13 32 0" fill="none" stroke-width="7" stroke-linecap="round"/>',
  angry: '<path d="M27 32 l17 8" fill="none" stroke-width="6.5" stroke-linecap="round"/> <path d="M73 32 l-17 8" fill="none" stroke-width="6.5" stroke-linecap="round"/> <circle cx="36" cy="51" r="5"/><circle cx="64" cy="51" r="5"/> <path d="M37 69 q13 -10 26 0" fill="none" stroke-width="6.5" stroke-linecap="round"/>',
};

function createFace(mood, size = "medium") {
  const inner = FACES[mood.face] || FACES.calm;
  return `
    <svg class="face face--${size}" data-mood="${mood.face}" viewBox="0 0 100 100" role="img" aria-label="${escapeHtml(mood.name)}">
      <circle class="face__disc" cx="50" cy="50" r="50"></circle>
      <g class="face__ink">${inner}</g>
    </svg>
  `;
}

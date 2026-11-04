const CHART = {
  width: 320,
  height: 158,
  top: 16,
  bottom: 34,
  left: 12,
  right: 276,
  axisX: 290,
  faceSize: 20,
  labelStep: 4,
};

function getChartX(day, monthLength) {
  const step = (CHART.right - CHART.left) / Math.max(monthLength - 1, 1);
  return CHART.right - (day - 1) * step;
}

function getChartY(valence) {
  const span = CHART.height - CHART.top - CHART.bottom;
  return CHART.top + ((2 - valence) * span) / 4;
}

function createChartRow(valence, mood) {
  const y = getChartY(valence);
  const face = mood
    ? `<svg x="${CHART.axisX}" y="${y - CHART.faceSize / 2}" width="${CHART.faceSize}" height="${CHART.faceSize}" viewBox="0 0 100 100" data-mood="${mood.face}">${createFaceInner(mood)}</svg>`
    : "";
  return `
    <line class="chart__grid" x1="${CHART.left}" y1="${y}" x2="${CHART.right + 6}" y2="${y}"></line>
    ${face}
  `;
}

function createChartLabels(monthLength) {
  let labels = "";
  for (let day = 1; day <= monthLength; day += CHART.labelStep) {
    labels += `<text class="chart__label" x="${getChartX(day, monthLength)}" y="${CHART.height - 16}">${toFarsiNumber(day)}</text>`;
  }
  return labels;
}

function createMoodChart(data) {
  const monthLength = data.days.length;
  const rows = [2, 1, 0, -1, -2]
    .map((valence) => createChartRow(valence, data.chart_faces[valence]))
    .join("");

  const points = data.days
    .filter((day) => day.mood)
    .map((day) => ({
      x: getChartX(day.day, monthLength),
      y: getChartY(day.mood.valence),
      face: day.mood.face,
    }))
    .sort((first, second) => first.x - second.x);

  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const dots = points
    .map((point) => `<circle class="chart__dot" data-mood="${point.face}" cx="${point.x}" cy="${point.y}" r="4.5"></circle>`)
    .join("");

  return `
    <svg class="chart" viewBox="0 0 ${CHART.width} ${CHART.height}" role="img" aria-label="نمودار نوسان حال در طول ماه">
      ${rows}
      ${points.length > 1 ? `<polyline class="chart__line" pathLength="1" points="${line}"></polyline>` : ""}
      ${dots}
      ${createChartLabels(monthLength)}
    </svg>
  `;
}

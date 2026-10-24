document.addEventListener("DOMContentLoaded", () => {
  const side = document.getElementById("sidebar");
  document.getElementById("menu-toggle")?.addEventListener("click", () => side.classList.toggle("open"));
});

/* Draws a simple Chart.js chart from {label, value} rows. */
function drawChart(canvasId, rows, type, color) {
  const el = document.getElementById(canvasId);
  if (!el || typeof Chart === "undefined") return;
  new Chart(el, {
    type,
    data: { labels: rows.map(r => r.label),
      datasets: [{ data: rows.map(r => r.value), backgroundColor: type === "bar" ? color : color + "22",
        borderColor: color, borderWidth: 2, borderRadius: 6, fill: type === "line", tension: .35, pointRadius: 2 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, grid: { color: "#e9eaf4" }, ticks: { precision: 0 } }, x: { grid: { display: false } } } },
  });
}

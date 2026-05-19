document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("canvas[data-chart]").forEach((canvas) => {
    if (!window.Chart) return;
    const labels = (canvas.dataset.labels || "").split(",").filter(Boolean);
    const values = (canvas.dataset.values || "").split(",").filter(Boolean).map(Number);
    const type = canvas.dataset.chart || "bar";
    new Chart(canvas, {
      type,
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: ["#003C97", "#269AE6", "#9CDDE6", "#020F52", "#6EA8FE", "#70D6C3", "#F2B84B"],
          borderWidth: 0,
          borderRadius: type === "bar" ? 10 : 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: type !== "bar", position: "bottom" } },
        scales: type === "bar" ? { y: { beginAtZero: true, ticks: { precision: 0 } } } : {}
      }
    });
  });
});

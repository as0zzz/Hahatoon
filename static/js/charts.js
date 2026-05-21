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

  // --- DASHBOARD SPECIFIC CHARTS ---
  const d = window.__dashData;
  if (!d) return;

  // 1. Dept Efficiency Stacked Bar
  const ctxDeptEff = document.getElementById("chart-dept-efficiency");
  if (ctxDeptEff && d.deptEfficiency) {
    new Chart(ctxDeptEff, {
      type: "bar",
      data: d.deptEfficiency,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        scales: {
          x: { stacked: true, grid: { color: "#f0f4fa" } },
          y: { stacked: true, beginAtZero: true, grid: { color: "#f0f4fa" }, ticks: { precision: 0 } }
        }
      }
    });
  }

  // Helper for Doughnut with click navigation
  const initDoughnut = (id, labels, values, colors, codes, paramName) => {
    const ctx = document.getElementById(id);
    if (!ctx || !labels || !labels.length) return;
    new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{ data: values, backgroundColor: colors, borderWidth: 3 }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: { legend: { position: "bottom" } },
        onHover: (e, elements) => {
          e.native.target.style.cursor = elements.length ? 'pointer' : 'default';
        },
        onClick: (e, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const code = codes[index];
            if (code && d.tasksUrl) {
              window.location.href = `${d.tasksUrl}?${paramName}=${code}`;
            }
          }
        }
      }
    });
  };

  // 2. Priority Doughnut
  initDoughnut("chart-priority", d.priorityLabels, d.priorityValues, d.priorityColors, d.priorityCodes, "priority");

  // 3. Risk Doughnut
  initDoughnut("chart-risk", d.riskLabels, d.riskValues, d.riskColors, d.riskCodes, "risk_level");

  // 4. Periods Bar
  const ctxPeriods = document.getElementById("chart-periods");
  if (ctxPeriods && d.periodLabels && d.periodLabels.length) {
    new Chart(ctxPeriods, {
      type: "bar",
      data: {
        labels: d.periodLabels,
        datasets: [{
          label: "Задачи",
          data: d.periodValues,
          backgroundColor: ["#020F52", "#003C97", "#269AE6", "#9CDDE6"],
          borderRadius: 10
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#f0f4fa" } }
        }
      }
    });
  }

  // 5. Dept Progress Horizontal Bar
  const ctxDeptProg = document.getElementById("chart-dept-progress");
  if (ctxDeptProg && d.deptProgressLabels && d.deptProgressLabels.length) {
    new Chart(ctxDeptProg, {
      type: "bar",
      data: {
        labels: d.deptProgressLabels,
        datasets: [{
          label: "Средний прогресс (%)",
          data: d.deptProgressValues,
          backgroundColor: d.deptProgressValues.map(v => v >= 60 ? "#34D399" : v >= 30 ? "#FBBF24" : "#F97316"),
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.raw}%`
            }
          }
        },
        scales: {
          x: { max: 100, beginAtZero: true, grid: { color: "#f0f4fa" } },
          y: { grid: { display: false } }
        }
      }
    });
  }

  // 6. Overdue Dept Horizontal Bar
  const ctxOverdue = document.getElementById("chart-overdue-dept");
  if (ctxOverdue && d.overdueDeptLabels && d.overdueDeptLabels.length) {
    new Chart(ctxOverdue, {
      type: "bar",
      data: {
        labels: d.overdueDeptLabels,
        datasets: [{
          label: "Просроченных задач",
          data: d.overdueDeptValues,
          backgroundColor: "#F97316",
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#f0f4fa" } },
          y: { grid: { display: false } }
        }
      }
    });
  }

});

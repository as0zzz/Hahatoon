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

  const initScrollableChart = (container, count, maxVisible = 7) => {
    if (!container) return;
    if (count > maxVisible) {
      const wrapper = container.parentElement;
      const updateWidth = () => {
        const ww = wrapper.clientWidth;
        if (ww > 0) {
          const w = ((ww / maxVisible) * count) + "px";
          container.style.width = w;
          container.style.minWidth = w;
        }
      };
      updateWidth();
      window.addEventListener("resize", updateWidth);
      setTimeout(updateWidth, 100);
    } else {
      container.style.width = "100%";
      container.style.minWidth = "100%";
    }
  };

  // 1. Dept Efficiency Stacked Bar
  const ctxDeptEff = document.getElementById("chart-dept-efficiency");
  if (ctxDeptEff && d.deptEfficiency) {
    const container = document.getElementById("dept-chart-container");
    if (container && d.deptEfficiency.labels) {
      initScrollableChart(container, d.deptEfficiency.labels.length);
    }

    const deptChart = new Chart(ctxDeptEff, {
      type: "bar",
      data: d.deptEfficiency,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { 
            stacked: true, 
            grid: { color: "#f0f4fa" },
            ticks: {
              maxRotation: 0,
              minRotation: 0,
              autoSkip: false,
              callback: function(val) {
                const label = this.getLabelForValue(val);
                return (typeof label === 'string' && label.includes(' ') && label.length > 10) ? label.split(' ') : label;
              }
            }
          },
          y: { stacked: true, beginAtZero: true, grid: { color: "#f0f4fa" }, ticks: { precision: 0 } }
        }
      }
    });

    const legendContainer = document.getElementById("dept-efficiency-legend");
    if (legendContainer && d.deptEfficiency.datasets) {
      d.deptEfficiency.datasets.forEach((ds, i) => {
        const item = document.createElement("div");
        item.className = "chart-custom-legend-item";
        
        const box = document.createElement("span");
        box.className = "chart-custom-legend-color";
        box.style.backgroundColor = ds.backgroundColor;
        
        const text = document.createElement("span");
        text.textContent = ds.label;
        
        item.onclick = () => {
          const isHidden = !deptChart.isDatasetVisible(i);
          if (isHidden) {
            deptChart.show(i);
            item.style.opacity = 1;
          } else {
            deptChart.hide(i);
            item.style.opacity = 0.5;
          }
        };
        
        item.appendChild(box);
        item.appendChild(text);
        legendContainer.appendChild(item);
      });
    }
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
    const container = document.getElementById("dept-progress-container");
    if (container && d.deptProgressLabels) {
      initScrollableChart(container, d.deptProgressLabels.length, 6);
    }
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
          y: { max: 100, beginAtZero: true, grid: { color: "#f0f4fa" } },
          x: { 
            grid: { display: false }, 
            ticks: { 
              autoSkip: false,
              maxRotation: 0,
              minRotation: 0,
              callback: function(val) {
                const label = this.getLabelForValue(val);
                return (typeof label === 'string' && label.includes(' ') && label.length > 10) ? label.split(' ') : label;
              }
            } 
          }
        }
      }
    });
  }

  // 6. Overdue Dept Horizontal Bar
  const ctxOverdue = document.getElementById("chart-overdue-dept");
  if (ctxOverdue && d.overdueDeptLabels && d.overdueDeptLabels.length) {
    const container = document.getElementById("overdue-dept-container");
    if (container && d.overdueDeptLabels) {
      initScrollableChart(container, d.overdueDeptLabels.length, 6);
    }
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
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#f0f4fa" } },
          x: { 
            grid: { display: false }, 
            ticks: { 
              autoSkip: false,
              maxRotation: 0,
              minRotation: 0,
              callback: function(val) {
                const label = this.getLabelForValue(val);
                return (typeof label === 'string' && label.includes(' ') && label.length > 10) ? label.split(' ') : label;
              }
            } 
          }
        }
      }
    });
  }

});

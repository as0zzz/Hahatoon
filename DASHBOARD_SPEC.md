# Спецификация дашбордов Hahatoon (TTM)

Этот документ описывает **точную реализацию** страницы «Дашборды» (`/dashboards/`).
Используй его чтобы **полностью переделать** дашборды в обновлённом проекте, воспроизведя всю логику, шаблоны, стили и JS.

---

## Архитектура

Затронутые файлы:
- `apps/dashboards/views.py` — вьюхи
- `apps/dashboards/services.py` — бизнес-логика и формирование контекста
- `apps/dashboards/urls.py` — роутинг
- `templates/dashboard/dashboards.html` — шаблон страницы дашбордов
- `templates/dashboard/home.html` — шаблон главной страницы
- `static/js/charts.js` — Chart.js конфигурации (6 графиков + интерактивность)
- `static/css/app.css` — стили (секция Dashboard начинается с комментария `Dashboard: 6-column KPI grid`)

---

## 1. Views (`apps/dashboards/views.py`)

```python
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from apps.dashboards.services import build_dashboard_context
from apps.tasks.services import task_queryset_for_user

@login_required
def home(request):
    queryset = task_queryset_for_user(request.user)
    context = build_dashboard_context(queryset)
    context["title"] = "Главная"
    return render(request, "dashboard/home.html", context)

@login_required
def dashboards(request):
    queryset = task_queryset_for_user(request.user)
    context = build_dashboard_context(queryset)
    context["title"] = "Дашборды"
    return render(request, "dashboard/dashboards.html", context)
```

---

## 2. Services (`apps/dashboards/services.py`)

Функция `build_dashboard_context(queryset)` возвращает словарь контекста.

### Импорты
```python
import json
from collections import Counter, defaultdict
from django.db.models import Avg, Count, Q, Case, When, Value, IntegerField
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.tasks.models import Task
from apps.tasks.services import get_task_metrics, refresh_all_risks, refresh_all_workloads
```

### Что вычисляется (по порядку):

1. **Core KPIs**: `in_progress` (задачи IN_PROGRESS + REVIEW), `avg_progress` (средний % по открытым задачам)

2. **Department efficiency matrix** (stacked bar) — группировка задач по `department__name` × `status`, формирует JSON `dept_efficiency_data` с labels и datasets. Цвета статусов:
   - NEW: #94A3B8, PLANNED: #60A5FA, IN_PROGRESS: #3B82F6, REVIEW: #A78BFA, DONE: #34D399, OVERDUE: #F97316, CANCELLED: #CBD5E1

3. **Employee performance table** — `employee_data` (list of dicts). Поля: name, department, total, done, overdue, avg_progress, workload, workload_raw. Сортировка: `-overdue_count, -total`

4. **Priority distribution** (doughnut) — `priority_labels`, `priority_values`, `priority_codes`, `priority_colors`. Цвета: LOW=#94A3B8, MEDIUM=#60A5FA, HIGH=#FBBF24, CRITICAL=#EF4444

5. **Risk distribution** (doughnut) — `risk_labels`, `risk_values`, `risk_codes`, `risk_colors`. Цвета: LOW=#34D399, MEDIUM=#FBBF24, HIGH=#F97316, CRITICAL=#EF4444

6. **Dept average progress** (horizontal bar) — `dept_progress_labels`, `dept_progress_values` (открытые задачи, исключая DONE/CANCELLED)

7. **Overdue by department** (horizontal bar) — `overdue_dept_labels`, `overdue_dept_values`

8. **Top risky tasks** — queryset `risky_tasks`: `needs_manager_attention=True`, аннотация `risk_weight` через Case/When (CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1), сортировка `-risk_weight, deadline`, limit 50

9. **Unassigned tasks** — `unassigned_tasks`: `responsible__isnull=True`, исключая DONE/CANCELLED, limit 10

10. **Period distribution** — `period_labels`, `period_values` из `metrics["by_period"]`

### Ключи контекста (return dict):
Все JSON-поля сериализуются через `json.dumps(..., ensure_ascii=False)`:
- `metrics`, `in_progress`, `avg_progress`
- `dept_efficiency_json`
- `employee_data` (list, не JSON)
- `priority_labels`, `priority_values`, `priority_colors`, `priority_codes`
- `risk_labels`, `risk_values`, `risk_colors`, `risk_codes`
- `period_labels`, `period_values`
- `dept_progress_labels`, `dept_progress_values`
- `overdue_dept_labels`, `overdue_dept_values`
- `risky_tasks` (queryset), `unassigned_tasks` (queryset)
- `status_labels`, `status_values`, `department_labels`, `department_values`, `workload_labels`, `workload_values` (legacy для home.html)

---

## 3. Шаблон `dashboards.html`

Наследует `base.html`, загружает `ttm_tags`.

### Секции (сверху вниз):

**Секция KPI (6 карточек)** — класс `kpi-grid kpi-grid-6`:
- Всего задач, Выполнено (+ % от общего), В работе, Просрочено (warning), Требуют внимания (attention), Средний прогресс (с progress bar)

**Секция 1: Эффективность отделов** — `content-grid one`, stacked bar `#chart-dept-efficiency`, класс `chart-tall`

**Секция 2: Загрузка сотрудников** — `content-grid one`, таблица `dash-table #employee-table`:
- Столбцы: Сотрудник, Отдел, Всего, Выполнено, Просрочено (badge-red/badge-green), Прогресс (mini-progress bar с fill-low/mid/high), Загрузка (workload-badge)
- Строки с классами `row-warning` (overdue>0), `row-danger` (workload=overloaded)

**Секция 3: Приоритеты + Риски** — `content-grid two`, два doughnut: `#chart-priority`, `#chart-risk`

**Секция 4: Периоды + Прогресс** — `content-grid two`, bar `#chart-periods`, horizontal bar `#chart-dept-progress`

**Секция 5: ТОП проблемных задач** — `content-grid one`, таблица `dash-table #risky-table`:
- Заголовки с **Excel-фильтрами** (class `th-filter-select`): Отдел, Ответственный, Риск — select внутри th, автозаполняемые из данных через JS
- Строки с data-атрибутами: `data-dept`, `data-resp`, `data-risk`
- Критические задачи **первыми** (сортировка по risk_weight DESC)
- Столбец «Причина» — `risk_reason` усечённая до 12 слов

**Секция 6: Просрочки + Без ответственного** — `content-grid two`:
- Horizontal bar `#chart-overdue-dept`
- Список unassigned_tasks

### Блок `<script>` в конце шаблона:
- `window.__dashData` с данными для Chart.js (включая `priorityCodes`, `riskCodes`, `tasksUrl`)
- JS для автозаполнения фильтров таблицы risky-table (populate из Set)
- Функция `filterRiskyTasks()` — клиентская фильтрация строк по data-атрибутам

---

## 4. Charts.js (`static/js/charts.js`)

6 графиков Chart.js, читают из `window.__dashData`:

1. **chart-dept-efficiency** — stacked bar, x/y stacked, grid `#f0f4fa`, legend bottom
2. **chart-priority** — doughnut, cutout 62%, borderWidth 3, **onClick → навигация** `/tasks/?priority={code}`, **onHover → cursor pointer**
3. **chart-risk** — doughnut, cutout 62%, **onClick → навигация** `/tasks/?risk_level={code}`, **onHover → cursor pointer**
4. **chart-periods** — bar, цвета `["#020F52","#003C97","#269AE6","#9CDDE6"]`, borderRadius 10
5. **chart-dept-progress** — horizontal bar (indexAxis:"y"), динамические цвета (≥60 green, ≥30 yellow, else orange), max 100, tooltip с "%"
6. **chart-overdue-dept** — horizontal bar, цвет `#F97316`

Также есть generic charts для home.html (canvas с data-chart/data-labels/data-values атрибутами).

---

## 5. CSS стили (добавить в app.css)

```css
/* Dashboard: 6-column KPI grid */
.kpi-grid-6 { grid-template-columns: repeat(6, minmax(0, 1fr)); }
.kpi-sub { display: block; color: var(--muted); font-size: 13px; font-weight: 500; margin-top: 2px; }
.kpi-progress-bar {
  margin-top: 10px; height: 8px; border-radius: 99px;
  background: #E2E8F0; overflow: hidden;
}
.kpi-progress-fill {
  height: 100%; border-radius: 99px;
  background: linear-gradient(90deg, #003C97, #269AE6);
  transition: width .6s ease;
}

/* Dashboard: content-grid single column */
.content-grid.one { grid-template-columns: 1fr; }

/* Dashboard: chart containers */
.chart-container { position: relative; width: 100%; min-height: 260px; }
.chart-container.chart-tall { min-height: 340px; }
.chart-container canvas { max-height: 400px !important; }
.panel-hint { color: var(--muted); font-size: 13px; font-weight: 500; }

/* Dashboard: tables */
.dash-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.dash-table th {
  height: 44px; padding: 0 14px; text-align: left;
  color: var(--muted); font-weight: 700; white-space: nowrap;
  border-bottom: 2px solid var(--line); background: #FAFBFD;
}
.dash-table td { padding: 12px 14px; vertical-align: middle; border-bottom: 1px solid var(--line); }
.dash-table tr:last-child td { border-bottom: 0; }
.dash-table tr:hover { background: #f8fbff; }
.dash-table td:first-child { min-width: 160px; }

/* Row states */
.row-warning { background: #FFF7ED; }
.row-danger { background: #FEF2F2; }
.row-warning:hover { background: #FFF1DB !important; }
.row-danger:hover { background: #FEE2E2 !important; }

/* Mini progress bars (inside tables) */
.mini-progress {
  width: 80px; height: 6px; border-radius: 99px;
  background: #E2E8F0; overflow: hidden;
  display: inline-block; vertical-align: middle; margin-right: 6px;
}
.mini-progress-fill { height: 100%; border-radius: 99px; transition: width .5s ease; }
.fill-low { background: #F97316; }
.fill-mid { background: #FBBF24; }
.fill-high { background: #34D399; }

/* Workload badges */
.workload-badge {
  display: inline-flex; align-items: center;
  padding: 4px 10px; border-radius: 8px;
  font-size: 12px; font-weight: 700; white-space: nowrap;
}
.workload-normal { background: #F0FDF4; color: #15803D; }
.workload-high { background: #FEF3C7; color: #B45309; }
.workload-overloaded { background: #FEE2E2; color: #991B1B; }

/* Risk reason in table */
.risk-reason-cell { max-width: 280px; white-space: normal; color: #526176; font-size: 13px; line-height: 1.4; }

/* Overdue text */
.overdue-text { color: var(--red); font-weight: 700; }

/* Excel-like filter selects for tables */
.th-filter-select {
  appearance: none; -webkit-appearance: none;
  background: transparent url("data:image/svg+xml;charset=US-ASCII,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%2364748B' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") no-repeat right center;
  border: none; color: var(--muted); font-family: inherit;
  font-weight: 700; font-size: 14px; cursor: pointer;
  outline: none; padding: 0 16px 0 0;
}
.th-filter-select:hover { color: var(--blue); }
.th-filter-select option { color: var(--ink); font-weight: normal; }
```

Также в `@media (max-width: 1100px)` добавить `kpi-grid-6` и `content-grid.one` в строку с `grid-template-columns: 1fr`.

---

## 6. Интерактивность

### Клик по doughnut-графикам (Приоритеты / Риски)
При клике на сегмент → переход на `/tasks/?priority={code}` или `/tasks/?risk_level={code}`. Курсор меняется на pointer при наведении.

### Excel-фильтры в таблице «ТОП проблемных задач»
- Столбцы Отдел, Ответственный, Риск — `<select class="th-filter-select">` внутри `<th>`
- При загрузке страницы JS сканирует все строки `.risky-task-row`, собирает уникальные значения из data-атрибутов, заполняет `<option>` в каждом select
- При изменении select мгновенно фильтрует строки (display: none / "")

---

## 7. Ключевые моменты для точного воспроизведения

1. **Сортировка risky_tasks**: через `Case/When` аннотацию `risk_weight`, НЕ по текстовому полю risk_level (алфавитный порядок не совпадает с логическим)
2. **priority_codes и risk_codes** должны передаваться в контекст и в `window.__dashData` для работы кликов по графикам
3. **tasksUrl** передаётся через `{% url 'tasks:list' %}` в шаблоне
4. Все JSON-поля в контексте сериализуются с `ensure_ascii=False` для кириллицы
5. `risky_tasks` limit = 50, `unassigned` limit = 10
6. CSS переменные проекта: `--white`, `--surface`, `--ink`, `--blue`, `--digital`, `--light-blue`, `--line`, `--muted`, `--green`, `--orange`, `--red`

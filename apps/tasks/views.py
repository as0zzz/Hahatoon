import calendar as calendar_lib
from collections import defaultdict
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.audit.services import log_action
from apps.departments.models import Department
from apps.notifications.services import notify_task_assigned, notify_task_status_changed
from apps.tasks.forms import TaskCommentForm, TaskForm
from apps.tasks.models import Task, TaskHistory
from apps.tasks.services import filter_tasks, get_task_metrics, refresh_task_risk, task_queryset_for_user


@login_required
def task_list(request):
    queryset = filter_tasks(task_queryset_for_user(request.user), request.GET)
    paginator = Paginator(queryset, 12)
    page = paginator.get_page(request.GET.get("page"))
    query_without_page = request.GET.copy()
    query_without_page.pop("page", None)
    context = {
        "page_obj": page,
        "tasks": page.object_list,
        "departments": Department.objects.all(),
        "statuses": Task.Status.choices,
        "priorities": Task.Priority.choices,
        "risks": Task.Risk.choices,
        "periods": Task.PlanningPeriod.choices,
        "title": "Все задачи",
        "is_mine": False,
        "selected": request.GET,
        "query_without_page": query_without_page.urlencode(),
    }
    return render(request, "tasks/list.html", context)


@login_required
def my_tasks(request):
    queryset = task_queryset_for_user(request.user).filter(responsible=request.user)
    queryset = filter_tasks(queryset, request.GET)
    metrics = get_task_metrics(queryset)
    context = {
        "tasks": queryset,
        "departments": Department.objects.all(),
        "statuses": Task.Status.choices,
        "priorities": Task.Priority.choices,
        "risks": Task.Risk.choices,
        "periods": Task.PlanningPeriod.choices,
        "title": "Мои задачи",
        "is_mine": True,
        "profile": getattr(request.user, "profile", None),
        "task_metrics": metrics,
        "focus_tasks": queryset.exclude(status=Task.Status.DONE).order_by("deadline", "-priority")[:3],
        "selected": request.GET,
        "query_without_page": request.GET.urlencode(),
    }
    return render(request, "tasks/list.html", context)


@login_required
def task_detail(request, pk):
    task = get_object_or_404(task_queryset_for_user(request.user), pk=pk)
    refresh_task_risk(task)
    return render(
        request,
        "tasks/detail.html",
        {
            "title": task.title,
            "task": task,
            "comment_form": TaskCommentForm(),
            "history": task.history.select_related("user")[:20],
            "comments": task.comments.select_related("author")[:20],
        },
    )


@login_required
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.author = request.user
            task.last_status_change_at = timezone.now()
            task.save()
            form.save_m2m()
            refresh_task_risk(task)
            TaskHistory.objects.create(task=task, user=request.user, field_name="created", new_value="Задача создана")
            notify_task_assigned(task)
            log_action(request.user, "create", "Task", task.id, {"title": task.title}, request)
            messages.success(request, "Задача создана")
            return redirect("tasks:detail", pk=task.pk)
    else:
        initial_data = request.GET.dict()
        
        resp_str = initial_data.get("responsible", "").strip()
        if resp_str:
            from django.contrib.auth.models import User
            from django.db.models import Q
            # Try matching parts of the name
            parts = resp_str.split()
            q_objs = Q()
            for part in parts:
                q_objs |= Q(first_name__icontains=part) | Q(last_name__icontains=part) | Q(username__icontains=part)
            user_match = User.objects.filter(q_objs).first()
            if user_match:
                initial_data["responsible"] = user_match.id
            else:
                initial_data.pop("responsible", None)
                
        dept_str = initial_data.get("department", "").strip()
        if dept_str:
            from apps.departments.models import Department
            dept_match = None
            for word in dept_str.split():
                if len(word) > 4:
                    word = word[:4]
                dept_match = Department.objects.filter(name__icontains=word).first()
                if dept_match:
                    break
            if dept_match:
                initial_data["department"] = dept_match.id
            else:
                initial_data.pop("department", None)
                
        team_str = initial_data.get("team", "").strip()
        if team_str:
            from apps.departments.models import Team
            team_match = None
            for word in team_str.split():
                if len(word) > 4:
                    word = word[:4]
                team_match = Team.objects.filter(name__icontains=word).first()
                if team_match:
                    break
            if team_match:
                initial_data["team"] = team_match.id
            else:
                initial_data.pop("team", None)

        parent_task_str = initial_data.get("parent_task", "").strip()
        if parent_task_str:
            from apps.tasks.models import Task
            task_match = None
            for word in parent_task_str.split():
                if len(word) > 4:
                    word = word[:4]
                task_match = Task.objects.filter(title__icontains=word).first()
                if task_match:
                    break
            if task_match:
                initial_data["parent_task"] = task_match.id
            else:
                initial_data.pop("parent_task", None)

        watchers_list = request.GET.getlist("watchers")
        if watchers_list:
            from django.contrib.auth.models import User
            from django.db.models import Q
            resolved = []
            for w_str in watchers_list:
                w_str = w_str.strip()
                if not w_str: continue
                q_objs = Q()
                for part in w_str.split():
                    q_objs |= Q(first_name__icontains=part) | Q(last_name__icontains=part) | Q(username__icontains=part)
                user_match = User.objects.filter(q_objs).first()
                if user_match:
                    resolved.append(user_match.id)
            if resolved:
                initial_data["watchers"] = resolved
            else:
                initial_data.pop("watchers", None)

        form = TaskForm(initial=initial_data)
    return render(request, "tasks/form.html", {"form": form, "title": "Создание задачи"})


@login_required
def task_edit(request, pk):
    task = get_object_or_404(task_queryset_for_user(request.user), pk=pk)
    old_values = {field: getattr(task, field) for field in ["status", "priority", "deadline", "progress", "responsible_id"]}
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save()
            for field, old_value in old_values.items():
                new_value = getattr(task, field)
                if old_value != new_value:
                    TaskHistory.objects.create(task=task, user=request.user, field_name=field, old_value=old_value or "", new_value=new_value or "")
            if old_values["responsible_id"] != task.responsible_id:
                notify_task_assigned(task)
            if old_values["status"] != task.status:
                task.last_status_change_at = timezone.now()
                task.save(update_fields=["last_status_change_at"])
                notify_task_status_changed(task, old_values["status"])
            refresh_task_risk(task)
            log_action(request.user, "update", "Task", task.id, {"title": task.title}, request)
            messages.success(request, "Задача обновлена")
            return redirect("tasks:detail", pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, "tasks/form.html", {"form": form, "task": task, "title": "Редактирование задачи"})


@login_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(task_queryset_for_user(request.user), pk=pk)
    title = task.title
    log_action(request.user, "delete", "Task", task.id, {"title": title}, request)
    task.delete()
    messages.success(request, "Задача удалена")
    return redirect("tasks:list")


@login_required
@require_POST
def add_comment(request, pk):
    task = get_object_or_404(task_queryset_for_user(request.user), pk=pk)
    form = TaskCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.task = task
        comment.author = request.user
        comment.save()
        TaskHistory.objects.create(task=task, user=request.user, field_name="comment", new_value="Комментарий добавлен")
        refresh_task_risk(task)
        log_action(request.user, "comment", "Task", task.id, {}, request)
        messages.success(request, "Комментарий добавлен")
    return redirect("tasks:detail", pk=task.pk)


@login_required
@require_POST
def change_status(request, pk):
    task = get_object_or_404(task_queryset_for_user(request.user), pk=pk)
    new_status = request.POST.get("status")
    if new_status not in Task.Status.values:
        messages.error(request, "Некорректный статус")
        return redirect("tasks:detail", pk=task.pk)
    old_status = task.status
    task.status = new_status
    task.last_status_change_at = timezone.now()
    if new_status == Task.Status.DONE:
        task.progress = 100
    task.save(update_fields=["status", "last_status_change_at", "progress", "updated_at"])
    TaskHistory.objects.create(
        task=task,
        user=request.user,
        field_name="status",
        old_value=old_status,
        new_value=new_status,
    )
    refresh_task_risk(task)
    notify_task_status_changed(task, old_status)
    log_action(request.user, "change_status", "Task", task.id, {"from": old_status, "to": new_status}, request)
    messages.success(request, "Статус обновлён")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "status": task.status, "status_label": task.get_status_display()})
    return redirect("tasks:detail", pk=task.pk)


@login_required
def planning(request):
    tasks = task_queryset_for_user(request.user).select_related("parent_task", "department", "responsible")
    grouped = {period: tasks.filter(planning_period=period) for period, _ in Task.PlanningPeriod.choices}
    return render(request, "planning/index.html", {"grouped": grouped, "periods": Task.PlanningPeriod.choices, "title": "Планирование"})


@login_required
def kanban(request):
    kanban_statuses = [
        (Task.Status.NEW, "Новая"),
        (Task.Status.IN_PROGRESS, "В работе"),
        (Task.Status.REVIEW, "На согласовании"),
        (Task.Status.DONE, "Выполнена"),
        (Task.Status.OVERDUE, "Просрочена"),
    ]
    tasks = task_queryset_for_user(request.user).select_related("department", "responsible")
    columns = {status: tasks.filter(status=status) for status, _ in kanban_statuses}
    return render(request, "kanban/index.html", {"columns": columns, "statuses": kanban_statuses, "title": "Канбан"})


@login_required
def calendar(request):
    today = timezone.localdate()
    month = int(request.GET.get("month", today.month))
    year = int(request.GET.get("year", today.year))
    selected_iso = request.GET.get("date")
    selected_date = date.fromisoformat(selected_iso) if selected_iso else today
    if selected_date.month != month or selected_date.year != year:
        selected_date = date(year, month, 1)

    first_day = date(year, month, 1)
    previous_month_day = first_day - timedelta(days=1)
    next_month_day = date(year + (month // 12), (month % 12) + 1, 1)
    month_last_day = next_month_day - timedelta(days=1)

    tasks = task_queryset_for_user(request.user).filter(
        deadline__gte=first_day - timedelta(days=7),
        deadline__lte=month_last_day + timedelta(days=7),
    ).select_related("department", "responsible", "responsible__profile").order_by("deadline", "-priority")
    tasks_by_date = defaultdict(list)
    for task in tasks:
        tasks_by_date[task.deadline].append(task)

    weeks = []
    for week in calendar_lib.Calendar(firstweekday=0).monthdatescalendar(year, month):
        weeks.append(
            [
                {
                    "date": day,
                    "number": day.day,
                    "is_current_month": day.month == month,
                    "is_today": day == today,
                    "is_selected": day == selected_date,
                    "tasks": tasks_by_date.get(day, []),
                    "url": f"?year={day.year}&month={day.month}&date={day.isoformat()}",
                }
                for day in week
            ]
        )

    selected_tasks = tasks_by_date.get(selected_date, [])
    return render(
        request,
        "calendar/index.html",
        {
            "title": "Календарь задач",
            "weeks": weeks,
            "weekdays": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            "month_label": first_day.strftime("%B %Y").capitalize(),
            "selected_date": selected_date,
            "selected_tasks": selected_tasks,
            "previous_month": {"year": previous_month_day.year, "month": previous_month_day.month},
            "next_month": {"year": next_month_day.year, "month": next_month_day.month},
            "total_month_tasks": sum(1 for task in tasks if task.deadline.month == month and task.deadline.year == year),
        },
    )


def task_success_url(task):
    return reverse("tasks:detail", kwargs={"pk": task.pk})

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from apps.accounts.models import UserProfile
from apps.departments.models import Department
from apps.tasks.models import Task


@login_required
def employees(request):
    profiles = UserProfile.objects.select_related("user", "department", "team").annotate(
        total_tasks=Count("user__assigned_tasks", distinct=True),
        active_tasks=Count(
            "user__assigned_tasks",
            filter=Q(user__assigned_tasks__status__in=[Task.Status.NEW, Task.Status.IN_PROGRESS, Task.Status.REVIEW]),
            distinct=True,
        ),
        done_tasks=Count("user__assigned_tasks", filter=Q(user__assigned_tasks__status=Task.Status.DONE), distinct=True),
        overdue_tasks=Count("user__assigned_tasks", filter=Q(user__assigned_tasks__status=Task.Status.OVERDUE), distinct=True),
        high_tasks=Count(
            "user__assigned_tasks",
            filter=Q(user__assigned_tasks__priority__in=[Task.Priority.HIGH, Task.Priority.CRITICAL]),
            distinct=True,
        ),
    )

    # Search & filters
    q = request.GET.get("q", "").strip()
    dept = request.GET.get("department", "")
    workload = request.GET.get("workload", "")
    if q:
        profiles = profiles.filter(Q(full_name__icontains=q) | Q(position__icontains=q))
    if dept:
        profiles = profiles.filter(department_id=dept)
    if workload:
        profiles = profiles.filter(workload_index=workload)

    context = {
        "profiles": profiles,
        "title": "Сотрудники",
        "departments": Department.objects.all(),
        "workloads": UserProfile.Workload.choices,
        "selected": request.GET,
    }
    return render(request, "employees/index.html", context)


@login_required
def employee_detail(request, pk):
    profile = get_object_or_404(
        UserProfile.objects.select_related("user", "department", "team"),
        pk=pk,
    )
    tasks = Task.objects.filter(responsible=profile.user).select_related("department").order_by("deadline", "-priority")

    total = tasks.count()
    active = tasks.filter(status__in=[Task.Status.NEW, Task.Status.IN_PROGRESS, Task.Status.REVIEW]).count()
    done = tasks.filter(status=Task.Status.DONE).count()
    overdue = tasks.filter(status=Task.Status.OVERDUE).count()

    context = {
        "profile": profile,
        "tasks": tasks,
        "title": profile.full_name,
        "stats": {"total": total, "active": active, "done": done, "overdue": overdue},
    }
    return render(request, "employees/detail.html", context)


@login_required
def departments(request):
    items = Department.objects.select_related("manager").annotate(
        total_tasks=Count("tasks", distinct=True),
        attention_tasks=Count("tasks", filter=Q(tasks__needs_manager_attention=True), distinct=True),
        employees_count=Count("employees", distinct=True),
    )

    q = request.GET.get("q", "").strip()
    if q:
        items = items.filter(Q(name__icontains=q) | Q(description__icontains=q))

    context = {
        "departments": items,
        "title": "Отделы",
        "selected": request.GET,
    }
    return render(request, "departments/index.html", context)


@login_required
def department_detail(request, pk):
    department = get_object_or_404(Department, pk=pk)
    tasks = department.tasks.select_related("responsible").all()
    return render(request, "departments/detail.html", {"department": department, "tasks": tasks, "title": department.name})


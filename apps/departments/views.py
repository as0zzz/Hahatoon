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
    return render(request, "employees/index.html", {"profiles": profiles, "title": "Сотрудники"})


@login_required
def departments(request):
    items = Department.objects.select_related("manager").annotate(
        total_tasks=Count("tasks", distinct=True),
        attention_tasks=Count("tasks", filter=Q(tasks__needs_manager_attention=True), distinct=True),
        employees_count=Count("employees", distinct=True),
    )
    return render(request, "departments/index.html", {"departments": items, "title": "Отделы"})


@login_required
def department_detail(request, pk):
    department = get_object_or_404(Department, pk=pk)
    tasks = department.tasks.select_related("responsible").all()
    return render(request, "departments/detail.html", {"department": department, "tasks": tasks, "title": department.name})

# Create your views here.

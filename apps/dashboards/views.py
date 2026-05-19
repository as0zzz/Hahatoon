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

# Create your views here.

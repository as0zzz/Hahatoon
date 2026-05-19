from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from openpyxl import Workbook

from apps.reports.models import Report
from apps.reports.services import create_weekly_report


@login_required
def index(request):
    reports = Report.objects.select_related("department", "employee", "created_by")
    return render(request, "reports/index.html", {"reports": reports, "title": "Отчёты"})


@login_required
def create(request):
    report = create_weekly_report(request.user)
    messages.success(request, "Отчёт сформирован")
    return redirect("reports:index")


@login_required
def export_excel(request):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Отчёты TTM"
    sheet.append(["Название", "Период", "Начало", "Конец", "Создано"])
    for report in Report.objects.all():
        sheet.append([report.title, report.get_period_type_display(), report.period_start, report.period_end, report.created_at.date()])
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="ttm-reports.xlsx"'
    workbook.save(response)
    return response

# Create your views here.

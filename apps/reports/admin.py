from django.contrib import admin

from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "period_type", "department", "employee", "created_by", "created_at")
    list_filter = ("period_type", "department")
    search_fields = ("title", "content")

# Register your models here.

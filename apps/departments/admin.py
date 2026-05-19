from django.contrib import admin

from apps.departments.models import Department, Team


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "manager", "updated_at")
    search_fields = ("name", "description")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "lead")
    list_filter = ("department",)
    search_fields = ("name",)

# Register your models here.

from django.contrib import admin

from apps.tasks.models import Task, TaskComment, TaskHistory


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "responsible", "planning_period", "status", "priority", "risk_level", "deadline")
    list_filter = ("status", "priority", "risk_level", "planning_period", "department")
    search_fields = ("title", "description", "tags")
    autocomplete_fields = ("responsible", "author", "department", "team", "parent_task")


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "created_at")
    search_fields = ("task__title", "text")


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ("task", "field_name", "old_value", "new_value", "user", "created_at")
    list_filter = ("field_name",)

# Register your models here.

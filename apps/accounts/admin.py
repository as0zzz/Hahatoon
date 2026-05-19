from django.contrib import admin

from apps.accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position", "department", "role", "workload_index")
    list_filter = ("role", "workload_index", "department")
    search_fields = ("full_name", "position", "user__username")

# Register your models here.

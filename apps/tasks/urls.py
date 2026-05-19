from django.urls import path

from apps.tasks import views

app_name = "tasks"

urlpatterns = [
    path("mine/", views.my_tasks, name="mine"),
    path("", views.task_list, name="list"),
    path("create/", views.task_create, name="create"),
    path("<int:pk>/", views.task_detail, name="detail"),
    path("<int:pk>/edit/", views.task_edit, name="edit"),
    path("<int:pk>/delete/", views.task_delete, name="delete"),
    path("<int:pk>/comment/", views.add_comment, name="add_comment"),
    path("<int:pk>/change-status/", views.change_status, name="change_status"),
]

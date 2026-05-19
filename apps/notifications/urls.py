from django.urls import path

from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.notifications, name="list"),
    path("read-all/", views.mark_all_read, name="read_all"),
    path("<int:pk>/read/", views.read_notification, name="read"),
]

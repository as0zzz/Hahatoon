from django.urls import path

from apps.ai_assistant import views

app_name = "ai"

urlpatterns = [
    path("", views.index, name="index"),
    path("ask/", views.ask, name="ask"),
    path("report/", views.report, name="report"),
    path("extract-task/", views.extract_task, name="extract_task"),
]

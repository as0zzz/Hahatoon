from django.urls import path

from apps.reports import views

app_name = "reports"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/", views.create, name="create"),
    path("export/excel/", views.export_excel, name="export_excel"),
]

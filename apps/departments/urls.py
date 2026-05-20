from django.urls import path

from apps.departments import views

app_name = "departments"

urlpatterns = [
    path("employees/", views.employees, name="employees"),
    path("employees/<int:pk>/", views.employee_detail, name="employee_detail"),
    path("", views.departments, name="list"),
    path("<int:pk>/", views.department_detail, name="detail"),
]

from django.conf import settings
from django.db import models

from apps.departments.models import Department, Team


class UserProfile(models.Model):
    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Сотрудник"
        TEAM_LEAD = "team_lead", "Руководитель команды"
        DEPARTMENT_HEAD = "department_head", "Руководитель подразделения"
        ADMIN = "admin", "Администратор"

    class Workload(models.TextChoices):
        NORMAL = "normal", "Нормальная"
        HIGH = "high", "Высокая"
        OVERLOADED = "overloaded", "Перегрузка"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField("ФИО", max_length=160)
    position = models.CharField("Должность", max_length=160)
    department = models.ForeignKey(
        Department,
        verbose_name="Отдел",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="employees",
    )
    team = models.ForeignKey(
        Team,
        verbose_name="Команда",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="employees",
    )
    role = models.CharField("Роль", max_length=32, choices=Role.choices, default=Role.EMPLOYEE)
    avatar = models.ImageField("Аватар", upload_to="avatars/", blank=True)
    workload_index = models.CharField(
        "Индекс загрузки",
        max_length=32,
        choices=Workload.choices,
        default=Workload.NORMAL,
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["department__name", "full_name"]
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return self.full_name or self.user.get_username()

# Create your models here.

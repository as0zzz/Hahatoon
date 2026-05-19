from django.conf import settings
from django.db import models

from apps.departments.models import Department


class Report(models.Model):
    class Period(models.TextChoices):
        WEEK = "week", "Неделя"
        MONTH = "month", "Месяц"
        QUARTER = "quarter", "Квартал"
        YEAR = "year", "Год"

    title = models.CharField("Название", max_length=200)
    period_type = models.CharField("Период", max_length=16, choices=Period.choices, default=Period.WEEK)
    period_start = models.DateField("Начало периода")
    period_end = models.DateField("Конец периода")
    department = models.ForeignKey(
        Department,
        verbose_name="Отдел",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reports",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Сотрудник",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="employee_reports",
    )
    content = models.TextField("Содержание")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Создал",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_reports",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Отчёт"
        verbose_name_plural = "Отчёты"

    def __str__(self):
        return self.title

# Create your models here.

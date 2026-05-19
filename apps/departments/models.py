from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    description = models.TextField("Описание", blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Руководитель",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="managed_departments",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField("Название", max_length=120)
    department = models.ForeignKey(
        Department,
        verbose_name="Отдел",
        on_delete=models.CASCADE,
        related_name="teams",
    )
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Руководитель команды",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="led_teams",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["department__name", "name"]
        unique_together = [("name", "department")]
        verbose_name = "Команда"
        verbose_name_plural = "Команды"

    def __str__(self):
        return f"{self.name} / {self.department.name}"

# Create your models here.

from django.conf import settings
from django.db import models

from apps.tasks.models import Task


class Notification(models.Model):
    class Type(models.TextChoices):
        INFO = "info", "Информация"
        RISK = "risk", "Риск"
        DEADLINE = "deadline", "Дедлайн"
        STATUS = "status", "Статус"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Получатель",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField("Заголовок", max_length=160)
    message = models.TextField("Сообщение")
    type = models.CharField("Тип", max_length=24, choices=Type.choices, default=Type.INFO)
    task = models.ForeignKey(
        Task,
        verbose_name="Задача",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="notifications",
    )
    is_read = models.BooleanField("Прочитано", default=False)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    def __str__(self):
        return self.title

# Create your models here.

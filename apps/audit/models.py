from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="audit_logs",
    )
    action = models.CharField("Действие", max_length=160)
    object_type = models.CharField("Тип объекта", max_length=80)
    object_id = models.CharField("ID объекта", max_length=80, blank=True)
    payload = models.JSONField("Данные", default=dict, blank=True)
    ip_address = models.GenericIPAddressField("IP-адрес", blank=True, null=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Запись аудита"
        verbose_name_plural = "Журнал аудита"

    def __str__(self):
        return f"{self.action} / {self.object_type}"

# Create your models here.

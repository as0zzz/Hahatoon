from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.departments.models import Department, Team


class Task(models.Model):
    class PlanningPeriod(models.TextChoices):
        YEAR = "year", "Год"
        QUARTER = "quarter", "Квартал"
        MONTH = "month", "Месяц"
        WEEK = "week", "Неделя"

    class Priority(models.TextChoices):
        LOW = "low", "Низкий"
        MEDIUM = "medium", "Средний"
        HIGH = "high", "Высокий"
        CRITICAL = "critical", "Критический"

    class Status(models.TextChoices):
        NEW = "new", "Новая"
        PLANNED = "planned", "Запланирована"
        IN_PROGRESS = "in_progress", "В работе"
        REVIEW = "review", "На согласовании"
        DONE = "done", "Выполнена"
        OVERDUE = "overdue", "Просрочена"
        CANCELLED = "cancelled", "Отменена"

    class Risk(models.TextChoices):
        LOW = "low", "Низкий"
        MEDIUM = "medium", "Средний"
        HIGH = "high", "Высокий"
        CRITICAL = "critical", "Критический"

    title = models.CharField("Название", max_length=240)
    description = models.TextField("Описание", blank=True)
    department = models.ForeignKey(
        Department,
        verbose_name="Отдел",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tasks",
    )
    team = models.ForeignKey(
        Team,
        verbose_name="Команда",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tasks",
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Ответственный",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assigned_tasks",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_tasks",
    )
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Наблюдатели",
        blank=True,
        related_name="watched_tasks",
    )
    planning_period = models.CharField(
        "Период планирования",
        max_length=16,
        choices=PlanningPeriod.choices,
        default=PlanningPeriod.WEEK,
    )
    parent_task = models.ForeignKey(
        "self",
        verbose_name="Родительская задача",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="children",
    )
    annual_goal = models.CharField("Годовая цель", max_length=240, blank=True)
    deadline = models.DateField("Дедлайн", blank=True, null=True)
    priority = models.CharField("Приоритет", max_length=16, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField("Статус", max_length=24, choices=Status.choices, default=Status.NEW)
    risk_level = models.CharField("Риск", max_length=16, choices=Risk.choices, default=Risk.LOW)
    risk_reason = models.TextField("Причина риска", blank=True)
    risk_recommendation = models.TextField("Рекомендация", blank=True)
    progress = models.PositiveSmallIntegerField("Прогресс, %", default=0)
    tags = models.CharField("Теги", max_length=240, blank=True)
    estimated_hours = models.PositiveSmallIntegerField("Плановые часы", default=0)
    actual_hours = models.PositiveSmallIntegerField("Фактические часы", default=0)
    needs_manager_attention = models.BooleanField("Требует внимания руководителя", default=False)
    last_status_change_at = models.DateTimeField("Последнее изменение статуса", default=timezone.now)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["deadline", "-updated_at"]
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"

    def __str__(self):
        return self.title

    @property
    def is_closed(self):
        return self.status == self.Status.DONE

    @property
    def is_overdue(self):
        return bool(self.deadline and self.deadline < timezone.localdate() and not self.is_closed)


class TaskComment(models.Model):
    task = models.ForeignKey(Task, verbose_name="Задача", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="task_comments",
    )
    text = models.TextField("Комментарий")
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Комментарий к задаче"
        verbose_name_plural = "Комментарии к задачам"

    def __str__(self):
        return f"Комментарий к {self.task_id}"


class TaskHistory(models.Model):
    task = models.ForeignKey(Task, verbose_name="Задача", on_delete=models.CASCADE, related_name="history")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="task_history_items",
    )
    field_name = models.CharField("Поле", max_length=80)
    old_value = models.CharField("Было", max_length=240, blank=True)
    new_value = models.CharField("Стало", max_length=240, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "История задачи"
        verbose_name_plural = "История задач"

    def __str__(self):
        return f"{self.task_id}: {self.field_name}"

# Create your models here.

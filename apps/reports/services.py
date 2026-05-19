from datetime import timedelta

from django.utils import timezone

from apps.reports.models import Report
from apps.tasks.services import get_task_metrics


def create_weekly_report(user=None, department=None):
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    metrics = get_task_metrics()
    content = (
        f"Всего задач: {metrics['total']}. Выполнено: {metrics['done']}. "
        f"Просрочено: {metrics['overdue']}. Требуют внимания: {metrics['attention']}.\n\n"
        "Рекомендации: обновить статусы, закрыть просрочки, проверить загрузку сотрудников."
    )
    return Report.objects.create(
        title=f"Недельный отчёт TTM {start:%d.%m.%Y}",
        period_type=Report.Period.WEEK,
        period_start=start,
        period_end=end,
        department=department,
        content=content,
        created_by=user,
    )

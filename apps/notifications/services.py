from apps.notifications.models import Notification


def create_notification(recipient, title, message, type=Notification.Type.INFO, task=None):
    if not recipient:
        return None
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        type=type,
        task=task,
    )


def notify_task_assigned(task):
    return create_notification(
        task.responsible,
        "Новая задача",
        f"Вам назначена задача «{task.title}».",
        type=Notification.Type.INFO,
        task=task,
    )


def notify_task_status_changed(task, old_status=None):
    return create_notification(
        task.responsible,
        "Изменён статус задачи",
        f"Задача «{task.title}» переведена в статус «{task.get_status_display()}».",
        type=Notification.Type.STATUS,
        task=task,
    )

from apps.notifications.models import Notification


def notifications_summary(request):
    if not request.user.is_authenticated:
        return {"recent_notifications": [], "unread_notifications_count": 0}

    queryset = Notification.objects.filter(recipient=request.user).select_related("task")
    return {
        "recent_notifications": queryset[:6],
        "unread_notifications_count": queryset.filter(is_read=False).count(),
    }

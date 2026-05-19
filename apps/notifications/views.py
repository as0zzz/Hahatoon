from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.notifications.models import Notification


@login_required
def notifications(request):
    items = Notification.objects.filter(recipient=request.user).select_related("task")
    return render(request, "notifications/index.html", {"notifications": items, "title": "Уведомления"})


@login_required
def read_notification(request, pk):
    item = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not item.is_read:
        item.is_read = True
        item.save(update_fields=["is_read"])
    if item.task_id:
        return redirect("tasks:detail", pk=item.task_id)
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect(request.POST.get("next") or "notifications:list")

# Create your views here.

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def settings_view(request):
    sections = [
        "Профиль пользователя",
        "Уведомления",
        "Роли и права",
        "Отделы",
        "Сотрудники",
        "Статусы задач",
        "Приоритеты",
        "Периоды планирования",
        "Интеграции",
        "AI-настройки",
        "Экспорт данных",
        "Аудит действий",
        "Суверенность и корпоративный контур",
    ]
    return render(request, "settings/index.html", {"sections": sections, "title": "Настройки"})

# Create your views here.

from apps.notifications.services import create_notification
from apps.notifications.models import Notification
from django.shortcuts import redirect
from django.contrib import messages

@login_required
def test_notification(request):
    if request.method == "POST":
        create_notification(
            recipient=request.user,
            title="Тестовое уведомление",
            message="Это уведомление было отправлено вручную из настроек системы.",
            type=Notification.Type.INFO
        )
        messages.success(request, "Тестовое уведомление успешно отправлено!")
    return redirect('settings')

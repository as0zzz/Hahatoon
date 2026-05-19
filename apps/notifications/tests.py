from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.notifications.models import Notification
from apps.tasks.models import Task


class NotificationFlowTests(TestCase):
    def setUp(self):
        call_command("seed_data", verbosity=0)
        self.user = User.objects.get(username="ivan")
        self.task = Task.objects.filter(responsible=self.user).first()

    def test_notification_read_link_marks_item_and_opens_task(self):
        notification = Notification.objects.create(
            recipient=self.user,
            title="Новая задача",
            message=f"Вам назначена задача «{self.task.title}».",
            task=self.task,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("notifications:read", args=[notification.id]))

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertRedirects(response, reverse("tasks:detail", args=[self.task.id]))

    def test_mark_all_read_updates_unread_counter(self):
        Notification.objects.create(recipient=self.user, title="Событие", message="Текст")
        self.client.force_login(self.user)

        response = self.client.post(reverse("notifications:read_all"))

        self.assertRedirects(response, reverse("notifications:list"))
        self.assertFalse(Notification.objects.filter(recipient=self.user, is_read=False).exists())

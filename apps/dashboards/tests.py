from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(AI_MOCK_MODE=True)
class MainPagesSmokeTests(TestCase):
    def setUp(self):
        call_command("seed_data", verbosity=0)
        self.client.force_login(User.objects.get(username="ivan"))

    def test_core_pages_open_with_russian_interface(self):
        routes = [
            "home",
            "tasks:mine",
            "tasks:list",
            "planning",
            "kanban",
            "calendar",
            "dashboards:index",
            "ai:index",
            "departments:employees",
            "departments:list",
            "reports:index",
            "notifications:list",
            "settings",
            "audit:list",
        ]

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "TTM")

    def test_calendar_uses_month_grid_and_day_panel(self):
        response = self.client.get(reverse("calendar"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "calendar-month-grid")
        self.assertContains(response, "selected-day-panel")
        self.assertContains(response, "Задачи на день")

    def test_public_pages_do_not_call_product_staging(self):
        self.client.logout()
        login_response = self.client.get(reverse("login"))

        self.assertNotContains(login_response, "Демо")
        self.assertNotContains(login_response, "демо")

        self.client.force_login(User.objects.get(username="ivan"))
        settings_response = self.client.get(reverse("settings"))
        self.assertNotContains(settings_response, "демо")
        self.assertNotContains(settings_response, "демонстра")

    def test_all_tasks_filter_by_department_and_status(self):
        response = self.client.get(
            reverse("tasks:list"),
            {"department": "HR", "status": "in_progress", "q": "отчёт"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Все задачи")
        self.assertContains(response, "Применить")

# Create your tests here.

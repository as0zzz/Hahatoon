from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.departments.models import Department, Team
from apps.reports.models import Report
from apps.tasks.models import Task, TaskComment, TaskHistory
from apps.tasks.services import refresh_task_risk


class TaskRiskTests(TestCase):
    def test_overdue_critical_task_gets_critical_risk_and_attention_flag(self):
        department = Department.objects.create(name="ИТ", description="Инфраструктура")
        user = User.objects.create_user(username="dmitry", password="ttm1234", first_name="Дмитрий")
        UserProfile.objects.create(
            user=user,
            full_name="Дмитрий",
            position="Системный администратор",
            department=department,
            role=UserProfile.Role.EMPLOYEE,
            workload_index=UserProfile.Workload.OVERLOADED,
        )
        task = Task.objects.create(
            title="Проверить журнал ошибок внутреннего портала",
            department=department,
            responsible=user,
            author=user,
            planning_period=Task.PlanningPeriod.WEEK,
            deadline=timezone.now().date() - timedelta(days=1),
            priority=Task.Priority.CRITICAL,
            status=Task.Status.IN_PROGRESS,
            progress=10,
        )

        risk = refresh_task_risk(task)
        task.refresh_from_db()

        self.assertEqual(risk["level"], Task.Risk.CRITICAL)
        self.assertTrue(task.needs_manager_attention)
        self.assertIn("дедлайн", task.risk_reason.lower())
        self.assertIn("обновить", task.risk_recommendation.lower())


class DemoDataTests(TestCase):
    def test_seed_data_creates_idempotent_hackathon_dataset(self):
        call_command("seed_data", verbosity=0)
        first_task_count = Task.objects.count()

        self.assertGreaterEqual(first_task_count, 35)
        self.assertEqual(User.objects.filter(username="ivan").count(), 1)
        self.assertTrue(User.objects.filter(username="admin", is_superuser=True).exists())
        self.assertGreaterEqual(Department.objects.count(), 7)
        self.assertGreaterEqual(Team.objects.count(), 7)
        self.assertGreaterEqual(TaskComment.objects.count(), 5)
        self.assertGreaterEqual(TaskHistory.objects.count(), 5)
        self.assertGreaterEqual(Report.objects.count(), 1)

        call_command("seed_data", verbosity=0)
        self.assertEqual(Task.objects.count(), first_task_count)


class TaskWorkflowTests(TestCase):
    def setUp(self):
        call_command("seed_data", verbosity=0)
        self.user = User.objects.get(username="ivan")
        self.client.force_login(self.user)
        self.department = Department.objects.get(name="Направление молодых талантов")

    def test_create_comment_status_change_and_delete_task_workflow(self):
        create_response = self.client.post(
            reverse("tasks:create"),
            {
                "title": "Подготовить итоговую презентацию для хакатона",
                "description": "Собрать слайды по задачам, рискам и дашбордам.",
                "department": self.department.id,
                "responsible": self.user.id,
                "author": self.user.id,
                "planning_period": Task.PlanningPeriod.WEEK,
                "deadline": (timezone.localdate() + timedelta(days=3)).isoformat(),
                "priority": Task.Priority.HIGH,
                "status": Task.Status.NEW,
                "progress": 0,
            },
            follow=True,
        )
        self.assertEqual(create_response.status_code, 200)
        task = Task.objects.get(title="Подготовить итоговую презентацию для хакатона")
        self.assertEqual(task.risk_level, Task.Risk.MEDIUM)

        comment_response = self.client.post(
            reverse("tasks:add_comment", args=[task.id]),
            {"text": "Материалы собраны, ждём финальные цифры по KPI."},
            follow=True,
        )
        self.assertEqual(comment_response.status_code, 200)
        self.assertTrue(task.comments.filter(text__contains="Материалы собраны").exists())

        status_response = self.client.post(
            reverse("tasks:change_status", args=[task.id]),
            {"status": Task.Status.IN_PROGRESS},
            follow=True,
        )
        self.assertEqual(status_response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.IN_PROGRESS)
        self.assertTrue(TaskHistory.objects.filter(task=task, field_name="status").exists())

        delete_response = self.client.post(reverse("tasks:delete", args=[task.id]), follow=True)
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Task.objects.filter(id=task.id).exists())

# Create your tests here.

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from apps.ai_assistant.services import AIAssistantService
from apps.tasks.models import Task


class AIAssistantMockTests(TestCase):
    def setUp(self):
        call_command("seed_data", verbosity=0)
        self.user = User.objects.get(username="ivan")

    @override_settings(AI_MOCK_MODE=True, GEMINI_API_KEY="")
    def test_mock_mode_returns_provider_error_without_local_answer(self):
        service = AIAssistantService()
        answer = service.answer("Кто перегружен на этой неделе?", user=self.user)

        self.assertIn("Ошибка", answer)
        self.assertIn("Gemini", answer)
        self.assertNotIn("Рекомендация", answer)

    @override_settings(AI_MOCK_MODE=True, GEMINI_API_KEY="")
    def test_weekly_report_and_task_extraction_require_gemini(self):
        service = AIAssistantService()
        report = service.weekly_report(user=self.user)
        extracted = service.extract_task(
            "Нужно до пятницы подготовить отчёт по затратам подразделения, ответственная Елена, отдел Финансы, высокий приоритет."
        )

        self.assertIn("Ошибка", report)
        self.assertIn("error", extracted)
        self.assertIn("Gemini", extracted["error"])

    @override_settings(AI_MOCK_MODE=False, GEMINI_API_KEY="test-key")
    def test_gemini_provider_failure_returns_error_without_local_answer(self):
        service = AIAssistantService()

        with patch.object(service, "_gemini_answer", side_effect=RuntimeError("provider unavailable")):
            answer = service.answer("Какие задачи требуют внимания?", user=self.user)

        self.assertIn("Ошибка", answer)
        self.assertIn("Gemini", answer)
        self.assertNotIn("Рекомендация", answer)

    @override_settings(AI_MOCK_MODE=False, GEMINI_API_KEY="test-key")
    def test_gemini_prompt_contains_project_task_context(self):
        service = AIAssistantService()

        prompt = service._build_prompt("Кто перегружен на этой неделе?", self.user)

        self.assertIn("У тебя есть доступ", prompt)
        self.assertIn("Общие метрики:", prompt)
        self.assertIn("Задачи для анализа:", prompt)
        self.assertIn("не отвечай, что у тебя нет доступа".lower(), prompt.lower())

    @override_settings(AI_MOCK_MODE=False, GEMINI_API_KEY="test-key")
    def test_department_question_uses_gemini_answer(self):
        service = AIAssistantService()

        with patch.object(service, "_gemini_answer", return_value="В отделе «Финансы» 5 задач.\nРекомендация: начать с просрочек.") as provider:
            answer = service.answer("Какие задачи у отдела Финансы?", user=self.user)

        self.assertIn("Финансы", answer)
        self.assertIn("задач", answer.lower())
        self.assertIn("Рекомендация", answer)
        self.assertLess(len(answer), 1200)
        provider.assert_called_once()

    @override_settings(AI_MOCK_MODE=False, GEMINI_API_KEY="test-key")
    def test_off_topic_question_is_rejected_without_provider_call(self):
        service = AIAssistantService()

        with patch.object(service, "_gemini_answer", side_effect=AssertionError("provider should not be called")):
            answer = service.answer("Как приготовить пасту карбонара?", user=self.user)

        self.assertIn("только", answer.lower())
        self.assertIn("TTM", answer)

    @override_settings(AI_MOCK_MODE=False, GEMINI_API_KEY="test-key")
    def test_ai_page_without_question_does_not_call_external_provider(self):
        self.client.force_login(self.user)

        with patch("apps.ai_assistant.services.AIAssistantService._gemini_answer", side_effect=RuntimeError("external call")) as provider:
            response = self.client.get(reverse("ai:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI-помощник")
        provider.assert_not_called()

    @override_settings(AI_MOCK_MODE=False, GEMINI_API_KEY="test-key")
    def test_ai_page_with_get_question_renders_gemini_answer(self):
        self.client.force_login(self.user)

        with patch("apps.ai_assistant.services.AIAssistantService._gemini_answer", return_value="В отделе «Финансы» 5 задач.\nРекомендация: начать с просрочек."):
            response = self.client.get(reverse("ai:index"), {"question": "Какие задачи у отдела Финансы?"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Какие задачи у отдела Финансы?")
        self.assertContains(response, "Рекомендация")

# Create your tests here.

import re

from django.conf import settings

from apps.ai_assistant.prompts import SYSTEM_PROMPT
from apps.tasks.models import Task
from apps.tasks.services import get_task_metrics, task_queryset_for_user


class AIAssistantService:
    def __init__(self):
        self.mock_mode = settings.AI_MOCK_MODE or not settings.GEMINI_API_KEY

    def answer(self, question, user=None):
        question = (question or "").strip()
        if self.mock_mode:
            return self._mock_answer(question, user)
        try:
            return self._gemini_answer(question, user)
        except Exception as e:
            return f"⚠️ Ошибка подключения к AI (возможно, блокировка API или неверный ключ): {str(e)}\n\n---\n\n" + self._mock_answer(question, user)

    def weekly_report(self, user=None):
        question = "Сформируй недельный управленческий отчёт по задачам TTM: состояние, риски, перегрузка, рекомендации."
        if not self.mock_mode:
            try:
                return self._gemini_answer(question, user)
            except Exception:
                pass
        return self._mock_answer(question, user)

    def local_overview(self):
        return self._mock_answer("Какие задачи требуют внимания?", None)

    def extract_task(self, text):
        text = (text or "").strip()
        responsible = self._extract_after(text, r"ответственн(?:ая|ый|ые)?\s+([А-ЯЁA-Z][а-яёa-z]+)")
        department = self._extract_after(text, r"отдел\s+([А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z\s]+?)(?:,|\.|$)")
        priority = Task.Priority.HIGH if "высок" in text.lower() else Task.Priority.MEDIUM
        title = "Подготовить отчёт по затратам подразделения" if "отч" in text.lower() else text[:120]
        return {
            "title": title,
            "description": text,
            "responsible": responsible or "",
            "department": (department or "").strip(),
            "priority": priority,
            "status": Task.Status.NEW,
            "deadline_text": "до пятницы" if "пятниц" in text.lower() else "",
            "planning_period": Task.PlanningPeriod.WEEK,
        }

    def risky_tasks_summary(self):
        tasks = Task.objects.filter(needs_manager_attention=True).order_by("deadline")[:6]
        if not tasks:
            return "Сейчас нет задач с высоким риском. Рекомендуется поддерживать регулярное обновление статусов."
        lines = [f"- {task.title}: {task.get_risk_level_display()}, {task.risk_reason}" for task in tasks]
        return "Задачи в зоне внимания:\n" + "\n".join(lines)

    def _mock_answer(self, question, user=None):
        queryset = self._visible_tasks(user)
        metrics = get_task_metrics(queryset)
        lowered = question.lower()
        risky = list(queryset.filter(needs_manager_attention=True).select_related("department", "responsible", "responsible__profile")[:4])
        risky_lines = "\n".join(
            f"- {task.title}: {task.get_risk_level_display()}, {task.department.name if task.department else 'без отдела'}, дедлайн {task.deadline or 'не указан'}"
            for task in risky
        )
        if "перегруж" in lowered or "загруз" in lowered:
            workload = ", ".join(f"{name}: {count}" for name, count in metrics["workload"][:4])
            return (
                f"По текущим задачам повышенная загрузка видна у сотрудников: {workload or 'нет явного перегруза по назначенным задачам'}.\n\n"
                "Рекомендация руководителю:\n"
                "1. Проверить ближайшие дедлайны у этих сотрудников.\n"
                "2. Перенести часть задач среднего приоритета на менее загруженных участников.\n"
                "3. Оставить в фокусе только задачи с высоким приоритетом и риском."
            )
        if "просроч" in lowered or "риск" in lowered:
            prefix = "Недельный отчёт TTM\n\n" if "отч" in lowered else ""
            return (
                prefix +
                f"В зоне внимания {metrics['attention']} задач, просрочено {metrics['overdue']}.\n\n"
                f"{risky_lines or 'Критичных задач в текущем срезе нет.'}\n\n"
                "Рекомендация: сначала разобрать задачи с ближайшим дедлайном, затем обновить статусы и ответственных."
            )
        return (
            f"Сводка по текущему срезу: всего {metrics['total']} задач, выполнено {metrics['done']}, "
            f"требуют внимания {metrics['attention']}, высокий приоритет у {metrics['high_priority']}.\n\n"
            "Рекомендация: закрыть просрочки, уточнить статусы задач без прогресса и проверить загрузку ответственных."
        )

    def _gemini_answer(self, question, user=None):
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            settings.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            generation_config={"temperature": 0.25, "top_p": 0.8, "max_output_tokens": 900},
        )
        prompt = self._build_prompt(question, user)
        response = model.generate_content(prompt, request_options={"timeout": 12})
        return response.text

    def _visible_tasks(self, user=None):
        if user and getattr(user, "is_authenticated", False):
            return task_queryset_for_user(user).select_related("department", "responsible", "responsible__profile")
        return Task.objects.all().select_related("department", "responsible", "responsible__profile")

    def _build_prompt(self, question, user=None):
        queryset = self._visible_tasks(user)
        metrics = get_task_metrics(queryset)
        tasks = queryset.order_by("deadline", "-priority")[:25]
        workload = "; ".join(f"{name}: {count}" for name, count in metrics["workload"][:8]) or "нет назначенных задач"
        task_lines = []
        for task in tasks:
            task_lines.append(
                "- "
                f"{task.title} | отдел: {task.department.name if task.department else 'не указан'} | "
                f"ответственный: {getattr(getattr(task.responsible, 'profile', None), 'full_name', None) or getattr(task.responsible, 'username', 'не назначен')} | "
                f"статус: {task.get_status_display()} | приоритет: {task.get_priority_display()} | "
                f"дедлайн: {task.deadline or 'не указан'} | прогресс: {task.progress}% | "
                f"риск: {task.get_risk_level_display()} {task.risk_reason or ''}"
            )
        return (
            "У тебя есть доступ к нижеследующему минимальному срезу данных TTM. "
            "Не отвечай, что у тебя нет доступа к задачам: используй только эти данные.\n\n"
            f"Вопрос пользователя: {question}\n\n"
            "Метрики:\n"
            f"- всего задач: {metrics['total']}\n"
            f"- выполнено: {metrics['done']}\n"
            f"- просрочено: {metrics['overdue']}\n"
            f"- требуют внимания руководителя: {metrics['attention']}\n"
            f"- высокий приоритет: {metrics['high_priority']}\n"
            f"- загрузка: {workload}\n\n"
            "Задачи:\n"
            + "\n".join(task_lines)
            + "\n\nОтветь по-русски. Отвечай кратко, чётко и строго по делу (без воды). Дай короткий вывод и 1-3 конкретных действия."
        )

    @staticmethod
    def _extract_after(text, pattern):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else ""

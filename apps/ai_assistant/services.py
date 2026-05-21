import re

from django.conf import settings

from apps.ai_assistant.prompts import SYSTEM_PROMPT
from apps.departments.models import Department
from apps.tasks.models import Task
from apps.tasks.services import get_task_metrics, task_queryset_for_user


class AIAssistantService:
    OFF_TOPIC_RESPONSE = "Я могу помочь только с задачами, отделами, рисками и планированием в TTM."
    PROVIDER_ERROR_RESPONSE = "Ошибка: Gemini недоступен. Проверьте API-ключ, выбранную модель или подключение и повторите запрос."
    RELATED_KEYWORDS = (
        "ttm", "ттм", "транстелематика", "задач", "дедлайн", "срок", "статус",
        "риск", "приоритет", "отдел", "команд", "сотрудник", "ответствен",
        "перегруз", "перегруж", "загруз", "нагруз", "план", "календар", "уведом", "отчёт", "отчет",
        "канбан", "дашборд", "выполн", "просроч", "финанс",
        "юрид", "проект", "молодых талант",
    )

    def __init__(self):
        self.mock_mode = settings.AI_MOCK_MODE or not settings.GEMINI_API_KEY

    def answer(self, question, user=None, model_name=None):
        question = (question or "").strip()
        if not question:
            return "Задайте вопрос о задачах, отделах, рисках или загрузке в TTM."
        if not self._is_ttm_related(question):
            return self.OFF_TOPIC_RESPONSE
        if self.mock_mode:
            return self.PROVIDER_ERROR_RESPONSE
        try:
            return self._gemini_answer(question, user, model_name)
        except Exception as e:
            return f"Ошибка Gemini: {str(e)}"

    def weekly_report(self, user=None):
        question = "Сформируй недельный управленческий отчёт по задачам TTM: состояние, риски, перегрузка, рекомендации."
        if self.mock_mode:
            return self.PROVIDER_ERROR_RESPONSE
        try:
            return self._gemini_answer(question, user)
        except Exception as e:
            return f"Ошибка Gemini: {str(e)}"

    def local_overview(self):
        return self.PROVIDER_ERROR_RESPONSE

    def extract_task(self, text, model_name=None):
        text = (text or "").strip()
        if not text:
            return {}

        if self.mock_mode:
            return {"error": self.PROVIDER_ERROR_RESPONSE}

        try:
            import google.generativeai as genai
            import json
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            real_model_name = settings.GEMINI_MODEL
            if model_name:
                name_mapping = {
                    "Gemma 4 31B": "gemma-4-31b-it",
                    "Gemma 4 26B": "gemma-4-26b-a4b-it",
                    "Gemini 3.1 Flash Lite": "gemini-3.1-flash-lite"
                }
                real_model_name = name_mapping.get(model_name) or model_name.lower().replace(" ", "-")

            model = genai.GenerativeModel(real_model_name, generation_config={"temperature": 0.1})
            prompt = (
                "Проанализируй текст задачи и верни СТРОГО один валидный JSON объект (без Markdown). "
                "Поля: 'title' (строка), 'description' (строка), "
                "'responsible' (строка, И.О. или Имя Фамилия в именительном падеже), 'department' (строка, в именительном падеже), "
                "'team' (строка, команда в именительном падеже), 'watchers' (массив строк, имена), "
                "'planning_period' (строка, 'year', 'quarter', 'month', 'week'), 'annual_goal' (строка), "
                "'deadline' (строка, дата в формате YYYY-MM-DD), 'priority' (строка, 'critical', 'high', 'medium', 'low'), "
                "'tags' (строка, через запятую), 'estimated_hours' (целое число), 'parent_task' (строка, название родительской задачи). "
                "Не найденные строковые поля делай пустой строкой, числовые - 0, массивы - пустые.\n\nТекст: " + text
            )
            response = model.generate_content(prompt, request_options={"timeout": 15})
            raw_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(raw_text)
            return {
                "title": data.get("title") or text[:120],
                "description": data.get("description") or text,
                "responsible": data.get("responsible", ""),
                "department": data.get("department", ""),
                "team": data.get("team", ""),
                "watchers": data.get("watchers", []),
                "parent_task": data.get("parent_task", ""),
                "annual_goal": data.get("annual_goal", ""),
                "deadline": data.get("deadline", ""),
                "priority": data.get("priority", Task.Priority.MEDIUM),
                "tags": data.get("tags", ""),
                "estimated_hours": data.get("estimated_hours", 0),
                "planning_period": data.get("planning_period", Task.PlanningPeriod.WEEK)
            }
        except Exception as e:
            return {"error": f"Ошибка: {str(e)}"}

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
        department = self._find_department(question)
        if department:
            return self._department_answer(department, queryset)

        risky = list(queryset.filter(needs_manager_attention=True).select_related("department", "responsible", "responsible__profile")[:4])
        risky_lines = "\n".join(
            f"- {self._format_task_line(task)}"
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

    def _gemini_answer(self, question, user=None, model_name=None):
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        real_model_name = settings.GEMINI_MODEL
        if model_name:
            name_mapping = {
                "Gemma 4 31B": "gemma-4-31b-it",
                "Gemma 4 26B": "gemma-4-26b-a4b-it",
                "Gemini 3.1 Flash Lite": "gemini-3.1-flash-lite"
            }
            real_model_name = name_mapping.get(model_name) or model_name.lower().replace(" ", "-")

        model = genai.GenerativeModel(
            real_model_name,
            system_instruction=SYSTEM_PROMPT,
            generation_config={"temperature": 0.35, "top_p": 0.85, "top_k": 32, "max_output_tokens": 650},
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
        department = self._find_department(question)
        analysis_queryset = queryset
        if department:
            analysis_queryset = analysis_queryset.filter(department=department)
        tasks = analysis_queryset.order_by("deadline", "-priority")[:50]
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
        if not task_lines:
            task_lines.append("- задач по заданному фильтру не найдено")
        return (
            "У тебя есть доступ к базе задач TTM. Не отвечай, что у тебя нет доступа к задачам: используй только данные ниже.\n"
            "Если вопрос не связан с TTM, откажись коротко и не отвечай на внешнюю тему.\n\n"
            f"Вопрос пользователя: {question}\n\n"
            "Общие метрики:\n"
            f"- Всего задач: {metrics['total']}\n"
            f"- Выполнено: {metrics['done']}\n"
            f"- Просрочено: {metrics['overdue']}\n"
            f"- Требуют внимания руководителя: {metrics['attention']}\n"
            f"- Высокий приоритет: {metrics['high_priority']}\n"
            f"- Текущая загрузка сотрудников: {workload}\n"
            f"- Фильтр по отделу: {department.name if department else 'не задан'}\n"
            f"- Задач в выбранном срезе: {analysis_queryset.count()}\n\n"
            "Задачи для анализа:\n"
            + "\n".join(task_lines)
            + "\n\nПравила ответа: ответь только на вопрос пользователя; если это запрос списка любых данных (задачи, сотрудники, отделы и т.д.) — ОБЯЗАТЕЛЬНО выводи их вертикальным списком с новой строки (через дефис), а не сплошным текстом; заверши коротким блоком «Рекомендация:». Отвечай по существу, без длинных вступлений."
        )

    def _department_answer(self, department, queryset):
        tasks = list(
            queryset.filter(department=department)
            .select_related("department", "responsible", "responsible__profile")
            .order_by("deadline", "-priority")
        )
        count = len(tasks)
        if not tasks:
            return (
                f"По отделу «{department.name}» в доступном срезе TTM задач не найдено.\n\n"
                "Рекомендация: проверьте фильтры доступа или назначьте задачи отделу, если они ведутся вне системы."
            )
        visible_tasks = "\n".join(f"- {self._format_task_line(task)}" for task in tasks)
        risky_count = sum(1 for task in tasks if task.needs_manager_attention)
        overdue_count = sum(1 for task in tasks if task.is_overdue)
        return (
            f"В отделе «{department.name}» сейчас {count} {self._plural_tasks(count)}. "
            f"Из них {overdue_count} просрочено, {risky_count} требуют внимания.\n"
            f"{visible_tasks}\n\n"
            "Рекомендация: начните с просроченных и рискованных задач, затем обновите статусы и сроки по задачам без явного прогресса."
        )

    def _find_department(self, question):
        lowered = question.lower()
        for department in Department.objects.all():
            name = department.name.lower()
            if (len(name) <= 3 and self._contains_alias(lowered, name)) or (len(name) > 3 and name in lowered):
                return department
        aliases = {
            "финанс": "Финансы",
            "юрид": "Юридический отдел",
            "молодых талант": "Направление молодых талантов",
            "проект": "Проектный офис",
            "ахо": "АХО",
            "hr": "HR",
            "ит": "ИТ",
        }
        for alias, name in aliases.items():
            if self._contains_alias(lowered, alias):
                return Department.objects.filter(name=name).first()
        return None

    def _is_ttm_related(self, question):
        lowered = question.lower()
        if any(keyword in lowered for keyword in self.RELATED_KEYWORDS):
            return True
        return bool(self._find_department(question))

    def _format_task_line(self, task):
        responsible = getattr(getattr(task.responsible, "profile", None), "full_name", None) or getattr(task.responsible, "username", "не назначен")
        deadline = task.deadline.strftime("%d.%m.%Y") if task.deadline else "без срока"
        return f"{task.title} — {task.get_status_display()}, {responsible}, дедлайн {deadline}, риск {task.get_risk_level_display()}"

    @staticmethod
    def _contains_alias(text, alias):
        if len(alias) <= 3:
            return bool(re.search(rf"(?<![а-яёa-z0-9]){re.escape(alias)}(?![а-яёa-z0-9])", text, flags=re.IGNORECASE))
        return alias in text

    @staticmethod
    def _plural_tasks(count):
        if count % 10 == 1 and count % 100 != 11:
            return "задача"
        if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
            return "задачи"
        return "задач"

    @staticmethod
    def _extract_after(text, pattern):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else ""

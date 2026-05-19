from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.departments.models import Department, Team
from apps.notifications.models import Notification
from apps.reports.models import Report
from apps.tasks.models import Task, TaskComment, TaskHistory
from apps.tasks.services import refresh_all_risks


class Command(BaseCommand):
    help = "Создаёт стартовые данные TTM"

    def handle(self, *args, **options):
        today = timezone.localdate()
        self._create_groups()
        departments = self._create_departments()
        users = self._create_users(departments)
        teams = self._create_teams(departments, users)
        self._attach_profiles(users, departments, teams)
        self._assign_managers(departments, users)
        tasks = self._create_tasks(today, departments, teams, users)
        self._link_hierarchy(tasks)
        self._create_related_data(today, tasks, users, departments)
        refresh_all_risks(Task.objects.filter(tags__icontains="ttm"))
        self.stdout.write(self.style.SUCCESS("Данные TTM созданы или обновлены"))

    def _create_groups(self):
        for name in ["Сотрудник", "Руководитель команды", "Руководитель подразделения", "Администратор"]:
            Group.objects.get_or_create(name=name)

    def _create_departments(self):
        descriptions = {
            "HR": "Подбор, адаптация и развитие сотрудников.",
            "АХО": "Административная поддержка офиса и мероприятий.",
            "ИТ": "Внутренняя инфраструктура и цифровые сервисы.",
            "Финансы": "Бюджеты, отчётность и контроль затрат.",
            "Юридический отдел": "Договоры, согласования и правовая экспертиза.",
            "Направление молодых талантов": "Стажировки, вузы, хакатоны и кадровый резерв.",
            "Проектный офис": "Методология, контроль портфеля и управленческая аналитика.",
        }
        departments = {}
        for name, description in descriptions.items():
            departments[name], _ = Department.objects.update_or_create(name=name, defaults={"description": description})
        return departments

    def _create_users(self, departments):
        rows = [
            ("ivan", "Иван", "Руководитель проектов", "Направление молодых талантов", UserProfile.Role.TEAM_LEAD, UserProfile.Workload.HIGH),
            ("maria", "Мария", "Специалист АХО", "АХО", UserProfile.Role.EMPLOYEE, UserProfile.Workload.HIGH),
            ("alexey", "Алексей", "Координатор площадок", "АХО", UserProfile.Role.EMPLOYEE, UserProfile.Workload.NORMAL),
            ("olga", "Ольга", "HR-менеджер", "HR", UserProfile.Role.TEAM_LEAD, UserProfile.Workload.HIGH),
            ("anna", "Анна", "Специалист по подбору", "HR", UserProfile.Role.EMPLOYEE, UserProfile.Workload.OVERLOADED),
            ("dmitry", "Дмитрий", "Системный администратор", "ИТ", UserProfile.Role.EMPLOYEE, UserProfile.Workload.OVERLOADED),
            ("elena", "Елена", "Финансовый аналитик", "Финансы", UserProfile.Role.EMPLOYEE, UserProfile.Workload.HIGH),
            ("sergey", "Сергей", "Юрист", "Юридический отдел", UserProfile.Role.EMPLOYEE, UserProfile.Workload.NORMAL),
            ("natalia", "Наталья", "Руководитель проектного офиса", "Проектный офис", UserProfile.Role.DEPARTMENT_HEAD, UserProfile.Workload.NORMAL),
        ]
        users = {}
        for username, first_name, position, department_name, role, workload in rows:
            user, _ = User.objects.get_or_create(username=username, defaults={"first_name": first_name, "is_staff": True})
            user.first_name = first_name
            user.set_password("demo1234")
            user.save()
            users[username] = user

        admin, created = User.objects.get_or_create(username="admin", defaults={"first_name": "Администратор", "is_staff": True, "is_superuser": True})
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("admin1234")
        admin.save()
        users["admin"] = admin
        return users

    def _create_teams(self, departments, users):
        rows = [
            ("Команда молодых талантов", "Направление молодых талантов", "ivan"),
            ("Команда офиса", "АХО", "maria"),
            ("Команда HR", "HR", "olga"),
            ("Команда инфраструктуры", "ИТ", "dmitry"),
            ("Команда финансового контроля", "Финансы", "elena"),
            ("Команда правовой поддержки", "Юридический отдел", "sergey"),
            ("Команда проектного контроля", "Проектный офис", "natalia"),
        ]
        teams = {}
        for name, department_name, lead_username in rows:
            teams[department_name], _ = Team.objects.update_or_create(
                name=name,
                department=departments[department_name],
                defaults={"lead": users[lead_username]},
            )
        return teams

    def _attach_profiles(self, users, departments, teams):
        profile_rows = {
            "ivan": ("Иван", "Руководитель проектов", "Направление молодых талантов", UserProfile.Role.TEAM_LEAD, UserProfile.Workload.HIGH),
            "maria": ("Мария", "Специалист АХО", "АХО", UserProfile.Role.EMPLOYEE, UserProfile.Workload.HIGH),
            "alexey": ("Алексей", "Координатор площадок", "АХО", UserProfile.Role.EMPLOYEE, UserProfile.Workload.NORMAL),
            "olga": ("Ольга", "HR-менеджер", "HR", UserProfile.Role.TEAM_LEAD, UserProfile.Workload.HIGH),
            "anna": ("Анна", "Специалист по подбору", "HR", UserProfile.Role.EMPLOYEE, UserProfile.Workload.OVERLOADED),
            "dmitry": ("Дмитрий", "Системный администратор", "ИТ", UserProfile.Role.EMPLOYEE, UserProfile.Workload.OVERLOADED),
            "elena": ("Елена", "Финансовый аналитик", "Финансы", UserProfile.Role.EMPLOYEE, UserProfile.Workload.HIGH),
            "sergey": ("Сергей", "Юрист", "Юридический отдел", UserProfile.Role.EMPLOYEE, UserProfile.Workload.NORMAL),
            "natalia": ("Наталья", "Руководитель проектного офиса", "Проектный офис", UserProfile.Role.DEPARTMENT_HEAD, UserProfile.Workload.NORMAL),
            "admin": ("Администратор", "Администратор системы", "Проектный офис", UserProfile.Role.ADMIN, UserProfile.Workload.NORMAL),
        }
        for username, (full_name, position, department_name, role, workload) in profile_rows.items():
            UserProfile.objects.update_or_create(
                user=users[username],
                defaults={
                    "full_name": full_name,
                    "position": position,
                    "department": departments[department_name],
                    "team": teams.get(department_name),
                    "role": role,
                    "workload_index": workload,
                },
            )

    def _assign_managers(self, departments, users):
        mapping = {
            "Направление молодых талантов": users["ivan"],
            "HR": users["olga"],
            "Проектный офис": users["natalia"],
            "АХО": users["maria"],
            "ИТ": users["dmitry"],
            "Финансы": users["elena"],
            "Юридический отдел": users["sergey"],
        }
        for name, manager in mapping.items():
            Department.objects.filter(name=name).update(manager=manager)

    def _create_tasks(self, today, departments, teams, users):
        rows = [
            ("year", "Развить партнёрство с 5 вузами", "Направление молодых талантов", "ivan", "in_progress", "high", 120, 45),
            ("quarter", "Заключить соглашение с МИРЭА", "Направление молодых талантов", "ivan", "review", "high", 35, 70),
            ("month", "Подготовить участие в хакатоне", "Направление молодых талантов", "ivan", "in_progress", "high", 12, 55),
            ("week", "Согласовать постановку кейса", "Направление молодых талантов", "ivan", "new", "high", 2, 10),
            ("month", "Подготовить рабочие места для стажёров", "АХО", "maria", "planned", "medium", 18, 15),
            ("week", "Проверить переговорные перед мероприятием", "АХО", "alexey", "in_progress", "medium", 4, 45),
            ("quarter", "Обновить программу адаптации новичков", "HR", "olga", "planned", "medium", 45, 20),
            ("month", "Подготовить отчёт по найму молодых специалистов", "HR", "anna", "in_progress", "medium", 8, 40),
            ("week", "Проверить доступы новых сотрудников", "ИТ", "dmitry", "in_progress", "medium", 1, 30),
            ("month", "Подготовить отчёт по затратам подразделения", "Финансы", "elena", "overdue", "high", -3, 65),
            ("year", "Сформировать кадровый резерв для ключевых направлений", "HR", "olga", "in_progress", "high", 150, 35),
            ("quarter", "Провести оценку вовлечённости сотрудников", "HR", "olga", "planned", "medium", 40, 5),
            ("month", "Обновить шаблоны должностных инструкций", "HR", "anna", "review", "medium", 9, 60),
            ("week", "Подготовить список кандидатов на стажировку", "HR", "anna", "in_progress", "high", 3, 35),
            ("week", "Согласовать график интервью с руководителями", "HR", "anna", "new", "medium", 5, 0),
            ("year", "Оптимизировать административные процессы офиса", "АХО", "maria", "in_progress", "medium", 180, 30),
            ("quarter", "Провести инвентаризацию оборудования переговорных", "АХО", "alexey", "planned", "medium", 28, 10),
            ("month", "Закупить расходные материалы для мероприятий", "АХО", "maria", "in_progress", "medium", 11, 50),
            ("week", "Проверить готовность зоны регистрации гостей", "АХО", "alexey", "review", "high", 2, 75),
            ("week", "Организовать доставку брендированных материалов", "АХО", "maria", "overdue", "high", -1, 40),
            ("year", "Повысить устойчивость внутренней ИТ-инфраструктуры", "ИТ", "dmitry", "in_progress", "critical", 210, 25),
            ("quarter", "Обновить регламент управления доступами", "ИТ", "dmitry", "review", "high", 32, 55),
            ("month", "Провести аудит активных учётных записей", "ИТ", "dmitry", "in_progress", "high", 7, 45),
            ("week", "Настроить резервное копирование внутреннего сервера", "ИТ", "dmitry", "new", "high", 3, 0),
            ("week", "Проверить журнал ошибок внутреннего портала", "ИТ", "dmitry", "in_progress", "medium", 1, 20),
            ("year", "Внедрить единый контроль бюджетов подразделений", "Финансы", "elena", "planned", "high", 190, 10),
            ("quarter", "Подготовить финансовую модель пилотного проекта", "Финансы", "elena", "in_progress", "high", 36, 50),
            ("month", "Сверить расходы по мероприятиям молодых талантов", "Финансы", "elena", "overdue", "medium", -2, 80),
            ("week", "Согласовать лимиты на закупку оборудования", "Финансы", "elena", "review", "high", 2, 60),
            ("year", "Систематизировать договорную базу подразделений", "Юридический отдел", "sergey", "in_progress", "high", 160, 40),
            ("quarter", "Подготовить типовой шаблон соглашения с вузом", "Юридический отдел", "sergey", "review", "high", 26, 55),
            ("month", "Проверить договоры с подрядчиками мероприятия", "Юридический отдел", "sergey", "in_progress", "medium", 6, 40),
            ("week", "Согласовать обработку персональных данных участников", "Юридический отдел", "sergey", "new", "high", 4, 0),
            ("quarter", "Собрать статус портфеля проектов", "Проектный офис", "natalia", "in_progress", "high", 20, 65),
            ("week", "Подготовить управленческую сводку для руководства", "Проектный офис", "natalia", "planned", "critical", 2, 15),
            ("month", "Настроить регулярную отчётность по рискам", "Проектный офис", "natalia", "in_progress", "high", 10, 50),
        ]
        tasks = {}
        for period, title, department_name, username, status, priority, days, progress in rows:
            deadline = today + timedelta(days=days)
            last_change = timezone.now() - timedelta(days=8 if status == Task.Status.REVIEW else 2)
            task, _ = Task.objects.update_or_create(
                title=title,
                defaults={
                    "description": f"Задача подразделения «{departments[department_name].name}».",
                    "department": departments[department_name],
                    "team": teams.get(department_name),
                    "responsible": users[username],
                    "author": users["ivan"],
                    "planning_period": period,
                    "deadline": deadline,
                    "priority": priority,
                    "status": status,
                    "progress": progress,
                    "tags": "ttm, рабочий контур",
                    "estimated_hours": 16,
                    "actual_hours": max(0, progress // 5),
                    "last_status_change_at": last_change,
                },
            )
            tasks[title] = task
        return tasks

    def _link_hierarchy(self, tasks):
        links = {
            "Заключить соглашение с МИРЭА": "Развить партнёрство с 5 вузами",
            "Подготовить участие в хакатоне": "Заключить соглашение с МИРЭА",
            "Согласовать постановку кейса": "Подготовить участие в хакатоне",
            "Подготовить управленческую сводку для руководства": "Собрать статус портфеля проектов",
            "Настроить регулярную отчётность по рискам": "Собрать статус портфеля проектов",
        }
        for child_title, parent_title in links.items():
            child = tasks.get(child_title)
            parent = tasks.get(parent_title)
            if child and parent:
                child.parent_task = parent
                child.annual_goal = parent.title if parent.planning_period == Task.PlanningPeriod.YEAR else parent.annual_goal
                child.save(update_fields=["parent_task", "annual_goal", "updated_at"])

    def _create_related_data(self, today, tasks, users, departments):
        comment_titles = list(tasks.keys())[:10]
        for title in comment_titles:
            task = tasks[title]
            TaskComment.objects.get_or_create(
                task=task,
                author=task.responsible or users["ivan"],
                text="Статус обновлён для рабочего сценария.",
            )
            TaskHistory.objects.get_or_create(
                task=task,
                user=users["ivan"],
                field_name="seed",
                old_value="",
                new_value="Стартовые данные",
            )

        for task in list(tasks.values())[:8]:
            Notification.objects.update_or_create(
                recipient=task.responsible,
                title=f"Контроль задачи: {task.title[:80]}",
                defaults={
                    "message": "Проверьте статус, дедлайн и риск задачи.",
                    "type": Notification.Type.RISK if task.needs_manager_attention else Notification.Type.INFO,
                    "task": task,
                    "is_read": False,
                },
            )

        Report.objects.update_or_create(
            title="Недельный отчёт TTM",
            defaults={
                "period_type": Report.Period.WEEK,
                "period_start": today - timedelta(days=today.weekday()),
                "period_end": today - timedelta(days=today.weekday()) + timedelta(days=6),
                "department": departments["Проектный офис"],
                "employee": users["natalia"],
                "content": "Ключевые риски связаны с просрочками, высоким приоритетом и перегрузкой отдельных сотрудников.",
                "created_by": users["natalia"],
            },
        )

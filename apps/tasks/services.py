from collections import Counter
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.tasks.models import Task


def calculate_task_risk(task):
    today = timezone.localdate()
    score = 0
    reasons = []
    recommendations = []
    is_open = not task.is_closed

    if task.deadline and task.deadline < today and is_open:
        score += 50
        reasons.append("дедлайн уже прошёл")
        recommendations.append("обновить статус или назначить новый срок")
    elif task.deadline and (task.deadline - today).days < 3 and is_open:
        score += 25
        reasons.append("до дедлайна меньше 3 дней")
        recommendations.append("проверить готовность результата")

    if task.priority == Task.Priority.HIGH:
        score += 15
        reasons.append("высокий приоритет")
    elif task.priority == Task.Priority.CRITICAL:
        score += 25
        reasons.append("критический приоритет")

    if task.last_status_change_at and timezone.now() - task.last_status_change_at > timedelta(days=7) and is_open:
        score += 15
        reasons.append("статус не менялся больше 7 дней")
        recommendations.append("запросить актуальный статус у ответственного")

    profile = getattr(task.responsible, "profile", None) if task.responsible else None
    if profile and profile.workload_index == UserProfile.Workload.OVERLOADED:
        score += 20
        reasons.append("ответственный перегружен")
        recommendations.append("перераспределить часть задач")

    if task.status == Task.Status.REVIEW and task.last_status_change_at:
        if timezone.now() - task.last_status_change_at > timedelta(days=5):
            score += 20
            reasons.append("задача долго находится на согласовании")
            recommendations.append("ускорить согласование")

    if task.deadline and (task.deadline - today).days < 5 and task.progress < 30 and is_open:
        score += 20
        reasons.append("прогресс ниже 30% перед дедлайном")
        recommendations.append("разбить задачу на ближайшие действия")

    comments_count = task.comments.count() if task.pk else 0
    if task.progress == 0 and comments_count == 0 and is_open:
        score += 10
        reasons.append("нет комментариев и прогресса")
        recommendations.append("добавить рабочий комментарий")

    if task.planning_period in {Task.PlanningPeriod.YEAR, Task.PlanningPeriod.QUARTER} or task.annual_goal:
        score += 10
        reasons.append("задача связана со стратегическим периодом")

    if not task.responsible:
        score += 30
        reasons.append("не назначен ответственный")
        recommendations.append("назначить ответственного")

    if not task.deadline:
        score += 15
        reasons.append("не указан дедлайн")
        recommendations.append("указать срок выполнения")

    if score >= 80:
        level = Task.Risk.CRITICAL
    elif score >= 50:
        level = Task.Risk.HIGH
    elif score >= 25:
        level = Task.Risk.MEDIUM
    else:
        level = Task.Risk.LOW

    if not reasons:
        reasons.append("существенных факторов риска не выявлено")
    if not recommendations:
        recommendations.append("продолжать работу по плану")

    return {
        "score": score,
        "level": level,
        "reason": f"{Task.Risk(level).label} риск: " + ", ".join(reasons) + ".",
        "recommendation": "Рекомендуется " + "; ".join(dict.fromkeys(recommendations)) + ".",
        "needs_attention": level in {Task.Risk.HIGH, Task.Risk.CRITICAL},
    }


def refresh_task_risk(task, commit=True):
    risk = calculate_task_risk(task)
    task.risk_level = risk["level"]
    task.risk_reason = risk["reason"]
    task.risk_recommendation = risk["recommendation"]
    task.needs_manager_attention = risk["needs_attention"]
    if commit and task.pk:
        task.save(
            update_fields=[
                "risk_level",
                "risk_reason",
                "risk_recommendation",
                "needs_manager_attention",
                "updated_at",
            ]
        )
    return risk


def refresh_all_risks(queryset=None):
    queryset = queryset or Task.objects.all()
    for task in queryset.select_related("responsible", "responsible__profile"):
        refresh_task_risk(task)


def task_queryset_for_user(user):
    queryset = Task.objects.select_related("department", "team", "responsible", "author", "parent_task")
    if not user.is_authenticated:
        return queryset.none()
    profile = getattr(user, "profile", None)
    if user.is_superuser or not profile:
        return queryset
    if profile.role in {UserProfile.Role.ADMIN, UserProfile.Role.DEPARTMENT_HEAD}:
        return queryset
    if profile.role == UserProfile.Role.TEAM_LEAD and profile.team_id:
        return queryset.filter(Q(team=profile.team) | Q(responsible=user) | Q(author=user)).distinct()
    return queryset.filter(Q(responsible=user) | Q(author=user) | Q(watchers=user)).distinct()


def filter_tasks(queryset, params):
    q = params.get("q", "").strip()
    if q:
        queryset = queryset.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(tags__icontains=q))

    for field in ("status", "priority", "risk_level", "planning_period"):
        value = params.get(field)
        if value:
            queryset = queryset.filter(**{field: value})

    department = params.get("department")
    if department:
        if str(department).isdigit():
            queryset = queryset.filter(department_id=department)
        else:
            queryset = queryset.filter(department__name__iexact=department)

    responsible = params.get("responsible")
    if responsible and str(responsible).isdigit():
        queryset = queryset.filter(responsible_id=responsible)

    sort = params.get("sort", "deadline")
    allowed = {"deadline", "-deadline", "priority", "-priority", "risk_level", "-risk_level", "updated_at", "-updated_at"}
    if sort in allowed:
        queryset = queryset.order_by(sort)
    return queryset


def get_task_metrics(queryset=None):
    queryset = queryset or Task.objects.select_related("department", "responsible")
    total = queryset.count()
    done = queryset.filter(status=Task.Status.DONE).count()
    overdue = queryset.filter(Q(status=Task.Status.OVERDUE) | Q(deadline__lt=timezone.localdate())).exclude(status=Task.Status.DONE).count()
    attention = queryset.filter(needs_manager_attention=True).count()
    high_priority = queryset.filter(priority__in=[Task.Priority.HIGH, Task.Priority.CRITICAL]).count()
    completion = round(done / total * 100) if total else 0

    by_status = list(queryset.values("status").annotate(count=Count("id")).order_by("status"))
    by_department = list(queryset.values("department__name").annotate(count=Count("id")).order_by("-count"))
    by_period = list(queryset.values("planning_period").annotate(count=Count("id")).order_by("planning_period"))
    risky_tasks = queryset.filter(needs_manager_attention=True).order_by("-risk_level", "deadline")[:8]
    deadlines = queryset.filter(deadline__isnull=False).exclude(status=Task.Status.DONE).order_by("deadline")[:8]

    workload_counter = Counter()
    for row in queryset.exclude(responsible__isnull=True).values("responsible__profile__full_name").annotate(count=Count("id")):
        workload_counter[row["responsible__profile__full_name"] or "Без профиля"] = row["count"]

    return {
        "total": total,
        "done": done,
        "overdue": overdue,
        "attention": attention,
        "high_priority": high_priority,
        "completion": completion,
        "by_status": by_status,
        "by_department": by_department,
        "by_period": by_period,
        "risky_tasks": risky_tasks,
        "deadlines": deadlines,
        "workload": workload_counter.most_common(8),
    }

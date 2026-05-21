import json
from collections import defaultdict
from django.db.models import Avg, Count, Q, Case, When, Value, IntegerField
from django.utils import timezone
from apps.tasks.models import Task
from apps.tasks.services import get_task_metrics, refresh_all_risks
from apps.accounts.models import UserProfile

def build_dashboard_context(queryset=None):
    if queryset is None:
        queryset = Task.objects.select_related("department", "responsible", "responsible__profile")
    
    refresh_all_risks(queryset)
    
    metrics = get_task_metrics(queryset)
    
    # 1. Core KPIs
    in_progress_count = queryset.filter(status__in=[Task.Status.IN_PROGRESS, Task.Status.REVIEW]).count()
    open_tasks = queryset.exclude(status=Task.Status.DONE)
    avg_progress = open_tasks.aggregate(Avg('progress'))['progress__avg'] or 0
    avg_progress = round(avg_progress)

    # 2. Department efficiency matrix
    dept_status_counts = queryset.values('department__name', 'status').annotate(count=Count('id'))
    dept_names = sorted(list(set(row['department__name'] or 'Без отдела' for row in dept_status_counts)))
    
    status_colors = {
        Task.Status.NEW: '#94A3B8',
        Task.Status.IN_PROGRESS: '#3B82F6',
        Task.Status.REVIEW: '#A78BFA',
        Task.Status.DONE: '#34D399',
        Task.Status.OVERDUE: '#F97316',
    }
    
    datasets = []
    for status, color in status_colors.items():
        data = []
        for dept in dept_names:
            count = next((row['count'] for row in dept_status_counts if (row['department__name'] or 'Без отдела') == dept and row['status'] == status), 0)
            data.append(count)
        datasets.append({
            'label': Task.Status(status).label,
            'backgroundColor': color,
            'data': data
        })
    
    dept_efficiency_json = json.dumps({'labels': dept_names, 'datasets': datasets}, ensure_ascii=False)

    # 3. Employee performance table
    employee_stats = defaultdict(lambda: {'total': 0, 'done': 0, 'overdue': 0, 'progress_sum': 0, 'open_count': 0, 'dept': '', 'workload_raw': 0})
    for task in queryset.select_related('responsible', 'responsible__profile', 'department'):
        if not task.responsible:
            continue
        emp_name = getattr(task.responsible.profile, 'full_name', task.responsible.username) if hasattr(task.responsible, 'profile') else task.responsible.username
        emp_dept = task.department.name if task.department else 'Без отдела'
        
        stat = employee_stats[emp_name]
        stat['dept'] = emp_dept
        stat['total'] += 1
        stat['workload_raw'] = getattr(task.responsible.profile, 'active_tasks_count', 0) if hasattr(task.responsible, 'profile') else 0
        
        if task.status == Task.Status.DONE:
            stat['done'] += 1
        else:
            stat['open_count'] += 1
            stat['progress_sum'] += task.progress
            
        if task.is_overdue:
            stat['overdue'] += 1

    employee_data = []
    for name, stat in employee_stats.items():
        avg_prog = round(stat['progress_sum'] / stat['open_count']) if stat['open_count'] > 0 else 100 if stat['done'] > 0 else 0
        workload = 'workload-normal'
        if stat['workload_raw'] >= 10:
            workload = 'workload-overloaded'
        elif stat['workload_raw'] >= 5:
            workload = 'workload-high'
            
        employee_data.append({
            'name': name,
            'department': stat['dept'],
            'total': stat['total'],
            'done': stat['done'],
            'overdue': stat['overdue'],
            'avg_progress': avg_prog,
            'workload': workload,
            'workload_raw': stat['workload_raw']
        })
    employee_data.sort(key=lambda x: (-x['overdue'], -x['total']))

    # 4. Priority distribution
    priority_counts = queryset.values('priority').annotate(count=Count('id'))
    priority_map = {
        Task.Priority.LOW: {'color': '#94A3B8'},
        Task.Priority.MEDIUM: {'color': '#60A5FA'},
        Task.Priority.HIGH: {'color': '#FBBF24'},
        Task.Priority.CRITICAL: {'color': '#EF4444'},
    }
    
    priority_labels = []
    priority_values = []
    priority_codes = []
    priority_colors = []
    for p_code, p_info in priority_map.items():
        count = next((row['count'] for row in priority_counts if row['priority'] == p_code), 0)
        if count > 0:
            priority_labels.append(Task.Priority(p_code).label)
            priority_values.append(count)
            priority_codes.append(p_code)
            priority_colors.append(p_info['color'])

    # 5. Risk distribution
    risk_counts = queryset.values('risk_level').annotate(count=Count('id'))
    risk_map = {
        Task.Risk.LOW: {'color': '#34D399'},
        Task.Risk.MEDIUM: {'color': '#FBBF24'},
        Task.Risk.HIGH: {'color': '#F97316'},
        Task.Risk.CRITICAL: {'color': '#EF4444'},
    }
    
    risk_labels = []
    risk_values = []
    risk_codes = []
    risk_colors = []
    for r_code, r_info in risk_map.items():
        count = next((row['count'] for row in risk_counts if row['risk_level'] == r_code), 0)
        if count > 0:
            risk_labels.append(Task.Risk(r_code).label)
            risk_values.append(count)
            risk_codes.append(r_code)
            risk_colors.append(r_info['color'])

    # 6. Dept average progress
    dept_progress = open_tasks.values('department__name').annotate(avg=Avg('progress'))
    dept_progress_labels = [row['department__name'] or 'Без отдела' for row in dept_progress]
    dept_progress_values = [round(row['avg'] or 0) for row in dept_progress]

    # 7. Overdue by department
    overdue_dept = queryset.filter(
        Q(status=Task.Status.OVERDUE) | Q(deadline__lt=timezone.localdate())
    ).exclude(status=Task.Status.DONE).values('department__name').annotate(count=Count('id'))
    overdue_dept_labels = [row['department__name'] or 'Без отдела' for row in overdue_dept]
    overdue_dept_values = [row['count'] for row in overdue_dept]

    # 8. Top risky tasks
    risky_tasks = queryset.filter(needs_manager_attention=True).annotate(
        risk_weight=Case(
            When(risk_level=Task.Risk.CRITICAL, then=Value(4)),
            When(risk_level=Task.Risk.HIGH, then=Value(3)),
            When(risk_level=Task.Risk.MEDIUM, then=Value(2)),
            When(risk_level=Task.Risk.LOW, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('-risk_weight', 'deadline')[:50]
    
    for task in risky_tasks:
        if task.risk_reason:
            words = task.risk_reason.split()
            task.short_risk_reason = ' '.join(words[:12]) + ('...' if len(words) > 12 else '')
        else:
            task.short_risk_reason = ''

    # 9. Unassigned tasks
    unassigned_tasks = open_tasks.filter(responsible__isnull=True)[:10]

    return {
        "metrics": metrics,
        "in_progress": in_progress_count,
        "avg_progress": avg_progress,
        "dept_efficiency_json": dept_efficiency_json,
        "employee_data": employee_data,
        "priority_labels": json.dumps(priority_labels, ensure_ascii=False),
        "priority_values": json.dumps(priority_values, ensure_ascii=False),
        "priority_colors": json.dumps(priority_colors, ensure_ascii=False),
        "priority_codes": json.dumps(priority_codes, ensure_ascii=False),
        "risk_labels": json.dumps(risk_labels, ensure_ascii=False),
        "risk_values": json.dumps(risk_values, ensure_ascii=False),
        "risk_colors": json.dumps(risk_colors, ensure_ascii=False),
        "risk_codes": json.dumps(risk_codes, ensure_ascii=False),
        "period_labels": json.dumps([Task.PlanningPeriod(row["planning_period"]).label for row in metrics["by_period"]], ensure_ascii=False),
        "period_values": json.dumps([row["count"] for row in metrics["by_period"]], ensure_ascii=False),
        "dept_progress_labels": json.dumps(dept_progress_labels, ensure_ascii=False),
        "dept_progress_values": json.dumps(dept_progress_values, ensure_ascii=False),
        "overdue_dept_labels": json.dumps(overdue_dept_labels, ensure_ascii=False),
        "overdue_dept_values": json.dumps(overdue_dept_values, ensure_ascii=False),
        "risky_tasks": risky_tasks,
        "unassigned_tasks": unassigned_tasks,
        # Legacy for home.html
        "status_labels": [Task.Status(row["status"]).label for row in metrics["by_status"]],
        "status_values": [row["count"] for row in metrics["by_status"]],
        "department_labels": [row["department__name"] or "Без отдела" for row in metrics["by_department"]],
        "department_values": [row["count"] for row in metrics["by_department"]],
        "workload_labels": [item[0] for item in metrics["workload"]],
        "workload_values": [item[1] for item in metrics["workload"]],
    }

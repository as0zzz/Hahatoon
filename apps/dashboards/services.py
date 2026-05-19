from apps.tasks.models import Task
from apps.tasks.services import get_task_metrics, refresh_all_risks


def build_dashboard_context(queryset=None):
    queryset = queryset or Task.objects.select_related("department", "responsible", "responsible__profile")
    refresh_all_risks(queryset)
    metrics = get_task_metrics(queryset)
    return {
        "metrics": metrics,
        "status_labels": [Task.Status(row["status"]).label for row in metrics["by_status"]],
        "status_values": [row["count"] for row in metrics["by_status"]],
        "department_labels": [row["department__name"] or "Без отдела" for row in metrics["by_department"]],
        "department_values": [row["count"] for row in metrics["by_department"]],
        "period_labels": [Task.PlanningPeriod(row["planning_period"]).label for row in metrics["by_period"]],
        "period_values": [row["count"] for row in metrics["by_period"]],
        "workload_labels": [item[0] for item in metrics["workload"]],
        "workload_values": [item[1] for item in metrics["workload"]],
    }

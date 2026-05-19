from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.audit.models import AuditLog


@login_required
def audit_log(request):
    logs = AuditLog.objects.select_related("user")[:100]
    return render(request, "audit/index.html", {"logs": logs, "title": "Аудит"})

# Create your views here.

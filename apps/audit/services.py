from apps.audit.models import AuditLog


def log_action(user, action, object_type, object_id="", payload=None, request=None):
    ip_address = None
    if request:
        ip_address = request.META.get("REMOTE_ADDR")
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        object_type=object_type,
        object_id=str(object_id or ""),
        payload=payload or {},
        ip_address=ip_address,
    )

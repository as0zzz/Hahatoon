from django import template

from apps.tasks.models import Task

register = template.Library()


@register.filter
def status_class(value):
    return {
        Task.Status.NEW: "badge-gray",
        Task.Status.IN_PROGRESS: "badge-blue",
        Task.Status.REVIEW: "badge-purple",
        Task.Status.DONE: "badge-green",
        Task.Status.OVERDUE: "badge-red",
    }.get(value, "badge-gray")


@register.filter
def priority_class(value):
    return {
        Task.Priority.LOW: "badge-gray",
        Task.Priority.MEDIUM: "badge-blue",
        Task.Priority.HIGH: "badge-amber",
        Task.Priority.CRITICAL: "badge-red",
    }.get(value, "badge-gray")


@register.filter
def risk_class(value):
    return {
        Task.Risk.LOW: "badge-green",
        Task.Risk.MEDIUM: "badge-amber",
        Task.Risk.HIGH: "badge-red",
        Task.Risk.CRITICAL: "badge-darkred",
    }.get(value, "badge-gray")


@register.filter
def dict_get(mapping, key):
    return mapping.get(key)

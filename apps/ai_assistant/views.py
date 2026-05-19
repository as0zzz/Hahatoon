from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.ai_assistant.services import AIAssistantService
from apps.audit.services import log_action
from apps.tasks.models import Task


@login_required
def index(request):
    service = AIAssistantService()
    answer = None
    question = request.GET.get("question", "")
    if question:
        answer = service.answer(question, request.user)
        log_action(request.user, "ai_ask", "AI", payload={"question": question[:120]}, request=request)
    return render(
        request,
        "ai/index.html",
        {
            "title": "AI-помощник",
            "answer": answer,
            "question": question,
            "insights": [
                service.local_overview(),
                service.risky_tasks_summary(),
            ],
        },
    )


@login_required
@require_POST
def ask(request):
    question = request.POST.get("question", "")
    answer = AIAssistantService().answer(question, request.user)
    log_action(request.user, "ai_ask", "AI", payload={"question": question[:120]}, request=request)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"answer": answer})
    messages.success(request, "AI-помощник подготовил ответ")
    return render(request, "ai/index.html", {"answer": answer, "question": question})


@login_required
def report(request):
    content = AIAssistantService().weekly_report(request.user)
    return render(request, "ai/report.html", {"content": content, "title": "AI-отчёт"})


@login_required
@require_POST
def extract_task(request):
    extracted = AIAssistantService().extract_task(request.POST.get("text", ""))
    return JsonResponse(extracted)

# Create your views here.

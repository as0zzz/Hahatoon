from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.ai_assistant.services import AIAssistantService
from apps.audit.services import log_action
from apps.tasks.models import Task
from apps.ai_assistant.models import AIChat, AIChatMessage
from django.shortcuts import get_object_or_404
from django.db.models import Q
from openpyxl import Workbook
from django.http import HttpResponse

@login_required
def index(request):
    service = AIAssistantService()
    answer = None
    question = request.GET.get("question", "")
    if question:
        answer = service.answer(question, request.user)
        log_action(request.user, "ai_ask", "AI", payload={"question": question[:120]}, request=request)
    chats = AIChat.objects.filter(user=request.user).order_by('-updated_at')
    if not chats.exists():
        chat = AIChat.objects.create(user=request.user, title="Текущий чат")
        chats = [chat]

    # Preload messages for the most recently active or only chat
    active_chat = chats[0]
    chat_messages = active_chat.messages.all()

    return render(
        request,
        "ai/index.html",
        {
            "title": "AI-помощник",
            "answer": answer,
            "question": question,
            "chats": chats,
            "active_chat": active_chat,
            "chat_messages": chat_messages,
        },
    )


@login_required
@require_POST
def ask(request):
    question = request.POST.get("question", "")
    model_name = request.POST.get("model", "")
    chat_id = request.POST.get("chat_id", "")
    
    if chat_id:
        chat = get_object_or_404(AIChat, user=request.user, id=chat_id)
        chat.save()  # Bump updated_at
    else:
        chat = AIChat.objects.create(user=request.user, title=question[:50] or "Новый чат")
        
    if question:
        AIChatMessage.objects.create(chat=chat, role="user", content=question)
        
    answer = AIAssistantService().answer(question, request.user, model_name=model_name)
    log_action(request.user, "ai_ask", "AI", payload={"question": question[:120]}, request=request)
    
    if answer:
        AIChatMessage.objects.create(chat=chat, role="ai", content=answer)
        
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"answer": answer, "chat_id": chat.id})
    messages.success(request, "AI-помощник подготовил ответ")
    return render(request, "ai/index.html", {"answer": answer, "question": question})

@login_required
@require_POST
def create_chat(request):
    chat = AIChat.objects.create(user=request.user, title="Новый чат")
    return JsonResponse({"id": chat.id, "title": chat.title})

@login_required
@require_POST
def rename_chat(request, chat_id):
    title = request.POST.get("title", "").strip()
    if title:
        AIChat.objects.filter(user=request.user, id=chat_id).update(title=title)
    return JsonResponse({"status": "ok"})

@login_required
@require_POST
def delete_chat(request, chat_id):
    AIChat.objects.filter(user=request.user, id=chat_id).delete()
    return JsonResponse({"status": "ok"})

@login_required
def get_chat_messages(request, chat_id):
    chat = get_object_or_404(AIChat, user=request.user, id=chat_id)
    messages = chat.messages.all()
    return JsonResponse({
        "messages": [
            {"role": m.role, "content": m.content} for m in messages
        ]
    })


@login_required
def report(request):
    content = AIAssistantService().weekly_report(request.user)
    return render(request, "ai/report.html", {"content": content, "title": "AI-отчёт"})


@login_required
@require_POST
def extract_task(request):
    text = request.POST.get("text", "")
    model_name = request.POST.get("model", "")
    extracted = AIAssistantService().extract_task(text, model_name=model_name)
    return JsonResponse(extracted)

@login_required
def export_excel(request):
    question = request.GET.get("q", "").lower()
    service = AIAssistantService()
    queryset = service._visible_tasks(request.user)
    
    if question:
        # Basic filtering based on question content
        department = service._find_department(question)
        if department:
            queryset = queryset.filter(department=department)
        elif "просроч" in question:
            from django.utils import timezone
            queryset = queryset.filter(deadline__lt=timezone.now().date(), status__in=["new", "planned", "in_progress", "review"])
        elif "риск" in question or "вниман" in question:
            queryset = queryset.filter(needs_manager_attention=True)
            
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "AI Отчёт TTM"
    sheet.append(["ID", "Задача", "Отдел", "Ответственный", "Дедлайн", "Статус", "Приоритет", "Риск"])
    
    for task in queryset:
        responsible = getattr(getattr(task.responsible, "profile", None), "full_name", None) or getattr(task.responsible, "username", "Не назначен")
        sheet.append([
            task.id,
            task.title,
            task.department.name if task.department else "Без отдела",
            responsible,
            task.deadline.strftime("%d.%m.%Y") if task.deadline else "Без срока",
            task.get_status_display(),
            task.get_priority_display(),
            task.get_risk_level_display()
        ])
        
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="ai_report.xlsx"'
    workbook.save(response)
    return response

# Create your views here.

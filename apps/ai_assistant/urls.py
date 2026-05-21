from django.urls import path

from apps.ai_assistant import views

app_name = "ai"

urlpatterns = [
    path("", views.index, name="index"),
    path("ask/", views.ask, name="ask"),
    path("report/", views.report, name="report"),
    path("extract-task/", views.extract_task, name="extract_task"),
    path("export_excel/", views.export_excel, name="export_excel"),
    path("chat/create/", views.create_chat, name="create_chat"),
    path("chat/<int:chat_id>/rename/", views.rename_chat, name="rename_chat"),
    path("chat/<int:chat_id>/delete/", views.delete_chat, name="delete_chat"),
    path("chat/<int:chat_id>/messages/", views.get_chat_messages, name="chat_messages"),
]

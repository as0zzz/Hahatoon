from django.db import models
from django.conf import settings

class AIChat(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_chats")
    title = models.CharField(max_length=255, default="Новый чат")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

class AIChatMessage(models.Model):
    chat = models.ForeignKey(AIChat, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20) # 'user' or 'ai'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

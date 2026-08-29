from django.urls import path

from apps.ai.views import AIChatView


urlpatterns = [
    path(
        "chat/",
        AIChatView.as_view(),
        name="ai-chat",
    ),
]
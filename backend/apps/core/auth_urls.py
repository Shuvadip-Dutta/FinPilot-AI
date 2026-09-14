from django.urls import path
from apps.core.views import (
    RegisterView,
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("token/", ThrottledTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", ThrottledTokenRefreshView.as_view(), name="token-refresh"),
]

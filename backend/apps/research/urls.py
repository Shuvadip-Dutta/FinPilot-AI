from django.urls import path

from apps.research.views import CompanyResearchView


urlpatterns = [
    path(
        "company/",
        CompanyResearchView.as_view(),
        name="company-research",
    ),
]
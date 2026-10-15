# dashboard/urls.py

from django.urls import path

from dashboard.views.dashboard import DashboardIndexView
from dashboard.views.poems import (
    PoemListView,
    PoemDetailView,
    PoemEditView,
    PoemApproveView,
    PoemRejectView,
    PoemDeleteView,
    PoemRestoreView,
)
from dashboard.views.audio import (
    AudioReplaceView,
    AudioDeleteView,
)
from dashboard.views.registration import (
    RequestAccessView,
    RequestSuccessView,
    HiddenRegisterView,
    RegisterSuccessView,
)

from dashboard.views.tools import VoiceToTextView

app_name = "dashboard"

urlpatterns = [
    path("", DashboardIndexView.as_view(), name="index"),
    path('tools/voice-to-text/', VoiceToTextView.as_view(), name='voice_to_text'),
    # Poem management
    path("poems/", PoemListView.as_view(), name="poem_list"),
    path("poems/<int:pk>/", PoemDetailView.as_view(), name="poem_detail"),
    path("poems/<int:pk>/edit/", PoemEditView.as_view(), name="poem_edit"),
    path("poems/<int:pk>/approve/", PoemApproveView.as_view(), name="poem_approve"),
    path("poems/<int:pk>/reject/", PoemRejectView.as_view(), name="poem_reject"),
    path("poems/<int:pk>/delete/", PoemDeleteView.as_view(), name="poem_delete"),
    path("poems/<int:pk>/restore/", PoemRestoreView.as_view(), name="poem_restore"),

    # Audio management
    path("poems/<int:pk>/audio/replace/", AudioReplaceView.as_view(), name="audio_replace"),
    path("poems/<int:pk>/audio/delete/", AudioDeleteView.as_view(), name="audio_delete"),

    # Hidden access request / registration
    path("hidden/request/", RequestAccessView.as_view(), name="request_access"),
    path("hidden/request/success/", RequestSuccessView.as_view(), name="request_success"),
    path("hidden/register/<str:token>/", HiddenRegisterView.as_view(), name="hidden_register"),
    path("hidden/register/success/", RegisterSuccessView.as_view(), name="register_success"),
]
# END
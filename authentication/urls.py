from django.urls import path
from .views import VideoVerificationView, OTPVerificationView

app_name = 'authentication'

urlpatterns = [
    path('video-verify/', VideoVerificationView.as_view(), name='video_verify'),
    path('otp/', OTPVerificationView.as_view(), name='otp'),
]
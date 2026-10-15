from django.urls import path

from api.views import (
    APITokenDataView,
    ProfileAPIView,
)

from .views import (
    LoginView,
    LogoutView,
    ProfileView,
    SignUpView,
    DashboardRequestView,
    ForgotPasswordView,
    PasswordResetSentView,
    ResetPasswordView,
    PasswordResetCompleteView,
    LoginVerificationView,
)


urlpatterns = [
    path('0.1/login/', APITokenDataView.as_view(), name='api-token'),
    path('0.1/profile/', ProfileAPIView.as_view(), name='api-profile'),

    path('profile/', ProfileView.as_view(), name='profile'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('dashboard-request/', DashboardRequestView.as_view(), name='dashboard_request'),

    # Custom password reset
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('password-reset-sent/', PasswordResetSentView.as_view(), name='password_reset_sent'),
    path('reset/<str:token>/', ResetPasswordView.as_view(), name='password_reset_confirm'),
    path('reset/done/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Dashboard login verification
    path('login-verify/', LoginVerificationView.as_view(), name='login_verify'),
]
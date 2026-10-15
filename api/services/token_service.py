from django.contrib.auth import get_user_model

from authentication.services.dashboard_access import (
    has_valid_dashboard_access
)

from api.tokens import (
    DashboardAcessToken,
    StaffAcessToken,
    UserAcessToken
)

User = get_user_model()

def get_authenticated_user(session_user):
    return User.objects.get(pk=session_user.pk)

def create_api_token(session_user):
    user = get_authenticated_user(session_user)
    print(1)
    if user is None:
        print(2)
        return None, None 
    if not user.is_authenticated:
        print(3)
        return None, None
    if user.is_staff:
        print(4)
        
        token = StaffAcessToken.for_user(user)
        return token, "staff"
    if has_valid_dashboard_access(user):
        print(5)

        token = DashboardAcessToken.for_user(user)
        return token, "dashboard"
    token = UserAcessToken.for_user(user)
    print(6)
    return token, "user"
    


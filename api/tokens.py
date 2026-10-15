from datetime import timedelta

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

class UserAcessToken(AccessToken):
    lifetime=timedelta(hours=1)

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        
        token["role"] = "user"
        return token


class DashboardAcessToken(AccessToken):
    lifetime=timedelta(hours=10)

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        
        token["role"] = "dashboard"
        return token

class StaffAcessToken(AccessToken):
    lifetime=timedelta(minutes=25)

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token["role"] = "staff"
        return token        
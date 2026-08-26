from django.contrib.auth.backends import ModelBackend

from .models import Profile
from .services import release_expired_block


class AccountStatusBackend(ModelBackend):
    def user_can_authenticate(self, user):
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return super().user_can_authenticate(user)

        if profile.is_deleted:
            return False
        if release_expired_block(user):
            user.refresh_from_db(fields=["is_active"])
            profile.refresh_from_db()
        if profile.is_blocked:
            return False
        return super().user_can_authenticate(user)

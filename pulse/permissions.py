from rest_framework.permissions import BasePermission

from .models import UserProfile


class IsAdminUser(BasePermission):
    message = 'Admin access required.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and hasattr(user, 'profile')
            and user.profile.role == UserProfile.Role.ADMIN
        )
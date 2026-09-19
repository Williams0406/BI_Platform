from rest_framework.permissions import BasePermission

from .models import Membership


WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


def user_role_for_organization(user, organization_id):
    if not user or not user.is_authenticated:
        return None

    return (
        Membership.objects.filter(
            user=user,
            organization_id=organization_id,
            is_active=True,
        )
        .values_list("role", flat=True)
        .first()
    )


class IsOrganizationMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        organization_id = getattr(obj, "organization_id", None) or getattr(obj, "id", None)
        return user_role_for_organization(request.user, organization_id) is not None

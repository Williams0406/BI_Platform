from workspaces.models import Membership


WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


def can_read_view(user, view):
    return Membership.objects.filter(
        organization=view.workspace.organization,
        user=user,
        is_active=True,
    ).exists()


def can_write_view(user, view):
    return Membership.objects.filter(
        organization=view.workspace.organization,
        user=user,
        is_active=True,
        role__in=WRITE_ROLES,
    ).exists()

from rest_framework.permissions import BasePermission


class IsOrganizationMember(BasePermission):
    """Require authenticated user with membership in the requested organization."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        org_id = view.kwargs.get("organization_pk") or request.headers.get("X-Organization-ID")
        if not org_id:
            return request.user.memberships.exists()
        return request.user.memberships.filter(organization_id=org_id).exists()


def get_user_organization(request):
    """Resolve active organization from header or user's first membership."""
    org_id = request.headers.get("X-Organization-ID")
    if org_id and request.user.is_authenticated:
        membership = request.user.memberships.filter(organization_id=org_id).first()
        if membership:
            return membership.organization
    if request.user.is_authenticated:
        membership = request.user.memberships.select_related("organization").first()
        return membership.organization if membership else None
    return None

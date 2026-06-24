from django.db import models
from django.contrib.auth.models import User


class Organization(models.Model):
    """EU client company using the platform."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    origin_country = models.CharField(max_length=2, help_text="ISO code, e.g. DE")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "organization"], name="unique_user_org"),
        ]
        ordering = ["organization__name"]

    def __str__(self):
        return f"{self.user.username} @ {self.organization.slug}"

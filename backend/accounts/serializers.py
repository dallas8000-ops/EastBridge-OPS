from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Organization, OrganizationMembership


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "origin_country", "created_at")


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ("id", "organization", "role", "joined_at")


class UserSerializer(serializers.ModelSerializer):
    memberships = OrganizationMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "memberships")


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    organization_name = serializers.CharField(max_length=255)
    origin_country = serializers.CharField(max_length=2)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def create(self, validated_data):
        from django.utils.text import slugify

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        base_slug = slugify(validated_data["organization_name"])[:50]
        slug = base_slug
        counter = 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization.objects.create(
            name=validated_data["organization_name"],
            slug=slug,
            origin_country=validated_data["origin_country"].upper(),
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=org,
            role=OrganizationMembership.Role.ADMIN,
        )
        return user

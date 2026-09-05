from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "password_confirm")
        read_only_fields = ("id",)

    def validate_email(self, value: str) -> str:
        cleaned_email = value.strip().lower()
        if not cleaned_email:
            raise serializers.ValidationError("Email address is required.")
        if User.objects.filter(email__iexact=cleaned_email).exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return cleaned_email

    def validate_username(self, value: str) -> str:
        cleaned_username = value.strip()
        if not cleaned_username:
            raise serializers.ValidationError("Username is required.")
        if User.objects.filter(username__iexact=cleaned_username).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return cleaned_username

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Password fields do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "date_joined")
        read_only_fields = ("id", "username", "email", "date_joined")

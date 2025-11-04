from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "full_name", "email")
        read_only_fields = ("id",)


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(write_only=True)
    surname = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "phone", "name", "surname", "password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        name = validated_data.pop("name")
        surname = validated_data.pop("surname")
        validated_data["full_name"] = f"{name} {surname}"
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        phone = attrs.get("phone") or attrs.get("username")
        password = attrs.get("password")
        if phone is None or password is None:
            raise serializers.ValidationError("Phone and password are required")

        user = authenticate(request=self.context.get("request"), phone=phone, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid phone or password")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")

        refresh = self.get_token(user)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        }
        return data


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "full_name", "email", "date_joined")
        read_only_fields = fields

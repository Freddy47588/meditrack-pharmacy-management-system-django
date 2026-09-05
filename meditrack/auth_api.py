from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=150)
    password = serializers.CharField(write_only=True, min_length=5)
    password2 = serializers.CharField(write_only=True, min_length=5)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username sudah dipakai.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Password tidak sama."})
        try:
            validate_password(attrs["password"], User(username=attrs["username"]))
        except ValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
        )
        return user


class RegisteredUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer, responses={201: RegisteredUserSerializer}
    )
    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(
            {"id": user.id, "username": user.username}, status=status.HTTP_201_CREATED
        )

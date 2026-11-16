"""Login com throttling e `/api/v1/me/` · throttled login and `/api/v1/me/` (Ficha 03)."""

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView


class ThrottledTokenView(TokenObtainPairView):
    """10 tentativas por minuto por IP → 429 · 10 attempts per minute per IP → 429."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=inline_serializer(
            "Me",
            {
                "id": serializers.IntegerField(),
                "username": serializers.CharField(),
                "groups": serializers.ListField(child=serializers.CharField()),
            },
        )
    )
    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.get_username(),
                "groups": list(user.groups.values_list("name", flat=True)),
            }
        )

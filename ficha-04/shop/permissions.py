"""Permissões por papel e por objeto · role and object permissions (Ficha 03, parte 2).

PT: o papel é a pertença ao grupo `gestores` (o modelo User continua vazio);
a propriedade verifica-se no objeto E no queryset — as duas camadas, sempre.
EN: the role is membership of the `gestores` group (User stays empty);
ownership is checked on the object AND in the queryset — both layers, always.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_gestor(user):
    """Uma query por pedido, não uma por chamada · one query per request, not per call."""
    if not user.is_authenticated:
        return False
    if not hasattr(user, "_is_gestor"):
        user._is_gestor = user.groups.filter(name="gestores").exists()
    return user._is_gestor


class IsGestor(BasePermission):
    def has_permission(self, request, view):
        return is_gestor(request.user)


class IsGestorOrReadOnly(BasePermission):
    """Leituras para toda a gente (catálogo), escritas só para gestores.
    Reads for everyone (catalogue), writes for managers only."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_gestor(request.user)


class IsOwnerOrGestor(BasePermission):
    """Corre em get_object(): retrieve/update/destroy e ações detail=True (pay, cancel).
    Does NOT run on list/create — hence the queryset filter and perform_create."""

    def has_object_permission(self, request, view, obj):
        owner_id = getattr(obj, "customer", None) and obj.customer.user_id
        return is_gestor(request.user) or owner_id == request.user.id

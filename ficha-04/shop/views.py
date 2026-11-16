"""ViewSets · sem N+1 nos endpoints de lista · no N+1 on list endpoints."""

from django.db.models import F, Prefetch, Sum
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import OrderFilter, ProductFilter
from .models import LINE_TOTAL, Category, Customer, Order, OrderItem, Payment, Product
from .permissions import IsGestor, IsGestorOrReadOnly, IsOwnerOrGestor, is_gestor
from .serializers import (
    CategorySerializer,
    CustomerSerializer,
    GestorOrderSerializer,
    OrderItemSerializer,
    OrderSerializer,
    PaymentSerializer,
    ProductSerializer,
)
from .services import Conflict, cancel_order, pay_order


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]  # catálogo público, de propósito · public catalogue, on purpose
    search_fields = ["name"]
    ordering_fields = ["name"]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category")
    serializer_class = ProductSerializer
    # leitura pública, escrita só para gestores · public reads, writes for managers only
    permission_classes = [IsGestorOrReadOnly]
    filterset_class = ProductFilter
    search_fields = ["name", "sku"]
    ordering_fields = ["price", "name", "created_at"]
    ordering = ["name"]


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.select_related("user")
    serializer_class = CustomerSerializer
    permission_classes = [IsGestor]
    search_fields = ["user__username", "user__email"]


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.none()  # só para o drf-spectacular; o real está em get_queryset
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrGestor]
    filterset_class = OrderFilter
    ordering_fields = ["created_at", "total"]
    ordering = [
        "-created_at"
    ]  # explícito: annotate() perde o Meta.ordering · annotate() drops Meta.ordering
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        items = OrderItem.objects.select_related("product").annotate(
            line_total=F("quantity") * F("unit_price")
        )
        qs = (
            Order.objects.select_related("customer__user")
            .prefetch_related(Prefetch("items", queryset=items))
            .annotate(total=Sum(LINE_TOTAL))
        )
        # camada 1: o cliente só vê as suas; uma alheia é 404, não 403
        # layer 1: a customer only sees their own; someone else's is a 404, not a 403
        if is_gestor(self.request.user):
            return qs
        return qs.filter(customer__user=self.request.user)

    def get_serializer_class(self):
        if is_gestor(self.request.user):
            return GestorOrderSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        # o dono vem do pedido, nunca do corpo · the owner comes from the request, never the body
        customer, _ = Customer.objects.get_or_create(user=self.request.user)
        serializer.save(customer=customer)

    @extend_schema(
        request=None,
        responses={200: OrderSerializer, 409: OpenApiResponse(description="Order is not pending")},
    )
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        pay_order(self.get_object())
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(
        request=None,
        responses={200: OrderSerializer, 409: OpenApiResponse(description="Order is not pending")},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        cancel_order(self.get_object())
        return Response(self.get_serializer(self.get_object()).data)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.none()  # schema only · the real one is get_queryset
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["order", "product"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = OrderItem.objects.select_related("product", "order__customer").annotate(
            line_total=F("quantity") * F("unit_price")
        )
        if is_gestor(self.request.user):
            return qs
        return qs.filter(order__customer__user=self.request.user)

    def perform_create(self, serializer):
        # só se pode acrescentar linhas às próprias encomendas pendentes
        # lines can only be added to your own pending orders
        order = serializer.validated_data["order"]
        if not is_gestor(self.request.user) and order.customer.user_id != self.request.user.id:
            raise NotFound()
        if order.status != Order.Status.PENDING:
            raise Conflict(f"Order #{order.pk} is {order.status}.")
        serializer.save()


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.none()  # schema only · the real one is get_queryset
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["order", "method"]

    def get_queryset(self):
        qs = Payment.objects.select_related("order__customer")
        if is_gestor(self.request.user):
            return qs
        return qs.filter(order__customer__user=self.request.user)

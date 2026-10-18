import random

from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import NotificationLog, PriceAlert
from .permissions import IsAdminUser
from .serializers import PriceAlertSerializer, RegisterSerializer

MOCK_PRICES = {
    'DEL-BOM': (3000, 7000),
    'BLR-HYD': (1500, 4000),
    'DEL-BLR': (4000, 9000),
    'BOM-GOA': (2000, 5000),
}


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # 400 on duplicate / invalid
        user = serializer.save()
        access = str(RefreshToken.for_user(user).access_token)
        return Response(
            {'username': user.username, 'access': access, 'role': user.profile.role},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        user = authenticate(
            username=request.data.get('username'),
            password=request.data.get('password'),
        )
        if user is None:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        access = str(RefreshToken.for_user(user).access_token)
        return Response({'username': user.username, 'access': access, 'role': user.profile.role})


class AlertListCreateView(generics.ListCreateAPIView):
    serializer_class = PriceAlertSerializer

    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AlertDeactivateView(APIView):
    def delete(self, request, id):
        alert = get_object_or_404(PriceAlert, id=id)
        if alert.user != request.user:
            raise Http404
        alert.status = PriceAlert.Status.INACTIVE
        alert.save(update_fields=['status'])
        return Response({'status': 'inactive'}, status=status.HTTP_200_OK)


def get_flight_price(request):
    route = request.GET.get('route', '')
    price_range = MOCK_PRICES.get(route)
    if not price_range:
        return JsonResponse({'error': 'Route not found'}, status=404)
    return JsonResponse({'route': route, 'price': random.randint(*price_range)})


class AdminSummaryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        stats = PriceAlert.objects.aggregate(
            total_alerts=Count('id'),
            active_alerts=Count('id', filter=Q(status=PriceAlert.Status.ACTIVE)),
            triggered_alerts=Count('id', filter=Q(status=PriceAlert.Status.TRIGGERED)),
        )
        stats['total_notifications'] = NotificationLog.objects.aggregate(c=Count('id'))['c']
        rows = (
            PriceAlert.objects.values('origin', 'destination')
            .annotate(alert_count=Count('id'))
            .order_by('-alert_count')[:5]
        )
        stats['top_routes'] = [
            {'route': f"{r['origin']}-{r['destination']}", 'alert_count': r['alert_count']}
            for r in rows
        ]
        return Response(stats)
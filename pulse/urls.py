from django.urls import path

from .views import (
    AdminSummaryView, AlertDeactivateView, AlertListCreateView,
    LoginView, RegisterView, get_flight_price,
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('alerts/', AlertListCreateView.as_view()),
    path('alerts/<int:id>/', AlertDeactivateView.as_view()),
    path('flights/price/', get_flight_price),
    path('admin/summary/', AdminSummaryView.as_view()),
]
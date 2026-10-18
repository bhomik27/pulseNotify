from decimal import Decimal

import requests
from celery import shared_task
from django.conf import settings

from .models import NotificationLog, PriceAlert


def should_trigger(price, threshold):
    """Equality triggers: price <= threshold."""
    return Decimal(str(price)) <= Decimal(str(threshold))


@shared_task
def check_prices():
    active_alerts = PriceAlert.objects.filter(status=PriceAlert.Status.ACTIVE)
    routes = active_alerts.values_list('origin', 'destination').distinct()

    for origin, destination in routes:
        route = f'{origin}-{destination}'
        try:
            response = requests.get(settings.PRICE_FEED_URL, params={'route': route}, timeout=5)
        except requests.RequestException:
            continue
        if response.status_code != 200:
            continue
        current_price = response.json().get('price')

        for alert in active_alerts.filter(origin=origin, destination=destination):
            if should_trigger(current_price, alert.threshold_price):
                send_notification.delay(alert.id, current_price)


@shared_task
def send_notification(alert_id, triggered_price):
    alert = PriceAlert.objects.get(id=alert_id)
    if alert.status != PriceAlert.Status.ACTIVE:  # idempotency guard
        return
    message = (
        f'Price alert triggered! {alert.origin}-{alert.destination} '
        f'is now ₹{triggered_price} - below your threshold of ₹{alert.threshold_price}'
    )
    NotificationLog.objects.create(alert=alert, triggered_price=triggered_price, message=message)
    alert.status = PriceAlert.Status.TRIGGERED
    alert.save(update_fields=['status'])
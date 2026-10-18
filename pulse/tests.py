from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import NotificationLog, PriceAlert
from .tasks import check_prices, send_notification, should_trigger


def make_alert(user, origin='DEL', destination='BOM', threshold='4500'):
    return PriceAlert.objects.create(
        user=user, origin=origin, destination=destination, threshold_price=Decimal(threshold)
    )


class PriceThresholdTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='securepass')
        self.alert = make_alert(self.user)

    def test_price_below_threshold_triggers(self):
        self.assertTrue(should_trigger(4200, self.alert.threshold_price))

    def test_price_above_threshold_does_not_trigger(self):
        self.assertFalse(should_trigger(4800, self.alert.threshold_price))

    def test_price_equal_to_threshold_triggers(self):
        self.assertTrue(should_trigger(4500, self.alert.threshold_price))

    @patch('pulse.tasks.send_notification.delay')
    @patch('pulse.tasks.requests.get')
    def test_check_prices_fires_only_when_below(self, mock_get, mock_delay):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'route': 'DEL-BOM', 'price': 4200}
        check_prices()
        mock_delay.assert_called_once_with(self.alert.id, 4200)

    @patch('pulse.tasks.send_notification.delay')
    @patch('pulse.tasks.requests.get')
    def test_check_prices_skips_when_above(self, mock_get, mock_delay):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'route': 'DEL-BOM', 'price': 6000}
        check_prices()
        mock_delay.assert_not_called()


class NotificationLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='securepass')
        self.alert = make_alert(self.user)

    def test_send_notification_creates_log_and_marks_triggered(self):
        send_notification(self.alert.id, 4200)
        log = NotificationLog.objects.get()
        self.assertEqual(log.triggered_price, Decimal('4200'))
        self.assertEqual(log.alert, self.alert)
        self.assertIn('DEL-BOM', log.message)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, PriceAlert.Status.TRIGGERED)

    def test_send_notification_is_idempotent(self):
        send_notification(self.alert.id, 4200)
        send_notification(self.alert.id, 4100)
        self.assertEqual(NotificationLog.objects.count(), 1)


class AlertScopingTest(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', password='securepass')
        self.bob = User.objects.create_user('bob', password='securepass')
        self.alice_alert = make_alert(self.alice)
        self.bob_alert = make_alert(self.bob, 'BLR', 'HYD', '2000')
        self.client = APIClient()

    def test_queryset_contains_only_own_alerts(self):
        alerts = PriceAlert.objects.filter(user=self.alice)
        self.assertEqual(list(alerts), [self.alice_alert])

    def test_api_list_returns_only_callers_alerts(self):
        self.client.force_authenticate(self.alice)
        response = self.client.get('/api/alerts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([a['id'] for a in response.json()], [self.alice_alert.id])

    def test_delete_other_users_alert_returns_404(self):
        self.client.force_authenticate(self.alice)
        response = self.client.delete(f'/api/alerts/{self.bob_alert.id}/')
        self.assertEqual(response.status_code, 404)
        self.bob_alert.refresh_from_db()
        self.assertEqual(self.bob_alert.status, PriceAlert.Status.ACTIVE)

    def test_delete_own_alert_sets_inactive(self):
        self.client.force_authenticate(self.alice)
        response = self.client.delete(f'/api/alerts/{self.alice_alert.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'inactive'})

    def test_non_admin_gets_403_on_summary(self):
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get('/api/admin/summary/').status_code, 403)

    def test_role_in_register_body_is_ignored(self):
        response = APIClient().post(
            '/api/auth/register/',
            {'username': 'eve', 'password': 'securepass', 'role': 'admin'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['role'], 'user')
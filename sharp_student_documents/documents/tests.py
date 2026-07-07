from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class UploadDocumentAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_buyer_is_redirected_away_from_upload_page(self):
        buyer = self.user_model.objects.create_user(
            username="buyer_user",
            password="testpass123",
        )
        self.client.force_login(buyer)

        response = self.client.get(reverse("documents:upload_document"))

        self.assertRedirects(response, reverse("documents:buyer_dashboard"))

    def test_superuser_is_redirected_to_admin_dashboard(self):
        admin = self.user_model.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="testpass123",
        )
        self.client.force_login(admin)

        response = self.client.get(reverse("documents:upload_document"))

        self.assertRedirects(response, reverse("documents:admin_dashboard"))

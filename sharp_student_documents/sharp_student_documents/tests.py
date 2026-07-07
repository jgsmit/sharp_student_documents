from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import path

from . import views


def boom_403(request):
    raise PermissionDenied("blocked")


def boom_404(request):
    raise Http404("missing")


def boom_500(request):
    raise RuntimeError("server blew up")


urlpatterns = [
    path("test-403/", boom_403),
    path("test-404/", boom_404),
    path("test-500/", boom_500),
]


class ErrorPageTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_400_handler_renders_template(self):
        response = views.bad_request(self.factory.get("/bad-request/"), Exception("bad request"))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Bad Request", status_code=400)

    def test_403_handler_renders_template(self):
        response = views.permission_denied(self.factory.get("/forbidden/"), Exception("forbidden"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Access Denied", status_code=403)

    def test_404_handler_renders_template(self):
        response = views.page_not_found(self.factory.get("/missing/"), Exception("missing"))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page Not Found", status_code=404)

    def test_500_handler_renders_template(self):
        response = views.server_error(self.factory.get("/server-error/"))
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Something Went Wrong", status_code=500)


@override_settings(ROOT_URLCONF="sharp_student_documents.tests", DEBUG=False, ALLOWED_HOSTS=["testserver"])
class ErrorHandlerIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False)

    def test_403_handler_is_used_by_django(self):
        response = self.client.get("/test-403/")
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Access Denied", status_code=403)

    def test_404_handler_is_used_by_django(self):
        response = self.client.get("/test-404/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page Not Found", status_code=404)

    def test_500_handler_is_used_by_django(self):
        response = self.client.get("/test-500/")
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Something Went Wrong", status_code=500)

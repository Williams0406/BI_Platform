from django.test import TestCase, override_settings


class HealthEndpointTests(TestCase):

    def test_root_endpoint(self):
        response = self.client.get("/api/v1/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_liveness_endpoint(self):
        response = self.client.get("/api/v1/health/live/")

        self.assertEqual(response.status_code, 200)

        payload = response.json()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["check"], "liveness")

    @override_settings(
        OPS_READY_CHECK_REDIS=False,
        OPS_READY_CHECK_STORAGE=False,
    )
    def test_readiness_endpoint(self):
        response = self.client.get("/api/v1/health/ready/")

        self.assertEqual(
            response.status_code,
            200,
            msg=f"Readiness response: {response.content.decode()}",
        )

        payload = response.json()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(
            payload["checks"]["database"],
            "available",
        )

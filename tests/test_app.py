import os
import tempfile
import unittest
import app as queue_app


class QueueAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        queue_app.DB_PATH = os.path.join(self.temp_dir.name, "test_queue.db")
        queue_app.app.config["TESTING"] = True
        self.client = queue_app.app.test_client()
        queue_app.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def register_patient(self, name, department="General Medicine"):
        return self.client.post("/register", data={
            "patient_name": name,
            "department": department
        }, follow_redirects=True)

    def test_home_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Patient registration", response.data)

    def test_registration_creates_token(self):
        response = self.register_patient("Demo Patient")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"A001", response.data)

    def test_staff_call_next_and_complete(self):
        self.register_patient("Demo Patient")
        self.client.post("/staff/call-next", follow_redirects=True)
        data = self.client.get("/api/queue").get_json()
        self.assertEqual(data["current"]["token_label"], "A001")
        self.assertEqual(data["serving_count"], 1)

        with queue_app.get_db() as conn:
            patient_id = conn.execute(
                "SELECT id FROM patients WHERE token_label='A001'"
            ).fetchone()["id"]
        response = self.client.post(
            f"/staff/complete/{patient_id}", follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        data = self.client.get("/api/queue").get_json()
        self.assertIsNone(data["current"])

    def test_invalid_department_is_rejected(self):
        response = self.client.post("/register", data={
            "patient_name": "Demo Patient",
            "department": "Not a department"
        }, follow_redirects=True)
        self.assertIn(b"Please select a valid department", response.data)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()

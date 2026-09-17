import io
from rest_framework.test import APITestCase
from rest_framework import status
from apps.core.test_utils import make_org
from .models import User
from .bulk_import import import_users_from_csv


class UserScopingTests(APITestCase):
    """Regression coverage for the BA-sees-everyone scoping bug."""

    def setUp(self):
        self.org = make_org()

    def test_ba_listing_users_sees_only_self(self):
        self.client.force_authenticate(user=self.org["ba"])
        resp = self.client.get("/api/accounts/users/")
        results = resp.data["results"] if "results" in resp.data else resp.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.org["ba"].id)

    def test_supervisor_listing_users_sees_own_team_and_self_only(self):
        self.client.force_authenticate(user=self.org["supervisor"])
        resp = self.client.get("/api/accounts/users/")
        results = resp.data["results"] if "results" in resp.data else resp.data
        ids = {r["id"] for r in results}
        self.assertIn(self.org["ba"].id, ids)
        self.assertIn(self.org["supervisor"].id, ids)
        self.assertNotIn(self.org["other_ba"].id, ids)
        self.assertNotIn(self.org["other_supervisor"].id, ids)

    def test_manager_sees_everyone(self):
        self.client.force_authenticate(user=self.org["manager"])
        resp = self.client.get("/api/accounts/users/")
        results = resp.data["results"] if "results" in resp.data else resp.data
        self.assertGreaterEqual(len(results), 5)

    def test_ba_cannot_create_users(self):
        self.client.force_authenticate(user=self.org["ba"])
        resp = self.client.post("/api/accounts/users/", {
            "username": "sneaky", "password": "whatever123", "role": "BA",
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class SetPasswordTests(APITestCase):
    def setUp(self):
        self.org = make_org()

    def test_bulk_imported_user_can_set_own_password_and_flag_clears(self):
        self.org["ba"].must_change_password = True
        self.org["ba"].save()

        self.client.force_authenticate(user=self.org["ba"])
        resp = self.client.post("/api/accounts/users/set_password/", {"new_password": "brandnewpass1"})
        self.assertEqual(resp.status_code, 200)

        self.org["ba"].refresh_from_db()
        self.assertFalse(self.org["ba"].must_change_password)
        self.assertTrue(self.org["ba"].check_password("brandnewpass1"))

    def test_rejects_short_password(self):
        self.client.force_authenticate(user=self.org["ba"])
        resp = self.client.post("/api/accounts/users/set_password/", {"new_password": "short"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class BulkImportTests(APITestCase):
    def setUp(self):
        self.org = make_org()

    def test_import_creates_users_with_temp_password_and_must_change_flag(self):
        csv_content = (
            "first_name,last_name,username,phone,region,supervisor_username,role\n"
            "Test,Person,test_person,+263771111111,Harare CBD,supervisor,BA\n"
        )
        result = import_users_from_csv(io.StringIO(csv_content))
        self.assertEqual(len(result.created), 1)
        self.assertEqual(len(result.errors), 0)

        created = User.objects.get(username="test_person")
        self.assertTrue(created.must_change_password)
        self.assertEqual(created.role, "BA")
        self.assertEqual(created.supervisor, self.org["supervisor"])
        # temp password returned must actually be the working password
        temp_password = result.created[0]["temp_password"]
        self.assertTrue(created.check_password(temp_password))

    def test_import_rejects_duplicate_username_but_keeps_going(self):
        csv_content = (
            "first_name,last_name,username,role\n"
            "Dup,User,ba1,BA\n"  # 'ba1' already exists from make_org()
            "New,Person,,BA\n"   # blank username — should still succeed
        )
        result = import_users_from_csv(io.StringIO(csv_content))
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.created), 1)

    def test_import_rejects_unknown_supervisor(self):
        csv_content = (
            "first_name,last_name,supervisor_username,role\n"
            "New,Person,nonexistent_supervisor,BA\n"
        )
        result = import_users_from_csv(io.StringIO(csv_content))
        self.assertEqual(len(result.created), 0)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("nonexistent_supervisor", result.errors[0]["error"])

    def test_bulk_import_endpoint_requires_supervisor_or_above(self):
        self.client.force_authenticate(user=self.org["ba"])
        csv_file = io.BytesIO(b"first_name,last_name\nA,B\n")
        csv_file.name = "test.csv"
        resp = self.client.post("/api/accounts/users/bulk_import/", {"file": csv_file}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

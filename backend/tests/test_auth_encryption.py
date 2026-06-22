import unittest
import requests
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend


class TestAuthEncryption(unittest.TestCase):
    BASE_URL = "http://localhost:8000"

    def test_public_key_endpoint(self):
        """Test public key endpoint"""
        response = requests.get(f"{self.BASE_URL}/api/auth/public-key")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("public_key", data)
        self.assertIn("-----BEGIN PUBLIC KEY-----", data["public_key"])
        self.assertIn("-----END PUBLIC KEY-----", data["public_key"])

    def test_login_with_encrypted_password(self):
        """Test login with encrypted password"""
        # Get public key
        response = requests.get(f"{self.BASE_URL}/api/auth/public-key")
        self.assertEqual(response.status_code, 200)
        public_key = response.json()["public_key"]
        
        # Encrypt password
        password = "Test@bcd!234"
        public_key_obj = serialization.load_pem_public_key(public_key.encode(), backend=default_backend())
        encrypted = public_key_obj.encrypt(
            password.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        encrypted_base64 = f"encrypted:{base64.b64encode(encrypted).decode()}"
        
        # Login
        response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={"username": "admin", "password": encrypted_base64}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("username", data)
        self.assertEqual(data["username"], "admin")

    def test_login_with_plain_password(self):
        """Test login with plain password (backward compatibility)"""
        response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={"username": "admin", "password": "Test@bcd!234"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)

    def test_change_password_with_encrypted_password(self):
        """Test change password with encrypted passwords"""
        # First login to get token
        login_response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={"username": "admin", "password": "Test@bcd!234"}
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["token"]
        
        # Get public key
        key_response = requests.get(f"{self.BASE_URL}/api/auth/public-key")
        public_key = key_response.json()["public_key"]
        
        # Encrypt passwords
        old_password = "Test@bcd!234"
        new_password = "NewPass@567!"
        
        public_key_obj = serialization.load_pem_public_key(public_key.encode(), backend=default_backend())
        encrypted_old = public_key_obj.encrypt(
            old_password.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        encrypted_new = public_key_obj.encrypt(
            new_password.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Change password
        response = requests.post(
            f"{self.BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "admin",
                "old_password": f"encrypted:{base64.b64encode(encrypted_old).decode()}",
                "new_password": f"encrypted:{base64.b64encode(encrypted_new).decode()}"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        
        # Test login with new password
        login_response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={"username": "admin", "password": "NewPass@567!"}
        )
        self.assertEqual(login_response.status_code, 200)
        
        # Change back to original password
        response = requests.post(
            f"{self.BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {login_response.json()['token']}"},
            json={
                "username": "admin",
                "old_password": "NewPass@567!",
                "new_password": "Test@bcd!234"
            }
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
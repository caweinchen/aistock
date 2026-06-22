import unittest
from backend.app.rsa_utils import get_rsa_utils
from backend.app.main import decrypt_password


class TestRSAEncryption(unittest.TestCase):
    def test_rsa_key_generation(self):
        """Test RSA key pair generation"""
        rsa_utils = get_rsa_utils()
        public_key = rsa_utils.get_public_key()
        
        self.assertIsNotNone(public_key)
        self.assertIn("-----BEGIN PUBLIC KEY-----", public_key)
        self.assertIn("-----END PUBLIC KEY-----", public_key)

    def test_encryption_decryption(self):
        """Test encryption and decryption round trip"""
        rsa_utils = get_rsa_utils()
        test_password = "Test@bcd!234"
        
        # Encrypt using public key
        public_key = rsa_utils.get_public_key()
        
        # Simulate frontend encryption using cryptography library
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.backends import default_backend
        
        public_key_obj = serialization.load_pem_public_key(public_key.encode(), backend=default_backend())
        encrypted = public_key_obj.encrypt(
            test_password.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt using private key
        decrypted = rsa_utils.decrypt(encrypted)
        
        self.assertEqual(decrypted, test_password)

    def test_decrypt_password_with_prefix(self):
        """Test decrypt_password function with encrypted prefix"""
        rsa_utils = get_rsa_utils()
        test_password = "Test@bcd!234"
        
        public_key = rsa_utils.get_public_key()
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.backends import default_backend
        import base64
        
        public_key_obj = serialization.load_pem_public_key(public_key.encode(), backend=default_backend())
        encrypted = public_key_obj.encrypt(
            test_password.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        encrypted_base64 = f"encrypted:{base64.b64encode(encrypted).decode()}"
        decrypted = decrypt_password(encrypted_base64)
        
        self.assertEqual(decrypted, test_password)

    def test_decrypt_password_plaintext(self):
        """Test decrypt_password function with plain text (backward compatibility)"""
        test_password = "Test@bcd!234"
        result = decrypt_password(test_password)
        
        self.assertEqual(result, test_password)

    def test_decrypt_password_empty(self):
        """Test decrypt_password function with empty password"""
        result = decrypt_password("")
        self.assertEqual(result, "")

    def test_decrypt_password_none(self):
        """Test decrypt_password function with None"""
        result = decrypt_password(None)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
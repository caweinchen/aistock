import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
import os

class RSAUtils:
    _instance = None
    _private_key = None
    _public_key = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RSAUtils, cls).__new__(cls)
            cls._instance._init_keys()
        return cls._instance

    def _init_keys(self):
        key_path = os.path.join(os.path.dirname(__file__), 'rsa_keys')
        os.makedirs(key_path, exist_ok=True)
        
        private_key_file = os.path.join(key_path, 'private_key.pem')
        public_key_file = os.path.join(key_path, 'public_key.pem')

        if os.path.exists(private_key_file) and os.path.exists(public_key_file):
            with open(private_key_file, 'rb') as f:
                self._private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
            with open(public_key_file, 'rb') as f:
                self._public_key = serialization.load_pem_public_key(f.read(), backend=default_backend())
        else:
            self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
            self._public_key = self._private_key.public_key()

            with open(private_key_file, 'wb') as f:
                f.write(self._private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            with open(public_key_file, 'wb') as f:
                f.write(self._public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

    def get_public_key(self) -> str:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    def decrypt(self, encrypted_data: bytes) -> str:
        decrypted = self._private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted.decode('utf-8')

    def decrypt_base64(self, encrypted_base64: str) -> str:
        import base64
        encrypted_data = base64.b64decode(encrypted_base64)
        return self.decrypt(encrypted_data)

def get_rsa_utils() -> RSAUtils:
    return RSAUtils()
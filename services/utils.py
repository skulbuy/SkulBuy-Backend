import hashlib
import secrets
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hashes a plaintext password using argon2 / bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

def generate_otp(length: int = 6) -> str:
    """Generates a secure numeric OTP for delivery proof."""
    return "".join(secrets.choice("0123456789") for _ in range(length))

def hash_otp(raw_otp: str) -> str:
    """Hashes an OTP using SHA-256 for secure DB persistence."""
    return hashlib.sha256(raw_otp.strip().encode()).hexdigest()

def verify_otp(raw_otp: str, hashed_otp: str) -> bool:
    """Verifies an OTP against its SHA-256 hash."""
    return hash_otp(raw_otp) == hashed_otp

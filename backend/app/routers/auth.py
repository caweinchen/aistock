from datetime import datetime, timezone, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import AuthSession, User, get_db
from app.rsa_utils import get_rsa_utils
from app.schemas import ChangePasswordRequest, LoginRequest, LoginResponse, PasswordStrengthResponse, RegisterRequest, UserResponse
from app.security import generate_auth_token, hash_password, hash_token, is_password_hash, validate_password_strength, verify_password

logger = logging.getLogger("stocks")
router = APIRouter(prefix="/api/auth")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """验证token并返回当前用户"""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_hash = hash_token(token)
    session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash).first()
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 处理时区问题
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Token expired")
    
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user




@router.get("/public-key")
def get_public_key():
    """Get RSA public key for password encryption."""
    rsa_utils = get_rsa_utils()
    return {"public_key": rsa_utils.get_public_key()}


def decrypt_password(encrypted_password: str | None) -> str:
    """Decrypt password if it's encrypted, otherwise return as-is for backward compatibility."""
    if not encrypted_password:
        return ""
    
    if encrypted_password.startswith('encrypted:'):
        try:
            rsa_utils = get_rsa_utils()
            return rsa_utils.decrypt_base64(encrypted_password[10:])
        except Exception as e:
            logger.error(f"Failed to decrypt password: {e}")
            raise HTTPException(status_code=400, detail="Invalid encrypted password")
    
    return encrypted_password


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """User login endpoint. Supports both encrypted and plain password for backward compatibility."""
    logger.info(f"Login attempt for username: {request.username}")
    
    try:
        password = decrypt_password(request.password)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password decryption error: {e}")
        raise HTTPException(status_code=400, detail="Invalid password format")

    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        logger.info(f"User {request.username} not found, attempting auto-create")
        # Auto-create user if not exists (for demo purposes)
        if request.username == "admin" and password == "Test@bcd!234":
            user = User(username=request.username, password=hash_password(password), is_active=True, role="admin")
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"User {request.username} created successfully")
        else:
            logger.warning(f"Failed to auto-create user {request.username}: invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid username or password")

    logger.info(f"User found: {user.username}, verifying password...")
    if not verify_password(password, user.password):
        logger.warning(f"Password verification failed for user {request.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        logger.warning(f"Inactive user attempted login: {request.username}")
        raise HTTPException(status_code=403, detail="Account is inactive")

    if not is_password_hash(user.password):
        user.password = hash_password(password)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()

    token = generate_auth_token()
    db.add(AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    ))
    db.commit()
    logger.info(f"Login successful for user {request.username}")

    return LoginResponse(
        token=token,
        username=user.username,
        user_id=user.id,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/register", response_model=UserResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    try:
        password = decrypt_password(request.password)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password decryption error: {e}")
        raise HTTPException(status_code=400, detail="Invalid password format")

    strength = validate_password_strength(password)
    if not strength["valid"]:
        raise HTTPException(status_code=400, detail=strength["messages"])

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=username,
        password=hash_password(password),
        is_active=False,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password")
def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db)):
    """Change password endpoint. Supports encrypted passwords."""
    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        old_password = decrypt_password(request.old_password)
        new_password = decrypt_password(request.new_password)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password decryption error: {e}")
        raise HTTPException(status_code=400, detail="Invalid password format")

    if not verify_password(old_password, user.password):
        raise HTTPException(status_code=401, detail="Old password is incorrect")

    strength = validate_password_strength(new_password)
    if not strength["valid"]:
        raise HTTPException(status_code=400, detail=strength["messages"])

    user.password = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "message": "Password changed successfully"}


@router.post("/validate-password", response_model=PasswordStrengthResponse)
def check_password_strength(password: str):
    """妤犲矁鐦夌€靛棛鐖滃鍝勫€"""
    return validate_password_strength(password)


@router.get("/verify")
def verify_token(user: User = Depends(get_current_user)):
    """Verify token is valid and get user info."""
    return {
        "valid": True,
        "username": user.username,
        "user_id": user.id,
        "role": user.role,
        "is_active": user.is_active,
    }


@router.get("/generate-password")
def generate_strong_password():
    """Generate a strong random password."""
    import random
    import string

    lowercase = random.choice(string.ascii_lowercase)
    uppercase = random.choice(string.ascii_uppercase)
    digit = random.choice(string.digits)
    special = random.choice("!@#$%^&*")

    remaining_chars = random.choices(
        string.ascii_letters + string.digits + "!@#$%^&*",
        k=4
    )

    password_list = list(lowercase + uppercase + digit + special + ''.join(remaining_chars))
    random.shuffle(password_list)
    password = ''.join(password_list)

    return {"password": password, "length": len(password)}

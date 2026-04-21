import os, json, logging
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)
TOKENS_DIR = Path(os.getenv("TOKENS_DIR", "config/tokens"))
TOKENS_DIR.mkdir(parents=True, exist_ok=True)

try:
    os.chmod(TOKENS_DIR, 0o700)
except Exception:
    pass


def _fernet():
    key = os.getenv("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY missing in config/.env\n"
            "Run: python -c \"from cryptography.fernet import "
            "Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def save_token(provider: str, data: dict):
    encrypted = _fernet().encrypt(json.dumps(data).encode())
    path = TOKENS_DIR / f"{provider}.enc"
    path.write_bytes(encrypted)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    logger.info(f"Token saved: {provider}")


def load_token(provider: str) -> dict | None:
    path = TOKENS_DIR / f"{provider}.enc"
    if not path.exists():
        return None
    try:
        return json.loads(_fernet().decrypt(path.read_bytes()))
    except InvalidToken:
        logger.error(f"Cannot decrypt token: {provider}")
        return None


def delete_token(provider: str) -> bool:
    path = TOKENS_DIR / f"{provider}.enc"
    if path.exists():
        path.write_bytes(b"\x00" * path.stat().st_size)
        path.unlink()
        return True
    return False


def list_connected() -> list[str]:
    return [p.stem for p in TOKENS_DIR.glob("*.enc")]


def revoke_all():
    for p in TOKENS_DIR.glob("*.enc"):
        p.write_bytes(b"\x00" * p.stat().st_size)
        p.unlink()
    logger.warning("All tokens revoked.")
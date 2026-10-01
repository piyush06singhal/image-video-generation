import hashlib
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes client-provided filename to prevent path traversal and shell injection.
    Strips directory separators, non-printable characters, and keeps safe alphanumeric chars.
    """
    # Remove directory paths if present
    base_name = os.path.basename(filename)
    
    # Replace dangerous or whitespace characters with underscores
    clean_name = re.sub(r"[^\w\.\-]", "_", base_name)
    
    # Avoid empty filename or hidden dotfiles
    clean_name = clean_name.lstrip(".")
    if not clean_name:
        clean_name = f"image_{secrets.token_hex(4)}"
        
    # Limit length
    if len(clean_name) > 100:
        name_part, ext = os.path.splitext(clean_name)
        clean_name = name_part[: 100 - len(ext)] + ext
        
    return clean_name


def generate_project_id() -> str:
    """
    Generates a unique timestamped project ID in the format:
    project_YYYYMMDD_xxxxxx (e.g. project_20261001_a1b2c3)
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_suffix = secrets.token_hex(3)  # 6 hex chars
    return f"project_{date_str}_{random_suffix}"


def generate_image_id() -> str:
    """
    Generates a unique image identifier.
    """
    return f"img_{secrets.token_hex(6)}"


def calculate_sha256(data: bytes) -> str:
    """
    Computes standard SHA-256 hash for file content.
    """
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()

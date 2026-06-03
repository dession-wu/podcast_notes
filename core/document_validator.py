"""Document validation — pre and post conversion checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Validation failure."""
    pass


class DocumentValidator:
    """Validates documents before and after conversion."""

    MAX_FILE_SIZE_MB = 50
    SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig"]

    @staticmethod
    def pre_conversion_check(file_path: Path) -> dict[str, Any]:
        """Check file before processing.
        
        Returns:
            Dict with 'valid' (bool), 'errors' (list), 'warnings' (list).
        """
        errors = []
        warnings = []

        if not file_path.exists():
            errors.append(f"File not found: {file_path}")
            return {"valid": False, "errors": errors, "warnings": warnings}

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > DocumentValidator.MAX_FILE_SIZE_MB:
            errors.append(f"File too large: {size_mb:.1f}MB (max {DocumentValidator.MAX_FILE_SIZE_MB}MB)")

        if size_mb == 0:
            errors.append("File is empty")

        # Try reading with UTF-8
        try:
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                errors.append("File contains no text content")
        except UnicodeDecodeError:
            errors.append("File encoding is not UTF-8. Please convert to UTF-8.")
        except Exception as e:
            errors.append(f"Cannot read file: {e}")

        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
        logger.info("Pre-conversion check", file=str(file_path), **result)
        return result

    @staticmethod
    def post_conversion_check(output_dir: Path, expected_files: list[str]) -> dict[str, Any]:
        """Verify generated files exist and are valid.
        
        Returns:
            Dict with 'valid' (bool), 'missing' (list), 'corrupted' (list).
        """
        missing = []
        corrupted = []

        for filename in expected_files:
            file_path = output_dir / filename
            if not file_path.exists():
                missing.append(filename)
                continue
            if file_path.stat().st_size == 0:
                corrupted.append(f"{filename} (empty)")

        result = {
            "valid": len(missing) == 0 and len(corrupted) == 0,
            "missing": missing,
            "corrupted": corrupted,
        }
        logger.info("Post-conversion check", dir=str(output_dir), **result)
        return result

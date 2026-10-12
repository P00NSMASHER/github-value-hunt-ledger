"""Fail-closed, dependency-free image checks for RETALLY's public artifacts.

Metadata validation is not a replacement for human review of rendered images.
The approved logos additionally require exact SHA-256 identities.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

# Registration is intentional: newly added assets require review before use.
FREIGHT_IMAGE_BASES = frozenset({
    "approved-path", "dock-control", "freight-network", "human-review",
    "invoice-evidence", "rail-yard", "rate-authority", "terminal-blue-hour",
    "trailer-blue-hour", "truck-cab", "warehouse-handoff",
})
RECOVERY_IMAGE_NAMES = frozenset({
    "analyst-review.webp", "construction-project.webp",
    "healthcare-operations.webp", "hero-industrial.webp", "proof-stack.webp",
})
APPROVED_LOGOS = {
    "retally-wordmark-approved.png": (
        "08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd",
        (1619, 257),
    ),
    "retally-emblem-approved.png": (
        "bb02ab4a468762f597c241199baeff61b485dd793f8fb746140ad33670b68043",
        (805, 776),
    ),
}
MIN_WEBP_BYTES = 25_000
MAX_IMAGE_BYTES = 4_000_000


class AssetIntegrityError(ValueError):
    """A public-facing image failed the release boundary."""


def _read_safe(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise AssetIntegrityError(f"Missing or unsafe image source: {path.name}")
    data = path.read_bytes()
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise AssetIntegrityError(f"Empty or oversized image source: {path.name}")
    return data


def _registered(found: set[str], expected: set[str], group: str) -> None:
    if found != expected:
        raise AssetIntegrityError(
            f"{group} image register differs: missing={sorted(expected-found)}, "
            f"unreviewed={sorted(found-expected)}"
        )


def webp_dimensions(data: bytes) -> tuple[int, int]:
    """Read an ordinary RIFF/VP8 WebP without depending on Pillow or a browser."""
    if (len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP"
            or int.from_bytes(data[4:8], "little") + 8 != len(data)):
        raise AssetIntegrityError("Malformed or truncated WebP RIFF container")
    kind = data[12:16]
    if kind == b"VP8 ":
        if data[23:26] != b"\x9d\x01\x2a":
            raise AssetIntegrityError("Invalid VP8 dimension marker")
        width = int.from_bytes(data[26:28], "little") & 0x3fff
        height = int.from_bytes(data[28:30], "little") & 0x3fff
    elif kind == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        if data[20] != 0x2f:
            raise AssetIntegrityError("Invalid VP8L header")
        width = (bits & 0x3fff) + 1
        height = ((bits >> 14) & 0x3fff) + 1
    elif kind == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
    else:
        raise AssetIntegrityError("Unsupported WebP container encoding")
    if width < 1 or height < 1:
        raise AssetIntegrityError("Invalid WebP dimensions")
    return width, height


def assert_webp(data: bytes, label: str, min_width: int, min_height: int) -> tuple[int, int]:
    if len(data) < MIN_WEBP_BYTES:
        raise AssetIntegrityError(f"Unacceptably small image byte size: {label}")
    width, height = webp_dimensions(data)
    if width < min_width or height < min_height:
        raise AssetIntegrityError(
            f"Undersized {label}: {width}x{height}; requires {min_width}x{min_height}"
        )
    return width, height


def assert_approved_logo(data: bytes, name: str) -> None:
    digest, dimensions = APPROVED_LOGOS[name]
    if (len(data) < 24 or data[:16] !=
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"):
        raise AssetIntegrityError(f"Invalid PNG master: {name}")
    size = (int.from_bytes(data[16:20], "big"),
            int.from_bytes(data[20:24], "big"))
    if size != dimensions or hashlib.sha256(data).hexdigest() != digest:
        raise AssetIntegrityError(f"Approved original artwork changed: {name}")


def validate_freight_media(site: Path) -> None:
    """Verify source artwork, including images not yet used by the homepage."""
    image_dir = site / "assets" / "images"
    expected = {f"{base}.webp" for base in FREIGHT_IMAGE_BASES}
    expected |= {f"{base}-800.webp" for base in FREIGHT_IMAGE_BASES}
    _registered({p.name for p in image_dir.glob("*.webp")}, expected, "Freight")
    for base in sorted(FREIGHT_IMAGE_BASES):
        large = assert_webp(_read_safe(image_dir / f"{base}.webp"),
                            f"{base}.webp", 1100, 800)
        small = assert_webp(_read_safe(image_dir / f"{base}-800.webp"),
                            f"{base}-800.webp", 800, 450)
        if small[0] != 800 or abs(large[0]/large[1] - small[0]/small[1]) > 0.02:
            raise AssetIntegrityError(f"Responsive image pair geometry mismatch: {base}")
    brand = site / "assets" / "brand"
    for name in APPROVED_LOGOS:
        assert_approved_logo(_read_safe(brand / name), name)


def validate_recoveryos_media(site: Path) -> None:
    image_dir = site / "assets"
    _registered({p.name for p in image_dir.glob("*.webp")},
                set(RECOVERY_IMAGE_NAMES), "RecoveryOS")
    for name in sorted(RECOVERY_IMAGE_NAMES):
        assert_webp(_read_safe(image_dir / name), name, 1000, 900)

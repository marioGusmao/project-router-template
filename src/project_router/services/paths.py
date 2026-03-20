"""Shared path constants for Project Router.

Every module that needs project-level directory or file paths should import from
here rather than redefining them.  This keeps the layout in one place and makes
test patching straightforward.
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
#  Root and data directories
# ---------------------------------------------------------------------------
# In cli.py the root was parents[2] (src/project_router -> src -> ROOT).
# This file lives one level deeper (src/project_router/services/paths.py),
# so we need parents[3].
ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"
COMPILED_DIR = DATA_DIR / "compiled"
REVIEW_DIR = DATA_DIR / "review"
DISPATCHED_DIR = DATA_DIR / "dispatched"
PROCESSED_DIR = DATA_DIR / "processed"

# ---------------------------------------------------------------------------
#  State directories
# ---------------------------------------------------------------------------
STATE_DIR = ROOT / "state"
DECISIONS_DIR = STATE_DIR / "decisions"
DISCOVERIES_DIR = STATE_DIR / "discoveries"
PROJECT_ROUTER_STATE_DIR = STATE_DIR / "project_router"
OUTBOX_SCAN_STATE_PATH = PROJECT_ROUTER_STATE_DIR / "outbox_scan_state.json"
OUTBOX_SCAN_LOCK_PATH = PROJECT_ROUTER_STATE_DIR / "scan.lock"
ADOPTIONS_DIR = PROJECT_ROUTER_STATE_DIR / "adoptions"
INBOX_STATUS_DIR = PROJECT_ROUTER_STATE_DIR / "inbox_status"
DISCOVERY_REPORT_PATH = DISCOVERIES_DIR / "pending_project_latest.json"

# ---------------------------------------------------------------------------
#  Registry and config paths
# ---------------------------------------------------------------------------
REGISTRY_LOCAL_PATH = ROOT / "projects" / "registry.local.json"
REGISTRY_SHARED_PATH = ROOT / "projects" / "registry.shared.json"
REGISTRY_EXAMPLE_PATH = ROOT / "projects" / "registry.example.json"
ENV_LOCAL_PATH = ROOT / ".env.local"
ENV_PATH = ROOT / ".env"

# ---------------------------------------------------------------------------
#  Router / inbox paths
# ---------------------------------------------------------------------------
LOCAL_ROUTER_DIR = ROOT / "router"
LOCAL_ROUTER_ARCHIVE_DIR = LOCAL_ROUTER_DIR / "archive"

# ---------------------------------------------------------------------------
#  Template metadata paths
# ---------------------------------------------------------------------------
TEMPLATE_BASE_PATH = ROOT / "template-base.json"
PRIVATE_META_PATH = ROOT / "private.meta.json"
TEMPLATE_META_PATH = ROOT / "template.meta.json"
VERSION_PATH = ROOT / "version.txt"

# ---------------------------------------------------------------------------
#  Validation
# ---------------------------------------------------------------------------
NOTE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

# ---------------------------------------------------------------------------
#  Source constants
# ---------------------------------------------------------------------------
VOICE_SOURCE = "voicenotes"
PROJECT_ROUTER_SOURCE = "project_router"
FILESYSTEM_SOURCE = "filesystem"
READWISE_SOURCE = "readwise"
KNOWN_SOURCES = frozenset({VOICE_SOURCE, PROJECT_ROUTER_SOURCE, FILESYSTEM_SOURCE, READWISE_SOURCE})

# ---------------------------------------------------------------------------
#  Review queue constants
# ---------------------------------------------------------------------------
REVIEW_QUEUE_STATUSES = ("ambiguous", "needs_review", "pending_project")
FILESYSTEM_REVIEW_STATUSES = ("parse_errors", "needs_extraction", "needs_review", "ambiguous", "pending_project")
READWISE_REVIEW_STATUSES = ("ambiguous", "needs_review", "pending_project")
AMBIGUOUS_DIR = REVIEW_DIR / VOICE_SOURCE / "ambiguous"
NEEDS_REVIEW_DIR = REVIEW_DIR / VOICE_SOURCE / "needs_review"
PENDING_PROJECT_DIR = REVIEW_DIR / VOICE_SOURCE / "pending_project"


# ---------------------------------------------------------------------------
#  Source name normalisation
# ---------------------------------------------------------------------------
def normalize_source_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = str(raw).strip().lower()
    aliases = {
        "voice_notes": VOICE_SOURCE,
        "voice-notes": VOICE_SOURCE,
        "project-router": PROJECT_ROUTER_SOURCE,
        "filesystem": FILESYSTEM_SOURCE,
        "fs": FILESYSTEM_SOURCE,
        "local-inbox": FILESYSTEM_SOURCE,
        "inbox": FILESYSTEM_SOURCE,
        "reader": READWISE_SOURCE,
        "rw": READWISE_SOURCE,
    }
    return aliases.get(cleaned, cleaned)

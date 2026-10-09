"""Guard for the sealed preregistered test partition.

``evaluate.seed_set("prereg_test")`` refuses to return the seeds unless it is handed an ``UnsealToken``.
Tokens are only issued by ``verify_manifest`` (all preregistered runs complete, checkpoint hashes verified).
This prevents accidents (a stray ``--split`` or a copy-pasted call); it cannot stop someone who edits the code,
which is what the frozen commit hash and the procedural rules in docs/RESEARCH_LOG.md are for.
"""
from __future__ import annotations

_ISSUE_KEY = object()


class UnsealToken:
    """Proof that an integrity manifest was verified.  Do not construct directly."""

    def __init__(self, key, manifest_sha256: str):
        if key is not _ISSUE_KEY:
            raise TypeError("UnsealToken can only be issued by seal.verify_manifest")
        self.manifest_sha256 = manifest_sha256

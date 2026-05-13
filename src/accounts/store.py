"""Encrypted credential storage for platform accounts.

Credentials are stored AES-encrypted on disk using a master key derived
from a passphrase via PBKDF2. Each identity can have multiple platform
accounts to enable logged-in sessions.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_DEFAULT_ACCOUNTS_DIR = "data/accounts"


class AccountCredential(BaseModel):
    """Single platform account credential."""
    platform: str
    username: str
    password: str = ""
    email: str = ""
    phone: str = ""
    # Optional: recovery codes, 2FA secrets, etc.
    extra: dict[str, str] = Field(default_factory=dict)
    # Which identity this account is assigned to (None = unassigned/pool)
    identity_id: str | None = None
    # Whether this account is currently usable
    enabled: bool = True
    # Tags for grouping (e.g. "burner", "aged", "verified")
    tags: list[str] = Field(default_factory=list)


class AccountStore:
    """Manages encrypted storage of platform accounts.

    Accounts are stored in a single encrypted JSON file per-platform,
    protected by a passphrase-derived key.
    """

    def __init__(
        self,
        accounts_dir: str | Path = _DEFAULT_ACCOUNTS_DIR,
        passphrase: str | None = None,
    ) -> None:
        self._dir = Path(accounts_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._fernet = self._derive_key(passphrase or self._get_passphrase())
        self._accounts: dict[str, list[AccountCredential]] = {}
        self._loaded = False

    @staticmethod
    def _get_passphrase() -> str:
        """Get passphrase from environment or prompt."""
        passphrase = os.environ.get("PDP_ACCOUNTS_PASSPHRASE")
        if not passphrase:
            raise ValueError(
                "No passphrase provided. Set PDP_ACCOUNTS_PASSPHRASE env var "
                "or pass passphrase= to AccountStore."
            )
        return passphrase

    @staticmethod
    def _derive_key(passphrase: str) -> Fernet:
        """Derive a Fernet key from passphrase using PBKDF2."""
        # Use a fixed salt derived from project name (per-install, could be randomized)
        salt = b"pdp_personal_data_poison_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        return Fernet(key)

    def _store_path(self, platform: str) -> Path:
        return self._dir / f"{platform}.enc"

    def load(self) -> None:
        """Load all encrypted account files."""
        self._accounts.clear()
        for enc_file in self._dir.glob("*.enc"):
            platform = enc_file.stem
            try:
                ciphertext = enc_file.read_bytes()
                plaintext = self._fernet.decrypt(ciphertext)
                entries = json.loads(plaintext)
                self._accounts[platform] = [
                    AccountCredential(**entry) for entry in entries
                ]
                logger.info("Loaded %d accounts for %s", len(self._accounts[platform]), platform)
            except Exception:
                logger.exception("Failed to decrypt accounts for %s", platform)
        self._loaded = True

    def save(self, platform: str | None = None) -> None:
        """Save accounts to encrypted storage."""
        platforms_to_save = [platform] if platform else list(self._accounts.keys())
        for p in platforms_to_save:
            if p not in self._accounts:
                continue
            entries = [acc.model_dump() for acc in self._accounts[p]]
            plaintext = json.dumps(entries, indent=2).encode()
            ciphertext = self._fernet.encrypt(plaintext)
            self._store_path(p).write_bytes(ciphertext)
            logger.debug("Saved %d accounts for %s", len(entries), p)

    def add_account(self, credential: AccountCredential) -> None:
        """Add a new account credential."""
        platform = credential.platform
        if platform not in self._accounts:
            self._accounts[platform] = []

        # Check for duplicates
        for existing in self._accounts[platform]:
            if existing.username == credential.username:
                logger.warning("Account %s already exists for %s, updating",
                               credential.username, platform)
                self._accounts[platform].remove(existing)
                break

        self._accounts[platform].append(credential)
        self.save(platform)
        logger.info("Added account %s for %s", credential.username, platform)

    def remove_account(self, platform: str, username: str) -> bool:
        """Remove an account by platform and username."""
        if platform not in self._accounts:
            return False
        for acc in self._accounts[platform]:
            if acc.username == username:
                self._accounts[platform].remove(acc)
                self.save(platform)
                return True
        return False

    def get_account(self, platform: str, identity_id: str | None = None) -> AccountCredential | None:
        """Get an available account for a platform.

        If identity_id is provided, returns the account assigned to that identity.
        Otherwise returns the first enabled unassigned account.
        """
        if not self._loaded:
            self.load()

        accounts = self._accounts.get(platform, [])
        if not accounts:
            return None

        # Try to find identity-specific account first
        if identity_id:
            for acc in accounts:
                if acc.identity_id == identity_id and acc.enabled:
                    return acc

        # Fall back to unassigned enabled accounts
        for acc in accounts:
            if acc.identity_id is None and acc.enabled:
                return acc

        # Fall back to any enabled account
        for acc in accounts:
            if acc.enabled:
                return acc

        return None

    def assign_account(self, platform: str, username: str, identity_id: str) -> bool:
        """Assign an account to a specific identity."""
        accounts = self._accounts.get(platform, [])
        for acc in accounts:
            if acc.username == username:
                acc.identity_id = identity_id
                self.save(platform)
                return True
        return False

    def list_accounts(self, platform: str | None = None) -> list[AccountCredential]:
        """List all accounts, optionally filtered by platform."""
        if not self._loaded:
            self.load()

        if platform:
            return self._accounts.get(platform, [])

        all_accounts: list[AccountCredential] = []
        for accs in self._accounts.values():
            all_accounts.extend(accs)
        return all_accounts

    def get_platforms_with_accounts(self) -> list[str]:
        """Return list of platforms that have at least one enabled account."""
        if not self._loaded:
            self.load()
        return [p for p, accs in self._accounts.items() if any(a.enabled for a in accs)]

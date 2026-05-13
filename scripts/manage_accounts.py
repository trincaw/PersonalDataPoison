#!/usr/bin/env python3
"""CLI tool for managing platform accounts.

Usage:
    python scripts/manage_accounts.py add --platform google --username user@gmail.com --password "..."
    python scripts/manage_accounts.py add --platform instagram --username myuser --password "..." --email user@mail.com
    python scripts/manage_accounts.py list
    python scripts/manage_accounts.py list --platform google
    python scripts/manage_accounts.py remove --platform google --username user@gmail.com
    python scripts/manage_accounts.py assign --platform google --username user@gmail.com --identity id-abc123
    python scripts/manage_accounts.py test --platform google --username user@gmail.com

Environment:
    PDP_ACCOUNTS_PASSPHRASE: Passphrase to encrypt/decrypt account storage
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from accounts.store import AccountStore, AccountCredential


def ensure_passphrase() -> None:
    """Ensure passphrase is set in environment."""
    if not os.environ.get("PDP_ACCOUNTS_PASSPHRASE"):
        passphrase = getpass.getpass("Enter accounts passphrase: ")
        os.environ["PDP_ACCOUNTS_PASSPHRASE"] = passphrase


def cmd_add(args: argparse.Namespace) -> None:
    """Add a new account."""
    ensure_passphrase()
    store = AccountStore(args.accounts_dir)
    store.load()

    password = args.password
    if not password:
        password = getpass.getpass(f"Password for {args.username}@{args.platform}: ")

    credential = AccountCredential(
        platform=args.platform,
        username=args.username,
        password=password,
        email=args.email or "",
        phone=args.phone or "",
        tags=args.tags.split(",") if args.tags else [],
    )
    store.add_account(credential)
    print(f"✓ Added account: {args.username} → {args.platform}")


def cmd_list(args: argparse.Namespace) -> None:
    """List accounts."""
    ensure_passphrase()
    store = AccountStore(args.accounts_dir)
    store.load()

    accounts = store.list_accounts(args.platform)
    if not accounts:
        print("No accounts found.")
        return

    print(f"{'Platform':<12} {'Username':<30} {'Email':<30} {'Identity':<15} {'Enabled':<8} {'Tags'}")
    print("-" * 110)
    for acc in accounts:
        print(f"{acc.platform:<12} {acc.username:<30} {acc.email:<30} "
              f"{acc.identity_id or '-':<15} {'✓' if acc.enabled else '✗':<8} "
              f"{','.join(acc.tags)}")


def cmd_remove(args: argparse.Namespace) -> None:
    """Remove an account."""
    ensure_passphrase()
    store = AccountStore(args.accounts_dir)
    store.load()

    if store.remove_account(args.platform, args.username):
        print(f"✓ Removed: {args.username} from {args.platform}")
    else:
        print(f"✗ Account not found: {args.username}@{args.platform}")
        sys.exit(1)


def cmd_assign(args: argparse.Namespace) -> None:
    """Assign account to an identity."""
    ensure_passphrase()
    store = AccountStore(args.accounts_dir)
    store.load()

    if store.assign_account(args.platform, args.username, args.identity):
        print(f"✓ Assigned {args.username}@{args.platform} → identity {args.identity}")
    else:
        print(f"✗ Account not found: {args.username}@{args.platform}")
        sys.exit(1)


def cmd_test(args: argparse.Namespace) -> None:
    """Test login for an account (opens browser)."""
    ensure_passphrase()
    store = AccountStore(args.accounts_dir)
    store.load()

    credential = store.get_account(args.platform)
    if args.username:
        accounts = store.list_accounts(args.platform)
        credential = next((a for a in accounts if a.username == args.username), None)

    if not credential:
        print(f"✗ No account found for {args.platform}")
        sys.exit(1)

    print(f"Testing login: {credential.username} → {credential.platform}")
    print("(Browser will open in non-headless mode)")

    asyncio.run(_test_login(credential))


async def _test_login(credential: AccountCredential) -> None:
    from playwright.async_api import async_playwright
    from accounts.login import PlatformLogin, save_session_after_login

    login_handler = PlatformLogin()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        result = await login_handler.login(page, credential)

        if result.success:
            print(f"✓ Login successful: {credential.username}@{credential.platform}")

            # Optionally save session
            save = input("Save session for reuse? [y/N]: ").strip().lower()
            if save == "y":
                identity_id = credential.identity_id or "test"
                path = await save_session_after_login(context, identity_id, credential.platform)
                print(f"  Session saved to: {path}")
        else:
            print(f"✗ Login failed: {result.error}")

        input("Press Enter to close browser...")
        await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="manage_accounts",
        description="Manage encrypted platform accounts for PDP",
    )
    parser.add_argument(
        "--accounts-dir",
        default="data/accounts",
        help="Path to encrypted accounts storage (default: data/accounts)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_p = subparsers.add_parser("add", help="Add a new account")
    add_p.add_argument("--platform", required=True,
                       choices=["google", "youtube", "instagram", "facebook",
                                "tiktok", "linkedin", "twitter", "amazon"])
    add_p.add_argument("--username", required=True)
    add_p.add_argument("--password", default=None, help="Password (prompted if omitted)")
    add_p.add_argument("--email", default=None)
    add_p.add_argument("--phone", default=None)
    add_p.add_argument("--tags", default=None, help="Comma-separated tags")

    # list
    list_p = subparsers.add_parser("list", help="List accounts")
    list_p.add_argument("--platform", default=None)

    # remove
    rm_p = subparsers.add_parser("remove", help="Remove an account")
    rm_p.add_argument("--platform", required=True)
    rm_p.add_argument("--username", required=True)

    # assign
    assign_p = subparsers.add_parser("assign", help="Assign account to identity")
    assign_p.add_argument("--platform", required=True)
    assign_p.add_argument("--username", required=True)
    assign_p.add_argument("--identity", required=True)

    # test
    test_p = subparsers.add_parser("test", help="Test login (opens browser)")
    test_p.add_argument("--platform", required=True)
    test_p.add_argument("--username", default=None)

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "list": cmd_list,
        "remove": cmd_remove,
        "assign": cmd_assign,
        "test": cmd_test,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()

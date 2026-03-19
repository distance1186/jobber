#!/usr/bin/env python3
"""Extract LinkedIn li_at cookie from your browser and save it to .env.

Supports automatic extraction from Firefox (all platforms).
Falls back to an interactive prompt for Chrome/Edge users.

Usage:
    python scripts/get-linkedin-cookie.py [--env /path/to/.env]
"""

import argparse
import glob
import os
import platform
import shutil
import sqlite3
import sys
import tempfile


def find_firefox_cookie_dbs():
    """Find all Firefox cookies.sqlite files across profiles."""
    system = platform.system()

    if system == "Linux":
        pattern = os.path.expanduser("~/.mozilla/firefox/*/cookies.sqlite")
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        pattern = os.path.join(
            appdata, "Mozilla", "Firefox", "Profiles", "*", "cookies.sqlite"
        )
    elif system == "Darwin":
        pattern = os.path.expanduser(
            "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite"
        )
    else:
        return []

    return sorted(glob.glob(pattern))


def extract_li_at_from_firefox():
    """Extract li_at cookie value from Firefox cookie store."""
    db_paths = find_firefox_cookie_dbs()

    if not db_paths:
        return None

    for db_path in db_paths:
        # Copy DB to temp file — Firefox may hold a lock on it
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(tmp_fd)

        try:
            shutil.copy2(db_path, tmp_path)
            conn = sqlite3.connect(tmp_path)
            cursor = conn.execute(
                "SELECT value FROM moz_cookies "
                "WHERE name = 'li_at' AND host = '.linkedin.com' "
                "ORDER BY expiry DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                return row[0]
        except sqlite3.Error:
            continue
        finally:
            os.unlink(tmp_path)

    return None


def update_env_file(env_path, cookie_value):
    """Update or add LI_AT_COOKIE in the .env file."""
    if not os.path.exists(env_path):
        print(f"  Error: {env_path} does not exist.")
        return False

    with open(env_path, "r") as f:
        lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith("LI_AT_COOKIE="):
            lines[i] = f"LI_AT_COOKIE={cookie_value}\n"
            found = True
            break

    if not found:
        lines.append(f"\nLI_AT_COOKIE={cookie_value}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

    return True


def manual_instructions():
    """Print manual cookie extraction steps."""
    print()
    print("  To get your LinkedIn cookie manually:")
    print("  1. Open https://www.linkedin.com in your browser and log in")
    print("  2. Press F12 to open Developer Tools")
    print("  3. Go to the Application tab (Chrome/Edge) or Storage tab (Firefox)")
    print("  4. Click Cookies → https://www.linkedin.com")
    print('  5. Find the cookie named "li_at" and copy its Value')
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Extract LinkedIn li_at cookie and save to .env"
    )
    parser.add_argument(
        "--env",
        default=None,
        help="Path to .env file (default: auto-detect in project root)",
    )
    args = parser.parse_args()

    # Find .env file
    if args.env:
        env_path = os.path.abspath(args.env)
    else:
        # Walk up from script location to find .env
        search = os.path.dirname(os.path.abspath(__file__))
        env_path = None
        for _ in range(3):
            candidate = os.path.join(search, ".env")
            if os.path.exists(candidate):
                env_path = candidate
                break
            search = os.path.dirname(search)

        if not env_path:
            print("Could not find .env file. Use --env to specify the path.")
            sys.exit(1)

    print("=" * 50)
    print("  Jobber — LinkedIn Cookie Setup")
    print("=" * 50)
    print()

    # Try automatic extraction from Firefox
    print("  Checking Firefox for LinkedIn cookie...")
    cookie = extract_li_at_from_firefox()

    if cookie:
        preview = cookie[:12] + "..." + cookie[-6:]
        print(f"  ✓ Found li_at cookie from Firefox ({len(cookie)} chars)")
        print(f"    Preview: {preview}")
        print()

        confirm = input("  Save this cookie to .env? [Y/n] ").strip().lower()
        if confirm in ("", "y", "yes"):
            pass  # proceed to save
        else:
            print("  Skipped.")
            return
    else:
        print("  ✗ Could not find cookie automatically.")
        print("    (Firefox with an active LinkedIn session is required for auto-detect)")
        manual_instructions()

        cookie = input("  Paste your li_at cookie value: ").strip()

        if not cookie:
            print("  No cookie provided. Exiting.")
            sys.exit(1)

    # Validate cookie looks reasonable
    if len(cookie) < 50:
        print(f"  Warning: Cookie seems short ({len(cookie)} chars). Are you sure?")
        confirm = input("  Continue anyway? [y/N] ").strip().lower()
        if confirm not in ("y", "yes"):
            sys.exit(1)

    # Save to .env
    if update_env_file(env_path, cookie):
        print()
        print(f"  ✓ Saved to {env_path}")
        print()
        print("  Next: restart the agent to pick up the new cookie:")
        print("    docker compose up -d agent")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

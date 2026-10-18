"""CLI management tool for creating and updating admin user accounts in Truth Mirror."""

import argparse
import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from truth_mirror.db import get_db
from truth_mirror.auth_service import create_or_update_admin


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Truth Mirror CLI Account & Admin Management Utility"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-admin
    create_parser = subparsers.add_parser(
        "create-admin", help="Create a new verified admin user account"
    )
    create_parser.add_argument("--email", required=True, help="Admin user email")
    create_parser.add_argument("--password", required=True, help="Admin user password")
    create_parser.add_argument(
        "--db-path",
        default=os.environ.get("AUTH_DB_PATH", "truth_mirror.db"),
        help="Path to SQLite database file",
    )

    # reset-password
    reset_parser = subparsers.add_parser(
        "reset-password", help="Reset password for an existing account"
    )
    reset_parser.add_argument("--email", required=True, help="User email")
    reset_parser.add_argument("--password", required=True, help="New password")
    reset_parser.add_argument(
        "--db-path",
        default=os.environ.get("AUTH_DB_PATH", "truth_mirror.db"),
        help="Path to SQLite database file",
    )

    args = parser.parse_args()

    conn = get_db(args.db_path)
    try:
        result = create_or_update_admin(conn, args.email, args.password)
        if result.get("success"):
            print(f"[SUCCESS] {result.get('message')}")
            return 0
        else:
            print(f"[ERROR] {result.get('error')}", file=sys.stderr)
            return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

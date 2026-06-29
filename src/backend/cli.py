"""Management CLI — run from src/backend/: uv run python cli.py <command>"""
import argparse
import sys

from core.database import SessionLocal
from core.security import hash_password
from models.user import User


def cmd_create_user(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == args.email).first():
            print(f"Error: {args.email} already exists", file=sys.stderr)
            sys.exit(1)
        user = User(
            email=args.email,
            display_name=args.name,
            password_hash=hash_password(args.password),
        )
        db.add(user)
        db.commit()
        print(f"Created user: {args.name} <{args.email}>")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Finance App management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-user", help="Create a new user account")
    p.add_argument("--email", required=True, help="Login email address")
    p.add_argument("--name", required=True, help="Display name shown in the app")
    p.add_argument("--password", required=True, help="Initial password (user can change in-app)")

    args = parser.parse_args()
    if args.command == "create-user":
        cmd_create_user(args)


if __name__ == "__main__":
    main()

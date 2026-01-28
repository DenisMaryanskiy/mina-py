import argparse
import os

from app.core.config import get_settings


def main():
    parser = argparse.ArgumentParser(description="MINA command line interface")
    parser.add_argument(
        "--env",
        type=str,
        default="dev",
        choices=["dev", "prod"],
        help="Set the environment (default: dev)",
    )
    args = parser.parse_args()

    os.environ["ENVIRONMENT"] = args.env

    settings = get_settings()
    print(settings.ENVIRONMENT)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TransferSpeedColumn

# Initialize Rich console
console = Console()


def is_root() -> bool:
    """Check if the script is running with root privileges."""
    return os.geteuid() == 0


def run_with_sudo() -> None:
    """Re-run the script with sudo privileges."""
    if not is_root():
        console.print("[yellow]Requesting sudo privileges...[/yellow]")
        try:
            # Get the absolute path of the current script
            script_path = os.path.abspath(sys.argv[0])
            # Re-run the script with sudo
            os.execvp("sudo", ["sudo", sys.executable, script_path] + sys.argv[1:])
        except Exception as e:
            console.print(f"[red]Failed to obtain sudo privileges: {str(e)}[/red]")
            sys.exit(1)


def get_home_dir() -> str:
    """Get the user's home directory."""
    return os.path.expanduser("~")


def load_environment() -> None:
    """Load environment variables from .env file if it exists."""
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv()
        console.print("[green]Loaded environment variables from .env file[/green]")
    else:
        console.print(
            "[yellow]No .env file found. Please create one with your AWS credentials.[/yellow]"
        )
        console.print("Required environment variables:")
        console.print("  AWS_ACCESS_KEY_ID")
        console.print("  AWS_SECRET_ACCESS_KEY")
        console.print("  AWS_DEFAULT_REGION")
        sys.exit(1)


def validate_aws_credentials() -> None:
    """Validate AWS credentials from environment variables."""
    required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        console.print(
            f"[red]Missing required AWS environment variables: {', '.join(missing_vars)}[/red]"
        )
        console.print(
            "[yellow]Please update your .env file with the required credentials.[/yellow]"
        )
        sys.exit(1)


def parse_s3_path(s3_path: str) -> Tuple[str, Optional[str]]:
    """Parse S3 path into bucket and prefix."""
    if not s3_path.startswith("s3://"):
        raise ValueError("S3 path must start with 's3://'")

    path = s3_path[5:]  # Remove 's3://'
    parts = path.split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else None

    return bucket, prefix


def get_file_size(s3_path: str) -> int:
    """Get the size of a file in S3 in bytes."""
    try:
        result = subprocess.run(
            ["aws", "s3", "ls", s3_path], capture_output=True, text=True, check=True
        )
        # Parse the size from the ls output
        parts = result.stdout.strip().split()
        if len(parts) >= 3:
            return int(parts[2])  # Size is the third column
        return 0
    except Exception:
        return 0


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def sync_s3_to_local(s3_path: str, local_path: str) -> None:
    """Sync S3 path to local directory with progress tracking using boto3."""
    try:
        # Create local directory if it doesn't exist
        os.makedirs(local_path, exist_ok=True)

        # Parse S3 path
        bucket, prefix = parse_s3_path(s3_path)

        # Initialize S3 client
        s3_client = boto3.client("s3")

        # List all objects in the S3 path
        console.print("[cyan]Listing objects in S3 path...[/cyan]")
        paginator = s3_client.get_paginator("list_objects_v2")

        # Use empty string instead of None for prefix
        list_kwargs = {"Bucket": bucket}
        if prefix is not None:
            list_kwargs["Prefix"] = prefix

        pages = paginator.paginate(**list_kwargs)

        # Get total size and count of objects
        total_size = 0
        total_objects = 0
        objects = []

        for page in pages:
            if "Contents" in page:
                for obj in page["Contents"]:
                    size = obj["Size"]
                    key = obj["Key"]
                    total_size += size
                    total_objects += 1
                    objects.append((key, size))

        if total_objects == 0:
            console.print("[yellow]No objects found in the specified S3 path.[/yellow]")
            return

        console.print(
            f"[cyan]Found {total_objects} objects to sync (total size: {format_size(total_size)})[/cyan]"
        )

        # Initialize progress tracking
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TransferSpeedColumn(),
            TextColumn("•"),
            TextColumn("[cyan]{task.fields[filename]}"),
            console=console,
        ) as progress:
            # Create a task for overall progress
            task = progress.add_task(
                "[cyan]Syncing files...", total=total_size, filename=""
            )

            # Download each object
            for key, size in objects:
                # Calculate local path for the object
                relative_path = key[len(prefix) :] if prefix else key
                local_file_path = os.path.join(local_path, relative_path)

                # Ensure the parent directory exists
                parent_dir = os.path.dirname(local_file_path)
                if parent_dir:
                    try:
                        # First, check if the parent directory exists and is a file
                        if os.path.exists(parent_dir) and not os.path.isdir(parent_dir):
                            # Create a unique backup path
                            backup_path = f"{parent_dir}.{os.urandom(4).hex()}.bak"
                            os.rename(parent_dir, backup_path)
                            console.print(
                                f"[yellow]Renamed conflicting file to {backup_path}[/yellow]"
                            )

                        # Now create the directory
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError as e:
                        console.print(
                            f"[red]Error creating directory {parent_dir}: {str(e)}[/red]"
                        )
                        continue

                # Update progress with current filename
                progress.update(task, filename=os.path.basename(key))

                # Download the object with progress tracking
                try:
                    s3_client.download_file(
                        bucket,
                        key,
                        local_file_path,
                        Callback=lambda bytes_transferred: progress.update(
                            task, advance=bytes_transferred
                        ),
                    )
                except Exception as e:
                    console.print(f"[red]Error downloading {key}: {str(e)}[/red]")
                    continue

            # Mark progress as complete
            progress.update(task, completed=total_size, filename="")

        console.print("[green]Sync completed successfully![/green]")

    except ClientError as e:
        console.print(f"[red]AWS Error: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


def main():
    # Request sudo privileges if not already running as root
    run_with_sudo()

    # Load environment variables
    load_environment()
    validate_aws_credentials()

    # Get S3 path and local path from command line arguments
    if len(sys.argv) != 3:
        console.print("[red]Usage: python3 s3_sync.py <s3_path> <local_path>[/red]")
        console.print(
            "Example: python3 s3_sync.py s3://my-bucket/path/to/files /local/path"
        )
        sys.exit(1)

    s3_path = sys.argv[1]
    local_path = sys.argv[2]

    try:
        # Validate S3 path format
        bucket, prefix = parse_s3_path(s3_path)

        # Display sync information
        console.print(
            Panel.fit(
                f"[bold]S3 Sync Details[/bold]\n"
                f"Bucket: [cyan]{bucket}[/cyan]\n"
                f"Prefix: [cyan]{prefix or 'root'}[/cyan]\n"
                f"Local Path: [cyan]{local_path}[/cyan]",
                title="Sync Configuration",
            )
        )

        # Start the sync process
        sync_s3_to_local(s3_path, local_path)

    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

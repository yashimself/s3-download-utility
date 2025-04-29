#!/usr/bin/env python3

import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

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


def get_os_type() -> str:
    """Get the operating system type."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        # Try to determine the Linux distribution
        try:
            with open("/etc/os-release") as f:
                content = f.read().lower()
                if "ubuntu" in content or "debian" in content:
                    return "ubuntu"
                elif "fedora" in content or "rhel" in content or "centos" in content:
                    return "fedora"
        except FileNotFoundError:
            pass
        return "linux"
    elif system == "windows":
        return "windows"
    return system


def install_aws_cli() -> None:
    """Install AWS CLI based on the operating system."""
    os_type = get_os_type()
    console.print(f"[yellow]Installing AWS CLI for {os_type}...[/yellow]")

    try:
        if os_type == "macos":
            # Install using Homebrew
            subprocess.run(["brew", "install", "awscli"], check=True)
        elif os_type == "ubuntu":
            # Install using apt
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", "awscli"], check=True)
        elif os_type == "fedora":
            # Install using dnf
            subprocess.run(["dnf", "install", "-y", "awscli"], check=True)
        elif os_type == "windows":
            # Download and install AWS CLI for Windows
            installer_url = "https://awscli.amazonaws.com/AWSCLIV2.msi"
            installer_path = "AWSCLIV2.msi"

            # Download the installer
            subprocess.run(["curl", "-o", installer_path, installer_url], check=True)

            # Install using msiexec
            subprocess.run(["msiexec", "/i", installer_path, "/quiet"], check=True)

            # Clean up
            os.remove(installer_path)

            # Add AWS CLI to PATH if not already there
            aws_path = os.path.expanduser(
                "~\\AppData\\Local\\Programs\\Amazon\\AWSCLIV2"
            )
            if aws_path not in os.environ["PATH"]:
                os.environ["PATH"] = aws_path + os.pathsep + os.environ["PATH"]
        else:
            # Generic Linux installation
            subprocess.run(
                [
                    "curl",
                    "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip",
                    "-o",
                    "awscliv2.zip",
                ],
                check=True,
            )
            subprocess.run(["unzip", "awscliv2.zip"], check=True)
            subprocess.run(["./aws/install"], check=True)
            os.remove("awscliv2.zip")
            shutil.rmtree("aws")

        console.print("[green]AWS CLI installed successfully![/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to install AWS CLI: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error installing AWS CLI: {str(e)}[/red]")
        sys.exit(1)


def check_aws_cli() -> bool:
    """Check if AWS CLI is installed."""
    return shutil.which("aws") is not None


def check_aws_credentials() -> bool:
    """Check if AWS credentials are properly configured."""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"], capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


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


def sync_s3_to_local(s3_path: str, local_path: str) -> None:
    """Sync S3 path to local directory with progress tracking."""
    try:
        # Create local directory if it doesn't exist
        os.makedirs(local_path, exist_ok=True)

        # Start the sync process
        process = subprocess.Popen(
            ["aws", "s3", "sync", s3_path, local_path, "--no-progress"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Initialize progress tracking
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Syncing...", total=100)

            while True:
                # Update progress (this is a simplified version - you might want to parse actual progress)
                progress.update(task, advance=1)

                # Check if process is still running
                if process.poll() is not None:
                    break

                time.sleep(0.1)

            # Ensure progress shows 100% at the end
            progress.update(task, completed=100)

        # Check for errors
        if process.returncode != 0:
            error = process.stderr.read()
            console.print(f"[red]Error during sync: {error}[/red]")
            sys.exit(1)

        console.print("[green]Sync completed successfully![/green]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


def main():
    # Request sudo privileges if not already running as root
    run_with_sudo()

    # Check for AWS CLI and install if needed
    if not check_aws_cli():
        console.print("[yellow]AWS CLI not found. Installing...[/yellow]")
        install_aws_cli()

    # Load environment variables
    load_environment()
    validate_aws_credentials()

    # Check AWS credentials
    if not check_aws_credentials():
        console.print("[red]AWS credentials are not properly configured[/red]")
        sys.exit(1)

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

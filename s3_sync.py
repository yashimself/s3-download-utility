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
from rich.progress import BarColumn, Progress, TextColumn

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


def get_home_dir() -> str:
    """Get the user's home directory."""
    return os.path.expanduser("~")


def check_and_install_unzip() -> None:
    """Check if unzip is installed and install it if not."""
    if shutil.which("unzip") is None:
        console.print("[yellow]unzip utility not found. Installing...[/yellow]")
        os_type = get_os_type()

        try:
            if os_type == "ubuntu":
                subprocess.run(
                    ["apt-get", "update"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                subprocess.run(
                    ["apt-get", "install", "-y", "unzip"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
            elif os_type == "fedora":
                subprocess.run(
                    ["dnf", "install", "-y", "unzip"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
            else:
                # Generic Linux installation
                try:
                    # Try apt first (Debian/Ubuntu)
                    subprocess.run(
                        ["apt-get", "update"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                    subprocess.run(
                        ["apt-get", "install", "-y", "unzip"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                except subprocess.CalledProcessError:
                    try:
                        # Try dnf (Fedora/RHEL)
                        subprocess.run(
                            ["dnf", "install", "-y", "unzip"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=True,
                        )
                    except subprocess.CalledProcessError:
                        try:
                            # Try yum (older RHEL/CentOS)
                            subprocess.run(
                                ["yum", "install", "-y", "unzip"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                check=True,
                            )
                        except subprocess.CalledProcessError:
                            console.print(
                                "[red]Failed to install unzip. Please install it manually.[/red]"
                            )
                            sys.exit(1)

            console.print("[green]unzip utility installed successfully![/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to install unzip: {str(e)}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error installing unzip: {str(e)}[/red]")
            sys.exit(1)


def install_aws_cli() -> None:
    """Install AWS CLI based on the operating system."""
    os_type = get_os_type()
    console.print(f"[yellow]Installing AWS CLI for {os_type}...[/yellow]")

    # Create a temporary directory in the user's home directory
    home_dir = get_home_dir()
    temp_dir = os.path.join(home_dir, ".aws-cli-temp")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        if os_type == "macos":
            # Install using the official pkg installer for macOS
            console.print("[cyan]Downloading AWS CLI installer for macOS...[/cyan]")
            installer_path = os.path.join(temp_dir, "AWSCLIV2.pkg")
            subprocess.run(
                [
                    "curl",
                    "https://awscli.amazonaws.com/AWSCLIV2.pkg",
                    "-o",
                    installer_path,
                    "-s",
                ],
                check=True,
            )

            console.print("[cyan]Installing AWS CLI...[/cyan]")
            subprocess.run(
                ["sudo", "installer", "-pkg", installer_path, "-target", "/"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

        elif os_type == "ubuntu" or os_type == "fedora" or os_type == "linux":
            # Install using the official method for Linux
            console.print("[cyan]Installing AWS CLI for Linux...[/cyan]")

            # Check and install unzip if needed
            check_and_install_unzip()

            # Download the installation file
            zip_path = os.path.join(temp_dir, "awscliv2.zip")
            subprocess.run(
                [
                    "curl",
                    "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip",
                    "-o",
                    zip_path,
                    "-s",
                ],
                check=True,
            )

            # Unzip the installer
            subprocess.run(["unzip", "-q", zip_path, "-d", temp_dir], check=True)

            # Run the install program
            subprocess.run(
                ["sudo", "./aws/install"],
                cwd=temp_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

        elif os_type == "windows":
            # Install using the official MSI installer for Windows
            console.print("[cyan]Downloading AWS CLI installer for Windows...[/cyan]")

            # Download the MSI installer
            installer_path = os.path.join(temp_dir, "AWSCLIV2.msi")
            subprocess.run(
                [
                    "curl",
                    "https://awscli.amazonaws.com/AWSCLIV2.msi",
                    "-o",
                    installer_path,
                    "-s",
                ],
                check=True,
            )

            # Run the MSI installer
            console.print("[cyan]Installing AWS CLI...[/cyan]")
            subprocess.run(
                ["msiexec", "/i", installer_path, "/quiet"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

        console.print("[green]AWS CLI installed successfully![/green]")

        # Verify installation
        try:
            result = subprocess.run(
                ["aws", "--version"], capture_output=True, text=True, check=True
            )
            console.print(f"[green]AWS CLI version: {result.stdout.strip()}[/green]")
        except subprocess.CalledProcessError:
            console.print(
                "[yellow]AWS CLI installed but version check failed. You may need to restart your terminal.[/yellow]"
            )

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to install AWS CLI: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error installing AWS CLI: {str(e)}[/red]")
        sys.exit(1)
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


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
    """Sync S3 path to local directory with progress tracking."""
    try:
        # Create local directory if it doesn't exist
        os.makedirs(local_path, exist_ok=True)

        # First, get the list of objects to sync
        console.print("[cyan]Listing objects in S3 path...[/cyan]")
        list_cmd = ["aws", "s3", "ls", s3_path, "--recursive"]
        result = subprocess.run(list_cmd, capture_output=True, text=True, check=True)

        # Parse the list of objects and their sizes
        objects = []
        total_size = 0
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                size = int(parts[2])
                name = " ".join(parts[3:])
                objects.append((name, size))
                total_size += size

        total_objects = len(objects)

        if total_objects == 0:
            console.print("[yellow]No objects found in the specified S3 path.[/yellow]")
            return

        console.print(
            f"[cyan]Found {total_objects} objects to sync (total size: {format_size(total_size)})[/cyan]"
        )

        # Initialize progress tracking with a simple progress bar
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            # Create a task with a total of 100 for percentage tracking
            task = progress.add_task("[cyan]Syncing files...", total=100)

            # Use aws s3 sync command
            sync_cmd = ["aws", "s3", "sync", s3_path, local_path, "--no-progress"]

            # Run the sync command
            process = subprocess.Popen(
                sync_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Monitor the sync process
            start_time = time.time()
            files_completed = 0

            while True:
                # Check if process has finished
                if process.poll() is not None:
                    break

                # Count completed files by checking local directory
                # This is an approximation since we can't get real-time progress from aws s3 sync
                local_files = 0
                for root, _, files in os.walk(local_path):
                    for file in files:
                        local_files += 1

                # Calculate progress based on completed files
                if total_objects > 0:
                    progress_value = min(95, int((local_files / total_objects) * 100))
                else:
                    progress_value = 0

                # Update progress
                progress.update(task, completed=progress_value)

                # Sleep briefly to avoid excessive CPU usage
                time.sleep(0.5)

            # Get the return code and any error output
            return_code = process.wait()
            _, stderr = process.communicate()

            # Check for errors
            if return_code != 0:
                console.print(f"[red]Error during sync: {stderr}[/red]")
                sys.exit(1)

            # Mark progress as complete
            progress.update(task, completed=100)

        # Calculate and display final statistics
        end_time = time.time()
        total_time = end_time - start_time

        console.print(
            f"[green]Sync completed successfully in {total_time:.2f} seconds![/green]"
        )

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error during sync: {e.stderr}[/red]")
        sys.exit(1)
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

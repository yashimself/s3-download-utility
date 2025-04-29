# S3 Download Utility

A command-line utility for syncing files from Amazon S3 buckets to local directories. The utility provides an interactive interface with progress tracking and automatic setup of required dependencies.

## Features

- Automatic AWS CLI installation based on operating system
- Secure authentication with AWS credentials
- Progress tracking for downloads with transfer speed and time remaining
- Support for syncing entire buckets or specific prefixes
- Automatic sudo privilege handling
- Cross-platform support (Windows, macOS, Linux)

## Prerequisites

- Python 3.x
- AWS credentials

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd s3-download-utility
```

2. Install required Python packages:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project directory with your AWS credentials:

```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=your_region
```

## Usage

Basic usage:

```bash
python3 s3_sync.py s3://bucket-name/path/to/files /local/path
```

Examples:

```bash
# Sync entire bucket
python3 s3_sync.py s3://my-bucket /local/path

# Sync specific prefix
python3 s3_sync.py s3://my-bucket/path/to/files /local/path

# Sync to current directory
python3 s3_sync.py s3://my-bucket/path/to/files .
```

## How It Works

1. The script checks for and requests sudo privileges if needed
2. Verifies AWS CLI installation and installs it if necessary
3. Loads AWS credentials from the .env file
4. Validates the S3 path and local directory
5. Displays sync configuration details
6. Performs the sync operation with progress tracking

## Supported Operating Systems

- **Windows**
- **macOS**
- **Ubuntu/Debian**
- **Fedora/RHEL/CentOS**


## Development

### Setup Development Environment

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

2. Install development dependencies:

```bash
pip install -r requirements.txt
```

## Troubleshooting

### Common Issues

1. **AWS CLI Installation Fails**

   - Ensure you have internet connectivity
   - Check if you have sufficient permissions
   - Try installing AWS CLI manually

2. **Authentication Errors**

   - Verify your AWS credentials in the .env file
   - Ensure the credentials have appropriate S3 permissions
   - Check if the AWS region is correct

3. **Permission Denied**
   - The script requires sudo privileges for installation
   - Ensure you have write permissions for the local directory

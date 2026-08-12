import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import time
import argparse

def ping_server():
    try:
        url = "http://127.0.0.1:5005/ping"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get("status") == "ok"
    except Exception:
        return False

def start_server():
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excel_server.py")
    print("Excel Persistent Server is not running. Hot-starting in background...")
    
    # Start the server as a detached background process
    if os.name == 'posix':
        subprocess.Popen(
            [sys.executable, server_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    else:
        subprocess.Popen(
            [sys.executable, server_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
    # Poll until server starts (max 3 seconds)
    for _ in range(30):
        time.sleep(0.1)
        if ping_server():
            print("Server successfully started and ready!")
            return True
            
    print("Error: Failed to start Excel Persistent Server within 3 seconds.")
    return False

def main():
    parser = argparse.ArgumentParser(description="Excel Persistent Client (Fast Converter)")
    parser.add_argument("image_path", nargs="?", help="Path to the screenshot image file")
    parser.add_argument("--target-xlsx", help="Target Excel file to update/create")
    parser.add_argument("--sheet-name", help="Specific sheet name to create/update")
    parser.add_argument("--append-rows", action="store_true", help="Append extracted data as new rows to the existing sheet instead of overwriting")
    parser.add_argument("--shutdown", action="store_true", help="Shutdown the background server")
    
    args = parser.parse_args()
    
    if args.shutdown:
        if ping_server():
            try:
                url = "http://127.0.0.1:5005/shutdown"
                req = urllib.request.Request(url, method="POST")
                with urllib.request.urlopen(req) as resp:
                    print("Shutdown signal sent successfully.")
            except Exception as e:
                print(f"Error sending shutdown signal: {e}")
        else:
            print("Server is not running.")
        return

    if not args.image_path:
        parser.print_help()
        sys.exit(1)
        
    abs_img_path = os.path.abspath(args.image_path)
    if not os.path.exists(abs_img_path):
        print(f"Error: Image file not found at {abs_img_path}")
        sys.exit(1)
        
    abs_target_xlsx = os.path.abspath(args.target_xlsx) if args.target_xlsx else None
    
    # 1. Ensure server is running
    if not ping_server():
        if not start_server():
            sys.exit(1)
            
    # 2. Send conversion request
    payload = {
        "image_path": abs_img_path,
        "target_xlsx": abs_target_xlsx,
        "sheet_name": args.sheet_name,
        "append_rows": args.append_rows
    }
    
    t0 = time.time()
    try:
        url = "http://127.0.0.1:5005/convert"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            elapsed = time.time() - t0
            if data.get("status") == "success":
                print(f"SUCCESS! Conversion completed in {elapsed:.3f} seconds.")
            else:
                print(f"Error from server: {data.get('message')}")
                sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error communicating with server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

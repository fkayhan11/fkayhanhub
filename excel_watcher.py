import os
import time
import subprocess

WATCH_DIR = "/Users/furkanmacbook/Desktop/Excel"
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.heic', '.heif'}

def watch_folder():
    print(f"Excel Watcher started. Monitoring folder: {WATCH_DIR}")
    print("Drop any image in this folder to automatically convert it to a styled Excel sheet!")
    print("Press Ctrl+C to stop.")
    
    # Pre-populate processed files by looking at what xlsx files already exist
    processed = set()
    
    while True:
        try:
            # Re-scan folder
            files = os.listdir(WATCH_DIR)
            
            # Find all existing Excel files to know what is already processed
            xlsx_bases = {os.path.splitext(f)[0].replace("_Raporu", "") for f in files if f.endswith(".xlsx") and not f.startswith("~$")}
            
            for file in files:
                if file.startswith("temp_") or file.startswith("~$") or file.startswith("."):
                    continue
                
                name, ext = os.path.splitext(file)
                if ext.lower() in IMAGE_EXTENSIONS:
                    # If this image is named "Ornektablo.png" and "Ornektablo_Raporu.xlsx" exists, skip it
                    if name in xlsx_bases or f"{name}_Raporu" in xlsx_bases:
                        continue
                    
                    # Found a new unprocessed image!
                    image_path = os.path.join(WATCH_DIR, file)
                    print(f"\n[Watcher] New image detected: {file}")
                    
                    # Run the pipeline
                    script_path = os.path.join(WATCH_DIR, "auto_excel_dynamic.py")
                    print(f"[Watcher] Converting {file} using auto_excel_dynamic.py...")
                    
                    start_time = time.time()
                    res = subprocess.run(["python3", script_path, image_path], capture_output=True, text=True)
                    elapsed = time.time() - start_time
                    
                    if res.returncode == 0:
                        print(f"[Watcher] Success! Converted in {elapsed:.2f} seconds.")
                    else:
                        print(f"[Watcher] Error processing {file}:")
                        print(res.stderr)
            
            time.sleep(1.0) # check folder every 1 second
            
        except KeyboardInterrupt:
            print("\nExcel Watcher stopped.")
            break
        except Exception as e:
            print(f"Error in watcher loop: {e}")
            time.sleep(5.0)

if __name__ == "__main__":
    watch_folder()

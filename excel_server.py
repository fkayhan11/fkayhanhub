import os
import sys
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import mimetypes
import traceback

from auto_excel_dynamic import process_image
from yorum_rag_handler import handle_reply_request
from md_converter_handler import handle_md_conversion

# Optional OpenAI for Yorum RAG
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

class ExcelServerHandler(BaseHTTPRequestHandler):
    # Quiet server logging to save terminal output and CPU
    def log_message(self, format, *args):
        pass

    def end_headers_with_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-type')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers_with_cors()

    def do_GET(self):
        if self.path.startswith("/download/"):
            import urllib.parse
            # e.g., /download/my_report.xlsx
            filename = urllib.parse.unquote(self.path[len("/download/"):])
            # Ensure it only downloads xlsx from current dir
            if not filename.endswith(".xlsx") or "/" in filename:
                self.send_response(403)
                self.end_headers_with_cors()
                return
                
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            if not os.path.exists(filepath):
                self.send_response(404)
                self.end_headers_with_cors()
                return
                
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers_with_cors()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers_with_cors()
                
        elif self.path == "/qr" or self.path == "/qr/":
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrgenerator", "dist", "index.html")
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers_with_cors()
                self.wfile.write(content)
            except Exception:
                self.send_response(404)
                self.end_headers_with_cors()
                
        elif self.path.startswith("/assets/") or self.path == "/vite.svg":
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrgenerator", "dist", self.path.lstrip("/"))
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    mime_type, _ = mimetypes.guess_type(filepath)
                    self.send_header('Content-Type', mime_type or 'application/octet-stream')
                    self.end_headers_with_cors()
                    self.wfile.write(content)
                except Exception:
                    self.send_response(500)
                    self.end_headers_with_cors()
            else:
                self.send_response(404)
                self.end_headers_with_cors()
                
        else:
            self.send_response(404)
            self.end_headers_with_cors()

    def do_POST(self):
        if self.path == "/reply":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))
                
                # Delegate to the standalone Yorum RAG module
                response_data = handle_reply_request(payload)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers_with_cors()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers_with_cors()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode('utf-8'))
            return
            
        if self.path == "/convert-md":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))
                
                response_data = handle_md_conversion(payload)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers_with_cors()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers_with_cors()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode('utf-8'))
            return
            
        if self.path in ["/convert", "/convert_sync"]:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data.decode('utf-8'))
            
            image_path = params.get('image_path')
            image_base64 = params.get('image_base64')
            target_xlsx = params.get('target_xlsx')
            sheet_name = params.get('sheet_name')
            append_rows = params.get('append_rows', False)
            
            import tempfile
            import base64
            
            if image_base64:
                # User uploaded a file via browser
                try:
                    img_data = base64.b64decode(image_base64.split(",")[1] if "," in image_base64 else image_base64)
                    temp_img_fd, temp_img_path = tempfile.mkstemp(suffix=".png")
                    with os.fdopen(temp_img_fd, 'wb') as f:
                        f.write(img_data)
                    image_path = temp_img_path
                except Exception as e:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers_with_cors()
                    self.wfile.write(json.dumps({"status": "error", "message": f"Invalid base64 image: {str(e)}"}).encode('utf-8'))
                    return
            
            if not image_path:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers_with_cors()
                self.wfile.write(json.dumps({"status": "error", "message": "Missing image_path or image_base64"}).encode('utf-8'))
                return
                
            try:
                # 1. Dual OCR Pre-processing for resident daemon
                from PIL import Image, ImageEnhance
                img = Image.open(image_path)
                img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
                unenhanced_path = os.path.join(os.path.dirname(image_path), "temp_unenhanced_daemon.png")
                img.save(unenhanced_path)
                
                img_enh = img.convert('L')
                img_enh = ImageEnhance.Contrast(img_enh).enhance(1.5)
                enhanced_path = os.path.join(os.path.dirname(image_path), "temp_enhanced_daemon.png")
                img_enh.save(enhanced_path)
                
                def query_daemon(path):
                    self.server.ocr_process.stdin.write(path + "\n")
                    self.server.ocr_process.stdin.flush()
                    lines = []
                    while True:
                        line = self.server.ocr_process.stdout.readline().strip()
                        if line == "---END-OF-JSON---" or not line: break
                        lines.append(line)
                    ocr_json_str = "".join(lines)
                    if ocr_json_str.startswith("Error:"): raise Exception(ocr_json_str)
                    return json.loads(ocr_json_str)
                    
                raw1 = query_daemon(unenhanced_path)
                raw2 = query_daemon(enhanced_path)
                
                for e_item in raw2:
                    exists = False
                    for r_item in raw1:
                        if abs(e_item['x'] - r_item['x']) < 0.03 and abs(e_item['y'] - r_item['y']) < 0.03:
                            exists = True
                            break
                    if not exists:
                        raw1.append(e_item)
                
                raw_ocr_data = raw1
                
                if os.path.exists(unenhanced_path): os.remove(unenhanced_path)
                if os.path.exists(enhanced_path): os.remove(enhanced_path)
                
                # 4. Call the Python Excel creator
                if self.path == "/convert":
                    # Async mode
                    import threading
                    threading.Thread(target=process_image, kwargs={
                        'image_path': image_path,
                        'target_xlsx': target_xlsx,
                        'sheet_name': sheet_name,
                        'append_rows': append_rows
                    }).start()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers_with_cors()
                    self.wfile.write(json.dumps({"status": "success", "message": "Excel created asynchronously"}).encode('utf-8'))
                
                elif self.path == "/convert_sync":
                    # Sync mode
                    process_image(
                        image_path=image_path,
                        target_xlsx=target_xlsx,
                        sheet_name=sheet_name,
                        append_rows=append_rows
                    )
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers_with_cors()
                    self.wfile.write(json.dumps({"status": "success", "message": "Excel created successfully", "file_path": target_xlsx}).encode('utf-8'))
                
            except Exception as e:
                # If we haven't sent headers yet, send 500 error
                try:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers_with_cors()
                    self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
                except Exception:
                    print(f"Error during async processing: {e}")
                    
                if image_base64 and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except: pass
                
        elif self.path == "/ping":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers_with_cors()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            
        elif self.path == "/shutdown":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers_with_cors()
            self.wfile.write(json.dumps({"status": "shutting_down"}).encode('utf-8'))
            # Schedule shutdown
            self.server.should_shutdown = True
            
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server_address = ('127.0.0.1', 5005)
    
    # Start Swift OCR daemon
    ocr_bin = "/Users/furkanmacbook/Desktop/Excel/ocr"
    if not os.path.exists(ocr_bin):
        ocr_bin = "./ocr"
        
    print("Starting resident Swift OCR process...")
    ocr_process = subprocess.Popen(
        [ocr_bin, "--daemon"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )
    
    # Read initialization line
    init_line = ocr_process.stdout.readline().strip()
    print(f"Swift OCR process initialized: {init_line}")
    
    httpd = HTTPServer(server_address, ExcelServerHandler)
    httpd.ocr_process = ocr_process
    httpd.should_shutdown = False
    httpd.wb_cache = {}
    
    print("Excel Persistent Server running on http://127.0.0.1:5005")
    
    # Custom loop to handle shutdown smoothly
    while not httpd.should_shutdown:
        httpd.handle_request()
        
    print("Shutting down Excel Persistent Server...")
    ocr_process.stdin.write("EXIT\n")
    ocr_process.stdin.flush()
    ocr_process.terminate()
    ocr_process.wait()
    print("Server stopped.")

if __name__ == "__main__":
    run_server()

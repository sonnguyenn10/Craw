import http.server
import json
import base64
import os
import requests
from craw_with_comments import run_crawler

PORT = int(os.environ.get("PORT", 8000))

class AdminHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    
    def do_POST(self):
        if self.path == '/api/crawl':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                base_url = data.get('base', 'https://fuoverflow.com')
                thread_url = data.get('thread', '')
                xf_user = data.get('xf_user', '')
                xf_session = data.get('xf_session', '')
                
                if not thread_url or not xf_user or not xf_session:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = {"status": "error", "message": "Vui lòng nhập đầy đủ Link Thread và Cookies (xf_user, xf_session)!"}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    return
                    
                # Chuẩn hóa thread_url nếu user nhập full link
                if thread_url.startswith('http'):
                    from urllib.parse import urlparse
                    parsed = urlparse(thread_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    thread_url = parsed.path
                
                if not thread_url.startswith('/'):
                    thread_url = '/' + thread_url
                    
                print(f"\n[API] Bắt đầu Crawl từ giao diện Web: {thread_url}")
                result = run_crawler(base_url, thread_url, xf_user, xf_session)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf-8'))
                print("[API] Crawl hoàn tất!\n")
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"status": "error", "message": f"Server Lỗi: {str(e)}"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        
        elif self.path == '/api/gemini':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                api_key = data.get('api_key')
                model = data.get('model', 'gemini-2.0-flash') # Default to 2.0-flash
                image_path = data.get('image_path')
                course_json_path = data.get('course_json_path')
                item_id = data.get('item_id')
                prompt = data.get('prompt', 'Hãy phân tích hình ảnh này, tìm ra đáp án đúng cho câu hỏi trắc nghiệm và giải thích chi tiết tại sao các đáp án khác sai. Trả lời bằng tiếng Việt, giải thích rõ ngữ cảnh. Định dạng Markdown.')
                
                if not api_key or not image_path:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Thiếu API Key hoặc đường dẫn ảnh!"}).encode('utf-8'))
                    return
                
                if not os.path.exists(image_path):
                    raise Exception(f"Không tìm thấy file ảnh tại: {image_path}")
                
                print(f"[API Gemini] Gọi model {model} phân tích ảnh {image_path}...")
                with open(image_path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                    
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                
                ext = image_path.split('.')[-1].lower()
                mime_type = "image/webp" if ext == "webp" else "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
                
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": image_base64
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                         "temperature": 0.2
                    }
                }
                
                req = requests.post(url, json=payload)
                resp_data = req.json()
                
                if req.status_code != 200:
                    raise Exception(resp_data.get("error", {}).get("message", "Lỗi từ API Google Gemini"))
                    
                answer_text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                
                # Lưu câu trả lời vào data.json nếu được yêu cầu
                if course_json_path and os.path.exists(course_json_path) and item_id is not None:
                    try:
                        with open(course_json_path, 'r', encoding='utf-8') as f:
                            course_data = json.load(f)
                        
                        # Tìm item hiện tại để chèn câu trả lời của gemini vào
                        for item in course_data:
                            if str(item.get("id")) == str(item_id):
                                item["gemini_answer"] = answer_text
                                break
                                
                        with open(course_json_path, 'w', encoding='utf-8') as f:
                            json.dump(course_data, f, ensure_ascii=False, indent=4)
                        print("[API Gemini] Đã lưu đáp án vào data.json")
                    except Exception as json_err:
                        print(f"Lỗi khi lưu data.json: {json_err}")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "answer": answer_text}).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))

        elif self.path == '/api/move_thread':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                subject = data.get('subject')
                category = data.get('category')
                thread = data.get('thread')
                new_subject = data.get('new_subject')
                new_category = data.get('new_category')
                
                if not all([subject, category, thread, new_subject, new_category]):
                    raise Exception("Vui lòng cung cấp đủ thông tin!")
                
                old_path = os.path.join("images", subject, category, thread)
                if not os.path.exists(old_path) and category == "other":
                    old_path = os.path.join("images", subject, thread)
                    
                new_category_path = os.path.join("images", new_subject, new_category)
                new_path = os.path.join(new_category_path, thread)
                
                if not os.path.exists(old_path):
                    raise Exception(f"Không tìm thấy thư mục: {old_path}")
                
                os.makedirs(new_category_path, exist_ok=True)
                
                import shutil
                shutil.move(old_path, new_path)
                
                from craw_with_comments import update_index_json
                update_index_json("images")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Đã di chuyển thành công"}).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

def main():
    server_address = ('', PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, AdminHTTPRequestHandler)
    print("====================================")
    print(f"🚀 ADMIN SERVER ĐANG CHẠY TẠI PORT {PORT}")
    print(f"👉 Link Hệ Thống Ôn Tập: http://localhost:{PORT}")
    print(f"👉 Link Bảng Điều Khiển: http://localhost:{PORT}/admin.html")
    print("Nhấn Ctrl + C để dừng Server")
    print("====================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("\nĐã dừng Server.")

if __name__ == '__main__':
    main()

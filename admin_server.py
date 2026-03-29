import http.server
import json
from craw_with_comments import run_crawler

PORT = 8000

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
        else:
            self.send_response(404)
            self.end_headers()

def main():
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, AdminHTTPRequestHandler)
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

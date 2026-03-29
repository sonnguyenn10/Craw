import json

def fix_app_js():
    with open('app.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Force bypass cache
    content = content.replace("fetch('./images/index.json');", "fetch('./images/index.json?t=' + new Date().getTime());")
    
    # Give better error alert
    content = content.replace("alert('Could not load index.json. Please make sure the crawler has run successfully.');", "alert('Lỗi khởi tạo: ' + error.message);")
    
    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(content)
fix_app_js()

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import time
import json
import re
import concurrent.futures

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_images_from_page(url, base_url, cookies):
    print(f"[{url}] Đang tải trang...")
    res = requests.get(url, cookies=cookies, headers=HEADERS)
    print(f"[{url}] Mã phản hồi: {res.status_code}")
    
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Check if Cloudflare blocked or Not logged in
    title = soup.title.string.strip() if soup.title else ""
    if "Just a moment" in title or "Cloudflare" in title:
        print("CẢNH BÁO: Bị Cloudflare chặn! Bot không thể vào trang.")
        
    login_link = soup.select_one("a[href*='/login/']")
    if login_link and "Đăng nhập" in login_link.text:
         print("CẢNH BÁO: Cookies xf_user/xf_session đã hết hạn hoặc không hợp lệ. Trang đang hiển thị dưới quyền Khách (Guest). Khách không thể xem ảnh đính kèm!")

    items = {}
    files = {}

    anchor_tags = soup.select("a.js-lbImage")
    for a in anchor_tags:
        href = a.get("href")
        if href and "/attachments/" in href:
            img_url = urljoin(base_url, href)
            media_href = a.get("data-lb-sidebar-href")
            media_url = None
            if media_href:
                media_url = urljoin(base_url, media_href.split("?")[0])
            items[img_url] = media_url

    imgs = soup.select("img.bbImage")
    for img in imgs:
        src = img.get("src") or img.get("data-src")
        if src and "/attachments/" in src:
            img_url = urljoin(base_url, src)
            if img_url not in items:
                items[img_url] = None

    all_anchors = soup.select("a")
    for a in all_anchors:
        href = a.get("href")
        if href and "/attachments/" in href and "js-lbImage" not in a.get("class", []):
            file_name = a.text.strip()
            if file_name:
                file_url = urljoin(base_url, href)
                if file_url not in items and file_url not in files:
                    files[file_url] = file_name

    return items, files, soup

def get_next_page(soup, base_url):
    next_btn = soup.select_one("a.pageNav-jump--next")
    if next_btn:
        return urljoin(base_url, next_btn.get("href"))
    return None

def update_index_json(images_dir="images"):
    # Cập nhật file file index.json nằm ở root mục images với cấu trúc Object JS chuẩn
    index_data = {}
    if os.path.exists(images_dir):
        for subject_code in os.listdir(images_dir):
            if subject_code in ["index.json", "index.json.bak"]: continue
            subject_path = os.path.join(images_dir, subject_code)
            if os.path.isdir(subject_path):
                index_data[subject_code] = {"pe": {}, "fe": {}, "other": {}}
                
                # Check top-level threads or categories
                for item in os.listdir(subject_path):
                    item_path = os.path.join(subject_path, item)
                    if os.path.isdir(item_path):
                        if item in ["pe", "fe", "other"]:
                            # It's a category folder
                            category = item
                            for thread in os.listdir(item_path):
                                thread_path = os.path.join(item_path, thread)
                                if os.path.isdir(thread_path):
                                    index_data[subject_code][category][thread] = {
                                        "title": thread,
                                        "path": f"images/{subject_code}/{category}/{thread}"
                                    }
                        else:
                            # It's an un-categorized thread folder, put it in 'other'
                            index_data[subject_code]["other"][item] = {
                                "title": item,
                                "path": f"images/{subject_code}/{item}"
                            }

                # Xoá category rỗng cho gọn
                for cat in ["pe", "fe", "other"]:
                    if not index_data[subject_code][cat]:
                        del index_data[subject_code][cat]
                        
                if not index_data[subject_code]:
                    del index_data[subject_code]
    
    with open(os.path.join(images_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=4)
    print(f"\n=> Đã cập nhật mục lục index.json cho Web!")


def run_crawler(base_url, thread_url, xf_user, xf_session):
    cookies = {
        "xf_user": xf_user,
        "xf_session": xf_session
    }

    all_images = {}
    all_files = {}
    url = base_url + thread_url

    print(f"=== BẮT ĐẦU CRAWL ===\nURL: {url}")

    while url:
        print("Crawling thread:", url)
        imgs, page_files, soup = get_images_from_page(url, base_url, cookies)
        all_images.update(imgs)
        all_files.update(page_files)
        url = get_next_page(soup, base_url)
        time.sleep(1)

    print("Total images found:", len(all_images))
    print("Total files found:", len(all_files))

    # Tự động trích xuất mã môn logic thư mục
    folder_name = thread_url.strip("/").split("/")[-1].lower() # pru212-sp-2025...
    subject_code = ""
    if "-" in folder_name:
        subject_code = folder_name.split("-")[0] # pru212
    else:
        subject_code = "unknown"
        
    save_path = os.path.join("images", subject_code, folder_name)
    os.makedirs(save_path, exist_ok=True)
    print(f"Thư mục lưu trữ: {save_path}")

    # Bắt đầu duyệt và lưu ảnh / xuất JSON

    def process_image_item(idx, img_link, img_media_url):
        try:
            img_name = f"img_{idx}.webp"
            img_path = os.path.join(save_path, img_name)
            
            # 1. Tải hình ảnh (Chỉ tải nếu chưa có file để tiết kiệm thời gian chạy lại)
            if not os.path.exists(img_path):
                img_res = requests.get(img_link, cookies=cookies, headers=HEADERS, stream=True)
                if img_res.status_code == 200:
                    with open(img_path, "wb") as f:
                        for chunk in img_res.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Downloaded {img_name}")
            else:
                pass # Đã có hình, không bắt tải lại

            # 2. Xử lý bình luận và đoán đáp án đúng
            ans_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0}
            comments_extracted = []
            
            if img_media_url:
                m_res = requests.get(img_media_url, cookies=cookies, headers=HEADERS)
                m_soup = BeautifulSoup(m_res.text, "html.parser")
                comments = m_soup.select(".comment-body")
                if not comments:
                     comments = m_soup.select("article.message-body")
                     
                answers_dict = {}
                for c in comments:
                    text = c.text.strip().replace('\n', ' ').replace('\t', '')
                    if text and "****" not in text and "Mua gói thành viên" not in text and "Đăng nhập" not in text:
                        text_lower = text.lower()
                        if text_lower not in answers_dict:
                            answers_dict[text_lower] = {"text": text, "count": 1}
                        else:
                            answers_dict[text_lower]["count"] += 1
                        
                        # Phân tích xem có phải đáp án kiểu A B C D không
                        match = re.search(r'\b([A-Fa-f])\b', text, re.IGNORECASE)
                        if match:
                            char = match.group(1).upper()
                            ans_counts[char] += 1
                        else:
                            # Nếu đứng kề đầu vòng ví dụ "A." hay "A:" 
                            match_start = re.match(r'^([A-Fa-f])[\.\:\)]', text, re.IGNORECASE)
                            if match_start:
                                char = match_start.group(1).upper()
                                ans_counts[char] += 1

                for data in answers_dict.values():
                    comments_extracted.append(data)
            
            # Chọn best_answer dựa trên số votes
            best_answer = None
            max_votes = 0
            for k, v in ans_counts.items():
                if v > max_votes:
                    max_votes = v
                    best_answer = k
            
            # Trả về object dữ liệu
            return {
                "id": idx,
                "image": img_name,
                "best_answer": best_answer,
                "comments": comments_extracted
            }
            
        except Exception as e:
            print(f"Lỗi ở ảnh {idx}: {e}")
            return None

    course_data = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i, (link, media_url) in enumerate(all_images.items()):
            futures.append(executor.submit(process_image_item, i, link, media_url))
            
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                course_data.append(res)
                
    # Sắp xếp lại course_data theo ID vĩ chạy đa luồng thứ tự có thể lộn xộn
    course_data.sort(key=lambda x: x["id"])

    # Ghi dữ liệu ra file data.json
    data_json_path = os.path.join(save_path, "data.json")
    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(course_data, f, ensure_ascii=False, indent=4)
        
    print(f"Đã xuất dữ liệu vào: {data_json_path}")
    
    # Bắt đầu duyệt và lưu các tệp đính kèm không phải hình ảnh
    files_data = []
    for link, file_name in all_files.items():
        try:
            file_path = os.path.join(save_path, file_name)
            if not os.path.exists(file_path):
                file_res = requests.get(link, cookies=cookies, headers=HEADERS, stream=True)
                if file_res.status_code == 200:
                    with open(file_path, "wb") as f:
                        for chunk in file_res.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Downloaded file {file_name}")
            
            files_data.append({
                "name": file_name,
                "url": file_name  # Relative path basically, same dir
            })
        except Exception as e:
            print(f"Lỗi khi tải file {file_name}: {e}")
            
    if files_data:
        files_json_path = os.path.join(save_path, "files.json")
        with open(files_json_path, "w", encoding="utf-8") as f:
            json.dump(files_data, f, ensure_ascii=False, indent=4)
        print(f"Đã xuất file list vào: {files_json_path}")

    # Cập nhật lại index.json
    update_index_json("images")
    return {"status": "success", "images": len(all_images), "files": len(all_files), "path": save_path}


if __name__ == "__main__":
    BASE = "https://fuoverflow.com"
    THREAD = "/threads/pru212-sp-2025-fe.3546/" 
    user = "18815%2C1jSN53yi1hklxS-FqMavn_4FEywJ24ftNcaq1msZ"
    session = "eODIQmlWxY5BVUPKtJtn6ohyxqDFAo1y"
    
    print("Testing crawler as script...")
    run_crawler(BASE, THREAD, user, session)

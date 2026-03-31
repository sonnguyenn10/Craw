import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import time
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_images_from_page(url, base_url, cookies):
    res = requests.get(url, cookies=cookies, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

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
            subject_path = os.path.join(images_dir, subject_code)
            if os.path.isdir(subject_path):
                threads = [d for d in os.listdir(subject_path) if os.path.isdir(os.path.join(subject_path, d))]
                if threads:
                    index_data[subject_code] = {}
                    for thread in threads:
                        index_data[subject_code][thread] = {
                            "title": thread,
                            "path": f"images/{subject_code}/{thread}"
                        }
    
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
    course_data = []

    for i, (link, media_url) in enumerate(all_images.items()):
        try:
            img_name = f"img_{i}.webp"
            img_path = os.path.join(save_path, img_name)
            
            # 1. Tải hình ảnh (Chỉ tải nếu chưa có file để tiết kiệm thời gian chạy lại)
            if not os.path.exists(img_path):
                img_res = requests.get(link, cookies=cookies, headers=HEADERS, stream=True)
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
            
            if media_url:
                m_res = requests.get(media_url, cookies=cookies, headers=HEADERS)
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
            
            # Lưu object vào course_data array
            item_data = {
                "id": i,
                "image": img_name,
                "best_answer": best_answer,
                "comments": comments_extracted
            }
            course_data.append(item_data)
            
        except Exception as e:
            print(f"Lỗi ở ảnh {i}: {e}")

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

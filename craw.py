import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import time
import concurrent.futures

BASE = "https://fuoverflow.com"
THREAD = "/threads/pru212-sp-2025-fe.3546/"

# 👉 dán cookie vào đây
cookies = {
    "xf_user": "54171%2CHS1zjWhaaWMNdXW_rariIO_zOqhBTlH3gimoyDCR",
    "xf_session": "EqBMmOiRm_6xhusp165twhiJWWRFr8G8"
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

def get_images_from_page(url):
    res = requests.get(url, cookies=cookies, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    links = []
    
    # Thẻ <a> chứa link ảnh chất lượng cao (ảnh đính kèm chưa hiện full)
    anchor_tags = soup.select("a.js-lbImage")
    for a in anchor_tags:
        href = a.get("href")
        if href and "/attachments/" in href:
            links.append(urljoin(BASE, href))
            
    # Mở rộng thêm lấy ảnh chèn trực tiếp trong bài (nếu có)
    imgs = soup.select("img.bbImage")
    for img in imgs:
        src = img.get("src") or img.get("data-src")
        if src and "/attachments/" in src:
            links.append(urljoin(BASE, src))

    return list(set(links)), soup


def get_next_page(soup):
    next_btn = soup.select_one("a.pageNav-jump--next")
    if next_btn:
        return urljoin(BASE, next_btn.get("href"))
    return None


all_images = set()
url = BASE + THREAD

while url:
    print("Crawling:", url)

    imgs, soup = get_images_from_page(url)
    all_images.update(imgs)

    url = get_next_page(soup)

    time.sleep(1)  # tránh bị block

print("Total images:", len(all_images))

# Lấy tên bài làm thư mục con (ví dụ: pru212-sp-2025-fe.3546)
folder_name = THREAD.strip("/").split("/")[-1]
save_path = os.path.join("images", folder_name)

os.makedirs(save_path, exist_ok=True)
print(f"Saving images to: {save_path}")

def download_image(i, link):
    try:
        img = requests.get(link, cookies=cookies).content
        with open(os.path.join(save_path, f"img_{i}.webp"), "wb") as f:
            f.write(img)
        print(f"Downloaded img_{i}.webp")
    except Exception as e:
        print(f"Failed to download {link}: {e}")

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(download_image, i, link) for i, link in enumerate(all_images)]
    concurrent.futures.wait(futures)

print("Done downloading!")
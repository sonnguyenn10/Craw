import json

def update_index_json():
    # Load old index.json
    try:
        with open('images/index.json', 'r', encoding='utf-8') as f:
            old_data = json.load(f)
    except FileNotFoundError:
        print("Không tìm thấy images/index.json")
        return
        
    new_data = {}
    for subject, threads in old_data.items():
        new_data[subject] = {}
        for thread in threads:
            # We assume title is similar to thread name for now
            new_data[subject][thread] = {
                "title": thread,
                "path": f"images/{subject}/{thread}"
            }
            
    with open('images/index.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
        
    print("Đã cập nhật images/index.json thành công!")
    
update_index_json()

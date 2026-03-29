import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'src="app.js(\?v=\d+)?"', r'src="app.js?v=2"', content)
content = re.sub(r'href="style.css(\?v=\d+)?"', r'href="style.css?v=2"', content)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

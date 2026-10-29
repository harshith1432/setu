import sys

files = ['admin_web/admin.html', 'admin_web/login.html']

firebase_snippet = """<!-- Firebase SDK & Cloud Firestore -->
<script src="https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.8.0/firebase-auth-compat.js"></script>
<script src="/firebase-db.js"></script>
"""

for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '/firebase-db.js' in content:
        print(f"Already updated: {path}")
        continue
    
    if '<script src="/admin/table-manager.js' in content:
        idx = content.find('<script src="/admin/table-manager.js')
        content = content[:idx] + firebase_snippet + content[idx:]
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Successfully injected Firebase scripts into {path}")
    else:
        print(f"Target tag not found in {path}")

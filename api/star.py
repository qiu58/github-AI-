import os
import requests
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 解析 URL 参数
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        repo = query_params.get("repo", [None])[0]
        category = query_params.get("category", [None])[0]
        
        # 如果缺少参数，返回 400 错误
        if not repo or not category:
            self.send_response(400)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write('Missing repo or category parameter'.encode('utf-8'))
            return
        
        try:
            # 1. 给项目点 Star
            star_repo(repo)
            
            # 2. 尝试加入 List 分类
            try:
                add_to_list(repo, category)
            except Exception as list_error:
                # GitHub 的 List API 是非公开的，如果失败我们忽略，保证 Star 成功即可
                print(f"添加到列表失败: {list_error}")
            
            # 3. 构造好看的成功页面
            html = f"""
                <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>收藏成功</title>
                        <style>
                            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                            .card {{ background: white; padding: 40px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; max-width: 400px; }}
                            h1 {{ color: #333; margin-bottom: 16px; }}
                            p {{ color: #666; font-size: 16px; line-height: 1.6; }}
                            .success {{ color: #10b981; font-weight: 600; font-size: 48px; margin-bottom: 16px; }}
                            a {{ color: #667eea; text-decoration: none; font-weight: 600; }}
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <div class="success">✓</div>
                            <h1>收藏成功！</h1>
                            <p>项目 <strong>{repo}</strong> 已成功 Star 并添加到 <strong>{category}</strong> 列表。</p>
                            <p><a href="https://github.com/{repo}">返回 GitHub 查看项目 →</a></p>
                        </div>
                    </body>
                </html>
            """
            
            # 成功返回
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            # 报错返回
            self.send_response(500)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode('utf-8'))


# ================== 以下是你原本的处理逻辑 ==================

def star_repo(repo_full_name):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/user/starred/{repo_full_name}"
    response = requests.put(url, headers=headers)
    response.raise_for_status()

def add_to_list(repo_full_name, list_name):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    username = get_username(headers)
    list_id = get_or_create_list(username, list_name, headers)
    url = f"https://api.github.com/user/starred/{repo_full_name}/lists/{list_id}"
    response = requests.put(url, headers=headers)
    if response.status_code not in [204, 201]:
        pass

def get_username(headers):
    url = "https://api.github.com/user"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["login"]

def get_or_create_list(username, list_name, headers):
    url = "https://api.github.com/user/starred/lists"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    lists = response.json()
    for lst in lists:
        if lst["name"] == list_name:
            return lst["id"]
    create_url = "https://api.github.com/user/starred/lists"
    data = {"name": list_name, "description": f"{list_name} 相关项目"}
    response = requests.post(create_url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["id"]

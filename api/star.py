import os
import requests
from http.server import BaseHTTPRequestHandler

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def handler(request):
    from urllib.parse import urlparse, parse_qs
    
    parsed_path = urlparse(request.url)
    query_params = parse_qs(parsed_path.query)
    
    repo = query_params.get("repo", [None])[0]
    category = query_params.get("category", [None])[0]
    
    if not repo or not category:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'text/html; charset=utf-8'},
            'body': 'Missing repo or category parameter'
        }
    
    try:
        star_repo(repo)
        add_to_list(repo, category)
        
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
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html; charset=utf-8'},
            'body': html
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/html; charset=utf-8'},
            'body': f"Error: {str(e)}"
        }

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

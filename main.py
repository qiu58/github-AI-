import os
import datetime
from github import Github
from openai import OpenAI
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# MY_VERCEL_URL 已经被下面直接写死了，不需要再去环境变量里找了，防止报错

g = Github(GITHUB_TOKEN)
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.aaai.vip/v1"
)

def search_repositories():
    keywords = [
        "RAG", "Agent", "LangChain", "LlamaIndex", 
        "Ollama", "vLLM", "LoRA", "Recommender System"
    ]
    since_date = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    since_str = since_date.strftime("%Y-%m-%d")
    
    all_repos = []
    for keyword in keywords:
        query = f"{keyword} created:>{since_str}"
        repos = g.search_repositories(query=query, sort="stars", order="desc")
        
        # 安全遍历：防止该关键词今天没有新项目导致崩溃
        try:
            count = 0
            for repo in repos:
                all_repos.append((repo, keyword))
                count += 1
                if count >= 15:  # 手动计数，达到 15 个就停止
                    break
        except Exception as e:
            print(f"⚠️ 搜索 [{keyword}] 时没有找到匹配数据或跳过...")
            continue
    
    seen = set()
    unique_repos = []
    for repo, keyword in all_repos:
        if repo.full_name not in seen:
            seen.add(repo.full_name)
            unique_repos.append((repo, keyword))
            if len(unique_repos) >= 15:
                break
        if len(unique_repos) >= 15:
            break
    
    return unique_repos

def get_readme_content(repo):
    try:
        readme = repo.get_readme()
        return readme.decoded_content.decode("utf-8")
    except:
        return ""

def analyze_repos_with_ai(repos_with_keywords):
    repos_info = []
    for repo, keyword in repos_with_keywords:
        readme_content = get_readme_content(repo)[:4000]
        repos_info.append({
            "name": repo.full_name,
            "stars": repo.stargazers_count,
            "description": repo.description or "",
            "readme": readme_content,
            "keyword": keyword,
            "url": repo.html_url
        })
    
    prompt = f"""我有以下 {len(repos_info)} 个 GitHub 项目，请根据技术硬核程度从中精选出 5 个最优秀的项目。

项目列表：
"""
    for i, repo in enumerate(repos_info, 1):
        prompt += f"{i}. 项目名: {repo['name']}\n"
        prompt += f"   Stars: {repo['stars']}\n"
        prompt += f"   描述: {repo['description']}\n"
        prompt += f"   关键词: {repo['keyword']}\n"
        prompt += f"   README: {repo['readme'][:1000]}\n\n"
    
    prompt += """请按以下 JSON 格式返回结果，所有的文本描述必须使用【中文】：
{
    "top_projects": [
        {
            "name": "项目原始英文名(必须保留，仅用于系统内部链接拼接)",
            "title_cn": "用中文高度概括：基于XX技术的XX项目（⚠️强制要求：必须以“基于”两个字开头，绝对不要包含“这是一个”等废话）",
            "stars": 星数,
            "research_problem": "研究问题（项目解决了行业或开发中的什么具体痛点？50字以内）",
            "core_approach": "核心思路（用什么创新的思路或算法来解决上述问题？50字以内）",
            "method_framework": "方法框架（使用了哪些关键技术组件、框架或架构？50字以内）",
            "url": "GitHub链接",
            "keyword": "RAG/Agent/LLM等简短标签"
        }
    ]
}
注意：务必严格按照此 JSON 结构输出，不要包含其他解释性文字。"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是一个专业的技术分析师与产品经理，擅长用极简、结构化的语言拆解复杂的开源项目。"},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    import json
    result = json.loads(response.choices[0].message.content)
    return result["top_projects"]

def generate_markdown(top_projects):
    today = datetime.datetime.now().strftime("%Y年%m月%d日")
    markdown = f"# 🚀 每日 AI 技术精选 - {today}\n\n"
    
    for i, project in enumerate(top_projects, 1):
        # 英文名 project['name'] 现在只在底层用于拼接这三个链接，前端不再显示
        zhihu_search = f"https://www.zhihu.com/search?q={project['name']}"
        xiaohongshu_search = f"https://www.xiaohongshu.com/search_result?keyword={project['name']}"
        star_link = f"https://github-ai-kappa.vercel.app/api/star?repo={project['name']}&category={project['keyword']}"
        
        # 极简纯中文排版
        markdown += f"## {i}. {project['title_cn']}\n\n"
        markdown += f"⭐ **Stars**: {project['stars']} | 🏷️ **标签**: {project['keyword']}\n\n"
        markdown += f"### 💡 硬核拆解\n"
        markdown += f"- **❓ 研究问题**: {project['research_problem']}\n"
        markdown += f"- **🧠 核心思路**: {project['core_approach']}\n"
        markdown += f"- **⚙️ 方法框架**: {project['method_framework']}\n\n"
        markdown += f"🔗 **开源地址**: [前往 GitHub 查看项目详情]({project['url']})\n\n"
        markdown += f"📚 **教程搜索**: [知乎]({zhihu_search})\n\n"
        markdown += f"⚡ **一键操作**: [❤️ 收藏至我的 AI 知识库]({star_link})\n\n"
        markdown += "---\n\n"
    
    return markdown

def push_to_wechat(content):
    # 获取 Server酱 的 Key
    SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY") 
    
    if not SERVERCHAN_KEY:
        print("❌ 未找到 Server酱 Key")
        return False
        
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
    data = {
        "title": "🚀 每日 AI 技术精选",
        "desp": content 
    }
    response = requests.post(url, data=data)
    return response.status_code == 200

def main():
    print("🔍 正在搜索 GitHub 仓库...")
    repos = search_repositories()
    print(f"✅ 找到 {len(repos)} 个候选项目")
    
    print("🤖 正在分析项目...")
    top_projects = analyze_repos_with_ai(repos)
    
    # === 新增：按星星数量倒序排列 ===
    # reverse=True 表示降序（从大到小）
    top_projects.sort(key=lambda x: x['stars'], reverse=True)
    
    print(f"✅ 精选出 {len(top_projects)} 个硬核项目（已按 Star 数排序）")
    
    print("📝 生成报告...")
    markdown = generate_markdown(top_projects)
    
    print("📤 推送到微信...")
    if push_to_wechat(markdown):
        print("✅ 微信推送成功！")
    else:
        print("❌ 推送失败")
    
    print("\n" + markdown)

if __name__ == "__main__":
    main()

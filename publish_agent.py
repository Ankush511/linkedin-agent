import os
import sys
import json
import requests
from github import Github, Auth
from datetime import datetime

HISTORY_FILE = "topic_history.json"

def post_to_linkedin(content):
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    payload = {
        "author": os.environ['LINKEDIN_USER_URN'],
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 201:
        raise Exception(f"LinkedIn Error: {resp.text}")
    return resp.json()['id']

def update_history_file(topic):
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    else:
        history = []
        
    history.append({"date": str(datetime.now().date()), "topic": topic})
    
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

if __name__ == "__main__":
    # 1. New Auth Method (Fixes the Deprecation Warning)
    auth = Auth.Token(os.environ["GITHUB_TOKEN"])
    g = Github(auth=auth)
    
    repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
    issue = repo.get_issue(int(os.environ["ISSUE_NUMBER"]))
    
    raw = issue.body
    topic = issue.title.replace("Draft: ", "")
    
    # 2. Smarter Parsing Logic
    try:
        if "" in raw:
            content = raw.split("")[1].split("")[0].strip()
        else:
            # Fallback: Just grab everything before the '---' line
            content = raw.split("---")[0].replace(f"### 🤖 Draft: {topic}", "").strip()
            
        if not content:
            raise ValueError("Parsed content is empty!")
            
    except Exception as e:
        issue.create_comment(f"❌ Error parsing issue body: {e}")
        sys.exit(1)
        
    print(f"🚀 Posting: {topic}")
    try:
        post_id = post_to_linkedin(content)
        update_history_file(topic)
        
        issue.create_comment(f"✅ Published! ID: {post_id}")
        issue.edit(state='closed')
        
    except Exception as e:
        issue.create_comment(f"❌ Failed: {e}")
        sys.exit(1)
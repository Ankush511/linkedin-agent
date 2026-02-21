import os
import json
import requests
import sys
from github import Github
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
    # Load existing
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    else:
        history = []
        
    # Append new
    history.append({"date": str(datetime.now().date()), "topic": topic})
    
    # Save
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

if __name__ == "__main__":
    # 1. Get Issue Details
    g = Github(os.environ["GITHUB_TOKEN"])
    repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
    issue = repo.get_issue(int(os.environ["ISSUE_NUMBER"]))
    
    # 2. Parse Content
    raw = issue.body
    try:
        # Extract text between markers
        content = raw.split("")[1].split("")[0].strip()
        topic = issue.title.replace("Draft: ", "")
    except:
        print("❌ Error parsing issue body!")
        sys.exit(1)
        
    # 3. Post to LinkedIn
    print(f"🚀 Posting: {topic}")
    try:
        post_id = post_to_linkedin(content)
        
        # 4. Update History File (Locally, will be committed by Actions)
        update_history_file(topic)
        
        # 5. Cleanup
        issue.create_comment(f"✅ Published! ID: {post_id}")
        issue.edit(state='closed')
        
    except Exception as e:
        issue.create_comment(f"❌ Failed: {e}")
        sys.exit(1)
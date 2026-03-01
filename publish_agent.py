import os
import sys
import json
import requests
from github import Github, Auth
from datetime import datetime

HISTORY_FILE = "topic_history.json"

def publish_to_hashnode(content):
    print("📝 Publishing to Hashnode...")
    headers = {
        "Authorization": os.environ['HASHNODE_TOKEN'],
        "Content-Type": "application/json"
    }
    
    lines = content.strip().split('\n')
    title = lines[0].replace("#", "").strip() if lines[0].startswith("#") else "Technical Deep Dive"
    body_content = '\n'.join(lines[1:]).strip()
    
    query = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post {
          url
        }
      }
    }
    """
    
    variables = {
        "input": {
            "title": title,
            "contentMarkdown": body_content,
            "publicationId": os.environ['HASHNODE_PUBLICATION_ID']
        }
    }
    
    payload = {
        "query": query,
        "variables": variables
    }
    
    response = requests.post("https://gql.hashnode.com/", headers=headers, json=payload)
    
    if response.status_code != 200:
        raise Exception(f"Hashnode API HTTP Error: {response.text}")
        
    result = response.json()
    if 'errors' in result:
        raise Exception(f"Hashnode GraphQL Error: {json.dumps(result['errors'])}")
        
    return result['data']['publishPost']['post']['url']

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
    auth = Auth.Token(os.environ["GITHUB_TOKEN"])
    g = Github(auth=auth)
    
    repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
    issue = repo.get_issue(int(os.environ["ISSUE_NUMBER"]))
    
    raw = issue.body or ""
    topic = issue.title.replace("Draft: ", "")
    
    try:
        hn_content = raw.split("---HASHNODE_ARTICLE---")[1].split("---LINKEDIN_POST---")[0].strip()
        li_content = raw.split("---LINKEDIN_POST---")[1].split("---END---")[0].strip()
            
        if not hn_content or not li_content:
            raise ValueError("Parsed content is empty! Make sure the markers are intact.")
            
        issue.create_comment("🚀 Pushing article to Hashnode...")
        hashnode_url = publish_to_hashnode(hn_content)
        
        promo_text = f"\n\n📖 To know more on this, check out my detailed blog: {hashnode_url}"
        final_li_content = li_content + promo_text
        
        print(f"🚀 Posting to LinkedIn: {topic}")
        issue.create_comment("🚀 Pushing summary to LinkedIn...")
        post_id = post_to_linkedin(final_li_content)
        
        update_history_file(topic)
        
        issue.create_comment(f"✅ Success!\nHashnode URL: {hashnode_url}\nLinkedIn ID: {post_id}")
        issue.edit(state='closed')
        
    except Exception as e:
        issue.create_comment(f"❌ Failed during publish sequence: {e}")
        sys.exit(1)
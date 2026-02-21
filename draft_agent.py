import os
import json
import boto3
import smtplib
from email.mime.text import MIMEText
from github import Github
from datetime import datetime
from botocore.exceptions import ClientError

# --- CONFIG ---
HISTORY_FILE = "topic_history.json"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
AWS_REGION = "us-east-1" 

# --- AWS SETUP ---
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=AWS_REGION,
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
)

def invoke_claude(prompt):
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    }
    try:
        response = bedrock.invoke_model(modelId=MODEL_ID, body=json.dumps(payload))
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except ClientError as e:
        print(f"AWS Error: {e}")
        raise

# --- LOGIC ---
def load_history():
    # In GitHub Actions, we read the file from the repo
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def get_unique_topic(history):
    past_topics = [h['topic'] for h in history]
    prompt = f"""
    Act as a Developer Advocate. Suggest a specialized topic for a LinkedIn post.
    Focus: Backend Engineering, System Design, or Generative AI.
    
    Constraints:
    1. NO generic advice (e.g. "Keep learning").
    2. MUST be technical (e.g. "Database Sharding vs Partitioning").
    3. DO NOT use these past topics: {past_topics}
    
    Output ONLY the topic title.
    """
    return invoke_claude(prompt).strip()

def generate_draft(topic):
    prompt = f"""
    Write a LinkedIn post about: "{topic}".
    Target Audience: Senior Software Engineers.
    
    Structure:
    - Hook: A technical challenge or common mistake.
    - Insight: The "How-To" or solution.
    - Engagement: A question for the comments.
    
    Format: Use bullet points and emojis. Length: < 1200 chars.
    """
    return invoke_claude(prompt)

def create_issue(topic, content):
    g = Github(os.environ["GITHUB_TOKEN"])
    repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
    
    body = f"""
### 🤖 Draft: {topic}

{content}
---
**Actions:**
1. Edit the text above if needed.
2. Add the label **"publish"** to post this to LinkedIn.
3. Close the issue to discard.
    """
    issue = repo.create_issue(title=f"Draft: {topic}", body=body, labels=["draft"])
    return issue

def send_email(issue_url, topic):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = os.environ["EMAIL_RECEIVER"]
    
    msg = MIMEText(f"New Draft Ready: {topic}\n\nReview here: {issue_url}")
    msg['Subject'] = f"🚀 Review: {topic}"
    msg['From'] = sender
    msg['To'] = receiver
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        server.send_message(msg)

if __name__ == "__main__":
    print("🧠 Brainstorming...")
    history = load_history()
    topic = get_unique_topic(history)
    print(f"💡 Topic: {topic}")
    
    content = generate_draft(topic)
    
    print("📝 Creating Issue...")
    issue = create_issue(topic, content)
    
    print("📧 Sending Email...")
    send_email(issue.html_url, topic)
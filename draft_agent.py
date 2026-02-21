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
    You are an Expert Developer Advocate and Senior Staff Engineer. 
    Your task is to suggest a single, highly specific technical topic for a LinkedIn post.

    Focus Areas (Choose ONE randomly to keep content fresh): 
    - Backend Engineering & System Design (e.g., Database Sharding trade-offs, Event-driven architectures, Caching strategies)
    - Generative AI & Cloud (e.g., RAG optimization, Building AI Agents with AWS Bedrock, LLM context limits)
    - Data Structures, Algorithms & Python (e.g., Advanced DP patterns, Optimizing Python code for scale, LeetCode patterns for real-world use)

    Strict Constraints:
    1. The topic MUST be niche, actionable, and tailored for mid-to-senior software engineers.
    2. NO generic advice like "How to learn Python" or "Why AI is the future".
    3. DO NOT use any of these past topics: {past_topics}

    Output Requirement:
    Return ONLY the topic title. Do not include quotes, preambles, or explanations.
    """
    return invoke_claude(prompt).strip()

def generate_draft(topic):
    prompt = f"""
    You are a Senior Staff Engineer writing a LinkedIn post about: "{topic}".
    Your target audience consists of Junior, Mid-level, and Senior Software Engineers who want deep, practical insights.

    Write the post following this exact structure:
    1. The Hook: Start with a contrarian statement, a common developer misconception, or a real-world production failure related to the topic. (Max 2 lines).
    2. The "Aha!" Moment: Explain the core technical concept or trade-off clearly. "Show, don't tell."
    3. The Blueprint: Provide 3-4 actionable bullet points, a mini-framework, or a specific architectural rule of thumb.
    4. The Closer: End with a specific, open-ended technical question to drive comments.

    Tone & Formatting Constraints:
    - Tone: Confident, insightful, conversational, and strictly fluff-free. 
    - Banned Words: DO NOT use generic AI buzzwords (e.g., "delve", "tapestry", "in today's fast-paced world", "supercharge").
    - Formatting: Use clear line breaks for scannability. Use a maximum of 3 relevant emojis in the entire post.
    - Length: Keep it under 1200 characters. 
    - Hashtags: Place exactly 4 relevant hashtags at the very bottom. DO NOT use hashtags inline.

    Output the LinkedIn post text directly with no introductory or concluding remarks.
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
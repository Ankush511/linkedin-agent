import os
import json
import boto3
import smtplib
from email.mime.text import MIMEText
from github import Github
from datetime import datetime
from botocore.exceptions import ClientError

HISTORY_FILE = "topic_history.json"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
AWS_REGION = "us-east-1" 

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
    - Backend Engineering & System Design (e.g., Database Sharding trade-offs, Event-driven architectures, Caching strategies, Clean Architecture etc.)
    - Generative AI & Cloud (e.g., RAG optimization, Building AI Agents with AWS Bedrock, LLM context limits, MCP Servers, etc)

    Strict Constraints:
    1. The topic MUST be niche, actionable, and tailored for early-to-senior software engineers.
    2. NO generic advice like "How to learn Python" or "Why AI is the future".
    3. DO NOT use any of these past topics: {past_topics}

    Output Requirement:
    Return ONLY the topic title. Do not include quotes, preambles, or explanations.
    """
    return invoke_claude(prompt).strip()

def generate_draft(topic):
    prompt = f"""
    Write a LinkedIn post about: "{topic}".
    
    Persona: You are an approachable, insightful software engineer sharing a "lightbulb" moment. You are explaining this to a mix of junior engineers, students, and peers. Make it fun, relatable, and easy to digest without feeling overwhelming.
    
    CRITICAL "Anti-Robot" Rules:
    1. NO HYPHENS OR ASTERISKS FOR LISTS (- or *). Do not use standard markdown formatting. If you need a list, use simple numbers (1., 2.) or just use line breaks.
    2. NO AI BUZZWORDS. Strictly ban: delve, tapestry, realm, navigate, supercharge, crucial, landscape, unlock, foster, beacon.
    3. Emojis: Use a MAXIMUM of 5 emojis in the entire post. Use them strategically.
    4. Write like a human. Use short, punchy sentences. Conversational tone.
    5. Formatting: Use plenty of line breaks (whitespace) so it is highly scannable and easy to read.

    Structure:
    1. The Hook: Start with a relatable struggle, a funny myth-bust, or a direct technical observation. 
    2. The "Aha!" Moment & Example: Explain the core concept simply. YOU CAN include a brief, easy-to-understand real-world example to make the concept click for a junior dev.
    3. The Takeaway: Give them one practical rule of thumb to remember.
    4. The Closer: Ask a casual question to spark comments (e.g., "How do you usually handle this?").
    5. Hashtags: Place exactly 3 to 5 highly relevant hashtags at the very bottom.
    6. Length: Keep it under 1000 characters. 

    Output the raw text only. No introductory or concluding remarks. Just the post content.
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
    print("🚀 Starting Agent...")
    history = load_history()
    
    custom_topic = os.environ.get("CUSTOM_TOPIC", "").strip()
    
    if custom_topic:
        print(f"🎯 UI Custom topic detected: {custom_topic}")
        topic = custom_topic
    else:
        print("🧠 No custom topic. Brainstorming automatically...")
        topic = get_unique_topic(history)
        print(f"💡 Auto-Topic: {topic}")
    
    # Generate and notify
    content = generate_draft(topic)
    issue = create_issue(topic, content)
    send_email(issue.html_url, topic)
import os
import json
import boto3
import smtplib
from email.mime.text import MIMEText
from github import Github
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

def invoke_claude(prompt, max_tokens=2000):
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
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

def load_topic_history():
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

def generate_linkedin_post(topic):
    prompt = f"""
    Write a LinkedIn post about: "{topic}".
    
    CRITICAL "Grounded Reality" Rule: 
    DO NOT invent fake startup metrics, massive cloud bills (e.g., "$800 API costs"), or fake user bases. Do not pretend to be a founder. Frame your "struggles" around standard developer realities: debugging a tricky issue, optimizing a local script, reading documentation, or a standard team architecture discussion. Keep the stakes realistic.
    
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
    return invoke_claude(prompt, max_tokens=2200)

def generate_hashnode_article(topic, linkedin_summary):
    prompt = f"""
    You are a Senior Software Engineer writing a deep-dive technical blog post for Hashnode for Beginners/Freshers on this Software Engineering domain.
    The topic is: "{topic}". 
    
    CRITICAL CONTENT RULES (READ CAREFULLY):
    1. PURE KNOWLEDGE TRANSFER: Do NOT use fake personal anecdotes, fake company scenarios, or phrases like "last week our service faced this" or "my team". Write this as a highly objective, educational deep dive.
    2. FOCUS: Explain HOW the technology works, WHY we need it, and its PROS & CONS. (e.g., If the topic is Kafka + Idempotency, explain how they work together fundamentally).
    3. CODE: Use shorter, highly meaningful code examples that get straight to the point without bloat.
    4. COMPLETION: Ensure the article is fully completed with a proper conclusion. Do not cut off mid-thought.
    
    STRUCTURE REQUIREMENTS:
    1. Catchy Title: Start with a single `# Title` line.
    2. The Core Problem: Objective explanation of what problem this tech solves.
    3. The Mental Model: A clear conceptual breakdown.
    4. Code Examples: Clear `java` blocks or `bash` commands.
    5. Trade-offs / Pros & Cons.
    
    Output ONLY the Markdown content. Start directly with the `# Title`.
    """
    return invoke_claude(prompt, max_tokens=8000)

def create_review_issue(topic, linkedin_content, hashnode_content):
    g = Github(os.environ["GITHUB_TOKEN"])
    repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
    
    body = f"""🤖 Draft generated for topic: {topic}

---HASHNODE_ARTICLE---
{hashnode_content}
---LINKEDIN_POST---
{linkedin_content}
---END---
"""
    issue = repo.create_issue(title=f"Draft: {topic}", body=body, labels=["draft"])
    return issue

def send_notification_email(issue_url, topic):
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
    history = load_topic_history()
    
    custom_topic = os.environ.get("CUSTOM_TOPIC", "").strip()
    topic = custom_topic if custom_topic else get_unique_topic(history)
    
    print("✍️ Generating LinkedIn Draft...")
    linkedin_content = generate_linkedin_post(topic)
    
    print("📝 Generating Hashnode Article...")
    hashnode_content = generate_hashnode_article(topic, linkedin_content)
    
    print("📦 Creating GitHub Issue...")
    issue = create_review_issue(topic, linkedin_content, hashnode_content)
    send_notification_email(issue.html_url, topic)
    print("✅ Done!")
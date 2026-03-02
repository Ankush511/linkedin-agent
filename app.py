import streamlit as st
import requests
import json
import base64
import boto3
import pandas as pd
import time

st.set_page_config(page_title="LinkedIn Command Center", page_icon="🚀", layout="wide")

# --- CONFIG & SECRETS ---
GITHUB_PAT = st.secrets["GITHUB_PAT"]
REPO_OWNER = st.secrets["REPO_OWNER"]
REPO_NAME = st.secrets["REPO_NAME"]
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
HASHNODE_TOKEN = st.secrets["HASHNODE_TOKEN"]
HASHNODE_PUBLICATION_ID = st.secrets["HASHNODE_PUBLICATION_ID"]

HEADERS = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

ISSUES_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues?labels=draft&state=open"
HISTORY_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/topic_history.json"

def publish_blog_to_hashnode(content):
    headers = {"Authorization": HASHNODE_TOKEN, "Content-Type": "application/json"}
    lines = content.strip().split('\n')
    title = lines[0].replace("#", "").strip() if lines[0].startswith("#") else "Technical Deep Dive"
    body_content = '\n'.join(lines[1:]).strip()
    
    query = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) { post { url } }
    }
    """
    variables = {
        "input": {"title": title, "contentMarkdown": body_content, "publicationId": HASHNODE_PUBLICATION_ID}
    }
    resp = requests.post("https://gql.hashnode.com/", headers=headers, json={"query": query, "variables": variables})
    if resp.status_code != 200:
        raise Exception(f"Hashnode API Error: {resp.text}")
    return resp.json()['data']['publishPost']['post']['url']

st.title("🚀 LinkedIn Agent Command Center")
tab1, tab2, tab3 = st.tabs(["✍️ Generate Post", "📊 Dashboard", "🧠 Brainstormer"])

# TAB 1: GENERATION CONTROLS
with tab1:
    st.markdown("### Force the Agent to write a specific post")
    topic_input = st.text_input("Custom Topic:", placeholder="e.g., Sliding Window Pattern in Python")

    if st.button("🚀 Generate Draft Now", type="primary"):
        current_issues_resp = requests.get(ISSUES_URL, headers=HEADERS)
        current_issue_ids = [issue['id'] for issue in current_issues_resp.json()] if current_issues_resp.status_code == 200 else []
        
        with st.spinner("Waking up GitHub Actions & generating draft (takes ~60-90 seconds)..."):
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/daily_draft.yml/dispatches"
            payload = {"ref": "main", "inputs": {"custom_topic": topic_input}}
            requests.post(url, headers=HEADERS, json=payload)
            
            for _ in range(24):
                time.sleep(5)
                check_resp = requests.get(ISSUES_URL, headers=HEADERS)
                if check_resp.status_code == 200:
                    if any(i['id'] not in current_issue_ids for i in check_resp.json()):
                        st.success("✅ Draft generated! Refreshing...")
                        time.sleep(2)
                        st.rerun()
            st.warning("⏳ Check the Dashboard tab in a minute.")

# TAB 2: THE DASHBOARD (NOW WITH INNER TABS)
with tab2:
    st.markdown("### 📋 Awaiting Your Approval")
    issues_resp = requests.get(ISSUES_URL, headers=HEADERS)
    
    if issues_resp.status_code == 200:
        issues = issues_resp.json()
        if not issues:
            st.info("🎉 No drafts waiting for approval! You're all caught up.")
            
        for issue in issues:
            issue_num = issue['number']
            raw_body = issue['body'] or ""
            
            try:
                hn_text = raw_body.split("---HASHNODE_ARTICLE---")[1].split("---LINKEDIN_POST---")[0].strip()
                li_text = raw_body.split("---LINKEDIN_POST---")[1].split("---END---")[0].strip()
            except IndexError:
                hn_text = raw_body
                li_text = ""

            with st.expander(f"📝 Draft: {issue['title']}", expanded=True):
                
                # --- INNER TABS FOR REVIEW ---
                blog_tab, li_tab = st.tabs(["📝 Review Hashnode Blog", "💼 Review LinkedIn Post"])
                
                with blog_tab:
                    updated_hn = st.text_area("Edit Blog Markdown:", value=hn_text, height=450, key=f"hn_{issue_num}")
                
                with li_tab:
                    st.info("💡 When you click '1️⃣ Publish Blog' below, the live URL will automatically be injected at the bottom of this text.")
                    updated_li = st.text_area("Edit LinkedIn Summary:", value=li_text, height=300, key=f"li_{issue_num}")
                
                new_full_body = f"🤖 Draft generated for topic: {issue['title'].replace('Draft: ', '')}\n\n---HASHNODE_ARTICLE---\n{updated_hn}\n---LINKEDIN_POST---\n{updated_li}\n---END---\n"
                
                st.markdown("---")
                col1, col2, col3, col4 = st.columns([1, 1.2, 1.2, 1])
                
                with col1:
                    if st.button("💾 Save Edits", key=f"save_{issue_num}"):
                        requests.patch(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}", headers=HEADERS, json={"body": new_full_body})
                        st.success("✅ Saved!")
                
                with col2:
                    if st.button("1️⃣ Publish Blog", type="primary", key=f"pub_blog_{issue_num}"):
                        with st.spinner("Publishing to Hashnode..."):
                            try:
                                url = publish_blog_to_hashnode(updated_hn)

                                appended_li = updated_li + f"\n\n📖 Read the detailed guide/blog on this here: {url}"
                                appended_body = f"🤖 Draft generated for topic: {issue['title'].replace('Draft: ', '')}\n\n---HASHNODE_ARTICLE---\n{updated_hn}\n---LINKEDIN_POST---\n{appended_li}\n---END---\n"
                                
                                requests.patch(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}", headers=HEADERS, json={"body": appended_body})
                                st.success("✅ Blog Live! Reloading UI...")
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
                                
                with col3:
                    if st.button("2️⃣ Publish to LinkedIn", type="primary", key=f"pub_li_{issue_num}"):
                        requests.patch(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}", headers=HEADERS, json={"body": new_full_body})
                        requests.post(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}/labels", headers=HEADERS, json={"labels": ["publish"]})
                        st.success("🚀 Pushing to LinkedIn! (Check GitHub Actions)")
                        time.sleep(2)
                        st.rerun()
                        
                with col4:
                    if st.button("🗑️ Discard", key=f"discard_{issue_num}"):
                        requests.patch(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}", headers=HEADERS, json={"state": "closed"})
                        st.success("🗑️ Discarded!")
                        time.sleep(1)
                        st.rerun()

    else:
        st.error("Could not fetch drafts from GitHub.")
    
    st.markdown("---")
    st.markdown("### 📚 Content Archive")
    
    hist_resp = requests.get(HISTORY_URL, headers=HEADERS)
    
    if hist_resp.status_code == 200:
        file_data = hist_resp.json()
        content_b64 = file_data['content']
        file_sha = file_data['sha']
        
        decoded_content = base64.b64decode(content_b64).decode('utf-8')
        history_data = json.loads(decoded_content)
        
        df = pd.DataFrame(history_data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values(by="date", ascending=False).reset_index(drop=True)
            
            st.metric("Total Posts Published", len(df))
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "date": st.column_config.DateColumn("Published Date", format="MMM DD, YYYY", width="medium"),
                    "topic": st.column_config.TextColumn("Post Topic", width="large")
                }
            )
            
            st.markdown("---")
            st.markdown("#### Danger Zone")
            if st.button("🗑️ Delete History File", type="primary", help="Permanently deletes topic_history.json"):
                with st.spinner("Deleting file from GitHub..."):
                    delete_resp = requests.delete(HISTORY_URL, headers=HEADERS, json={"message": "Deleted topic_history.json via Streamlit UI", "sha": file_sha})
                    if delete_resp.status_code == 200:
                        st.success("✅ History file deleted! The bot's memory is wiped.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to delete file: {delete_resp.text}")
    else:
        st.info("No history file found yet. It will appear here after your first published post.")

# TAB 3: BRAINSTORMING ASSISTANT
with tab3:
    st.markdown("### Let Claude generate 5 rapid-fire ideas.")
    theme = st.text_input("Enter a broad theme:", placeholder="e.g., Graph Algorithms, GenAI APIs, Clean Code")
    
    if st.button("🧠 Brainstorm Ideas"):
        if not theme:
            st.warning("Please enter a theme first.")
        else:
            with st.spinner("Thinking..."):
                try:
                    bedrock = boto3.client(
                        'bedrock-runtime', 
                        region_name='us-east-1',
                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                    )
                    prompt = f"Give me 5 highly specific, actionable LinkedIn post ideas about '{theme}' for backend developers. Output ONLY a numbered list."
                    payload = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
                    }
                    response = bedrock.invoke_model(
                        modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0", 
                        body=json.dumps(payload)
                    )
                    result = json.loads(response['body'].read())
                    
                    st.success("Done! Copy your favorite and paste it into the Generate tab.")
                    st.markdown(result['content'][0]['text'])
                except Exception as e:
                    st.error(f"AWS Error: {e}")
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

HEADERS = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

ISSUES_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues?labels=draft&state=open"
HISTORY_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/topic_history.json"

st.title("🚀 LinkedIn Agent Command Center")

tab1, tab2, tab3 = st.tabs(["✍️ Generate Post", "📊 Dashboard", "🧠 Brainstormer"])

with tab1:
    st.markdown("### Force the Agent to write a specific post")
    st.markdown("Leave blank to let the agent auto-brainstorm based on your history.")
    
    topic_input = st.text_input("Custom Topic:", placeholder="e.g., Sliding Window Pattern in Python")

    if st.button("🚀 Generate Draft Now", type="primary"):
        current_issues_resp = requests.get(ISSUES_URL, headers=HEADERS)
        current_issue_ids = [issue['id'] for issue in current_issues_resp.json()] if current_issues_resp.status_code == 200 else []
        
        with st.spinner("Waking up GitHub Actions & generating draft (takes ~60-90 seconds)..."):
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/daily_draft.yml/dispatches"
            payload = {"ref": "main", "inputs": {"custom_topic": topic_input}}
            resp = requests.post(url, headers=HEADERS, json=payload)
            
            if resp.status_code == 204:
                max_retries = 24
                found_new = False
                
                for _ in range(max_retries):
                    time.sleep(5)
                    check_resp = requests.get(ISSUES_URL, headers=HEADERS)
                    
                    if check_resp.status_code == 200:
                        new_issue_ids = [issue['id'] for issue in check_resp.json()]
                        if any(i_id not in current_issue_ids for i_id in new_issue_ids):
                            found_new = True
                            break
                            
                if found_new:
                    st.success("✅ Draft successfully generated! Refreshing dashboard...")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("⏳ The workflow is running, but taking a bit longer than expected. Check the Dashboard tab in a minute.")
            else:
                st.error(f"❌ Failed to trigger workflow. Status: {resp.status_code}")
                st.write(resp.text)

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
                
                st.markdown("#### 1. The Hashnode Article")
                updated_hn = st.text_area("Edit Blog (Markdown):", value=hn_text, height=400, key=f"hn_{issue_num}")
                
                st.markdown("#### 2. The LinkedIn Summary")
                updated_li = st.text_area("Edit Post:", value=li_text, height=200, key=f"li_{issue_num}")
                
                st.info("💡 When you hit publish, the bot will post to Hashnode, grab the URL, and attach 'To know more on this, check out my detailed blog: [URL]' to the bottom of the LinkedIn post.")

                new_full_body = f"🤖 Draft generated for topic: {issue['title'].replace('Draft: ', '')}\n\n---HASHNODE_ARTICLE---\n{updated_hn}\n---LINKEDIN_POST---\n{updated_li}\n---END---\n"
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if st.button("💾 Save Edits", key=f"save_{issue_num}"):
                        patch_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}"
                        requests.patch(patch_url, headers=HEADERS, json={"body": new_full_body})
                        st.success("✅ Edits saved to GitHub!")
                
                with col2:
                    if st.button("🚀 Publish Everywhere", key=f"pub_{issue_num}", type="primary"):
                        patch_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}"
                        requests.patch(patch_url, headers=HEADERS, json={"body": new_full_body})
                        
                        label_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}/labels"
                        label_resp = requests.post(label_url, headers=HEADERS, json={"labels": ["publish"]})
                        
                        if label_resp.status_code == 200:
                            st.success("🚀 Publishing sequence initiated! GitHub Actions is handling the rest.")
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to initiate publish. {label_resp.text}")
                            
                with col3:
                    if st.button("🗑️ Discard Draft", key=f"discard_{issue_num}"):
                        patch_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}"
                        requests.patch(patch_url, headers=HEADERS, json={"state": "closed"})
                        st.success("🗑️ Draft successfully discarded!")
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
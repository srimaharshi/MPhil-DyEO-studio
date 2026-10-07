import streamlit as st
import google.generativeai as genai
import os
from supabase import create_client, Client
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS
import io

# 1. Page Configuration
st.set_page_config(
    page_title="MPhil & DyEO Learning Hub",
    page_icon="📚",
    layout="wide"
)

# 2. Initialize Supabase Client
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase connection error: {e}")
        return None

supabase: Client = init_supabase()

# Helper Functions for Cloud Sync
def fetch_notes_from_cloud():
    if supabase:
        try:
            response = supabase.table("study_notes").select("*").execute()
            return {row["topic"]: row["notes"] for row in response.data}
        except Exception as e:
            st.warning(f"Could not fetch notes from cloud: {e}")
    return {}

def save_note_to_cloud(topic, notes):
    if supabase:
        try:
            supabase.table("study_notes").upsert({"topic": topic, "notes": notes}).execute()
            st.success("Cloud lo Sync aipoyindi! ☁️")
        except Exception as e:
            st.error(f"Sync error: {e}")

# Load initial notes
if "cloud_notes" not in st.session_state:
    st.session_state.cloud_notes = fetch_notes_from_cloud()

# 3. Sidebar for API Key & Exam Selection
st.sidebar.title("🎯 Control Panel")
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

exam_target = st.sidebar.selectbox(
    "Select Target Exam",
    ["MPhil Clinical Psychology", "Telangana DyEO (District Educational Officer)"]
)

if api_key:
    genai.configure(api_key=api_key)

# 4. Main App Navigation (6 Tabs)
st.title("🚀 Smart LMS & Revision Engine")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📖 Notes Hub", 
    "📂 PYQ Repository", 
    "📝 CBT Mock Engine", 
    "⚡ Practice Engine", 
    "🎥 YouTube Hub", 
    "📌 Revision Cheatsheet"
])

# ----------------- TAB 1: NOTES HUB -----------------
with tab1:
    st.header("Cloud-Synced Notes Hub")
    topic = st.text_input("Enter Topic Name (e.g., Cognitive Behavioral Therapy / Educational Statistics)")
    
    if st.button("Generate & Sync Notes"):
        if not api_key:
            st.error("Please enter Gemini API Key in the sidebar!")
        elif not topic:
            st.warning("Topic name enter cheyi buddy!")
        else:
            with st.spinner("AI Notes generate chestondi..."):
                model = genai.GenerativeModel('gemini-pro')
                prompt = f"Create comprehensive study notes for {exam_target} on topic: {topic}. Include Key Concepts, Definitions, and Exam Bullet Points."
                response = model.generate_content(prompt)
                generated_text = response.text
                
                st.markdown(generated_text)
                
                # Audio Generation using gTTS
                tts = gTTS(text=generated_text[:500], lang='en')
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                st.audio(audio_fp, format='audio/mp3')
                
                # Save to Supabase Cloud
                save_note_to_cloud(topic, generated_text)
                st.session_state.cloud_notes[topic] = generated_text

    st.divider()
    st.subheader("📚 Saved Cloud Notes")
    if st.session_state.cloud_notes:
        selected_topic = st.selectbox("View Saved Notes", list(st.session_state.cloud_notes.keys()))
        if selected_topic:
            st.write(st.session_state.cloud_notes[selected_topic])
    else:
        st.info("No saved notes found in cloud yet.")

# ----------------- TAB 2: PYQ REPOSITORY -----------------
with tab2:
    st.header("Previous Year Questions (PYQs)")
    st.info("Upload exam PYQ PDFs to search or analyze key themes.")
    uploaded_file = st.file_uploader("Upload PYQ PDF", type=["pdf"])
    if uploaded_file:
        st.success(f"Uploaded: {uploaded_file.name}")

# ----------------- TAB 3: CBT MOCK ENGINE -----------------
with tab3:
    st.header("CBT Mock Test Engine")
    mock_subject = st.text_input("Subject for Mock Test", value="General Psychology / Education")
    
    if st.button("Start Mock Test"):
        if api_key:
            with st.spinner("Creating 5 High-Yield Questions..."):
                model = genai.GenerativeModel('gemini-pro')
                prompt = f"Generate 5 Multiple Choice Questions for {exam_target} on {mock_subject} with options A, B, C, D and indicate the correct answer at the end."
                res = model.generate_content(prompt)
                st.markdown(res.text)
        else:
            st.error("Gemini API key enter cheyi buddy!")

# ----------------- TAB 4: PRACTICE ENGINE -----------------
with tab4:
    st.header("Practice Engine & Answer Writing")
    q_topic = st.text_input("Enter Question / Topic for Practice")
    user_answer = st.text_area("Write your answer here:")
    
    if st.button("Evaluate Answer"):
        if api_key and user_answer:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"Evaluate this answer for {exam_target}.\nQuestion: {q_topic}\nUser Answer: {user_answer}\nProvide score out of 10, feedback, and missing points."
            res = model.generate_content(prompt)
            st.markdown(res.text)

# ----------------- TAB 5: YOUTUBE LEARNING HUB -----------------
with tab5:
    st.header("YouTube Video Summarizer")
    yt_url = st.text_input("Paste YouTube Video URL")
    
    if st.button("Summarize Video"):
        if yt_url:
            try:
                video_id = yt_url.split("v=")[-1].split("&")[0]
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                text = " ".join([t['text'] for t in transcript])
                
                if api_key:
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = f"Summarize this YouTube transcript into key exam notes for {exam_target}:\n{text[:4000]}"
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
                else:
                    st.write("Transcript extracted:")
                    st.write(text[:1000] + "...")
            except Exception as e:
                st.error(f"Transcript Error: {e}")

# ----------------- TAB 6: REVISION CHEATSHEET -----------------
with tab6:
    st.header("Quick Revision Cheatsheet")
    if st.button("Generate Rapid Revision Sheet"):
        if api_key:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"Provide a high-yield quick revision bullet-point list of top 15 formulas/theories for {exam_target}."
            res = model.generate_content(prompt)
            st.markdown(res.text)

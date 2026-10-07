import streamlit as st
import google.generativeai as genai
import pypdf
import io
import docx
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS
import time
import json
import re

st.set_page_config(page_title="MPhil & DyEO Target LMS Studio", layout="wide", page_icon="🎓")

# Global State Initialization for Hierarchy & Vault
if 'hierarchy' not in st.session_state:
    st.session_state['hierarchy'] = {
        "Clinical Psychology": {
            "Neurodevelopmental Disorders": ["Autism Spectrum Disorder (ASD)", "ADHD"],
            "Schizophrenia Spectrum": ["Diagnostic Criteria", "Differential Diagnosis"]
        },
        "Educational Management (DyEO)": {
            "Educational Policies": ["NEP 2020", "RTE Act 2009"]
        }
    }

# Sidebar Engine Controls
st.sidebar.title("⚙️ Engine Controls")
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
if api_key:
    genai.configure(api_key=api_key)

category = st.sidebar.selectbox(
    "Target Exam Category",
    [
        "MPhil Clinical Psychology (Pure English)",
        "Telangana DyEO Paper-2 Education (Bilingual)",
        "Telangana DyEO Paper-1 GS (Bilingual)"
    ]
)

# DYNAMIC HIERARCHY SETUP
st.sidebar.markdown("---")
st.sidebar.subheader("📌 Syllabus Hierarchy Manager")

curr_subject = st.sidebar.selectbox("Select Subject:", list(st.session_state['hierarchy'].keys()))

# Add Subject
new_sub = st.sidebar.text_input("➕ New Subject Name:")
if st.sidebar.button("Add Subject"):
    if new_sub and new_sub not in st.session_state['hierarchy']:
        st.session_state['hierarchy'][new_sub] = {}
        st.rerun()

curr_chapter = st.sidebar.selectbox("Select Chapter:", list(st.session_state['hierarchy'][curr_subject].keys()) if st.session_state['hierarchy'][curr_subject] else ["None"])

# Add Chapter
new_chap = st.sidebar.text_input("➕ New Chapter Name:")
if st.sidebar.button("Add Chapter"):
    if new_chap and curr_subject:
        st.session_state['hierarchy'][curr_subject][new_chap] = []
        st.rerun()

subtopic_list = st.session_state['hierarchy'][curr_subject].get(curr_chapter, []) if curr_chapter != "None" else []
curr_subtopic = st.sidebar.selectbox("Select Sub-topic:", subtopic_list if subtopic_list else ["None"])

# Add Sub-topic
new_subtopic = st.sidebar.text_input("➕ New Sub-topic Name:")
if st.sidebar.button("Add Sub-topic"):
    if new_subtopic and curr_chapter != "None":
        st.session_state['hierarchy'][curr_subject][curr_chapter].append(new_subtopic)
        st.rerun()

# Workspace Header
st.title(f"🎓 Target Studio: {category}")
st.caption(f"📍 Active Path: **{curr_subject}** ➔ **{curr_chapter}** ➔ **{curr_subtopic}**")

# MAIN TABS NAVIGATION
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📚 Exhaustive Notes Hub", 
    "📄 PYQ Repository", 
    "🎯 CBT Mock Test Engine", 
    "🎮 Topic-wise Practice", 
    "📺 YouTube Learning Hub",
    "⚡ Revision Cheatsheet"
])

def extract_pdf_text(uploaded_files):
    text = ""
    for file in uploaded_files:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def create_docx(text):
    doc = docx.Document()
    for line in text.split('\n'):
        doc.add_paragraph(line)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_pdf(text):
    bio = io.BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    for line in text.split('\n'):
        if line.strip():
            story.append(Paragraph(line, styles['Normal']))
            story.append(Spacer(1, 4))
    doc.build(story)
    return bio.getvalue()

def generate_audio(text_content):
    clean_text = re.sub(r'[*#_`]', '', text_content[:1500])
    tts = gTTS(text=clean_text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

# TAB 1: EXHAUSTIVE NOTES
with tab1:
    st.header("📖 Line-by-Line Exhaustive Topic Notes")
    
    col_a, col_b = st.columns(2)
    with col_a:
        book_names = st.text_input("Book Names & Authors (Optional):", value="Kaplan & Sadock, DSM-5-TR")
    with col_b:
        uploaded_files = st.file_uploader("Upload Reference PDFs:", type=["pdf"], accept_multiple_files=True)
    
    target_topic = st.text_input("Target Topic for Line-by-Line Synthesis:", value=f"{curr_chapter} - {curr_subtopic}")
    
    if st.button("⚡ Generate Line-by-Line Deep Notes"):
        if not api_key:
            st.error("Please enter Gemini API Key in Sidebar!")
        else:
            with st.spinner("Synthesizing exhaustive notes, auto-fetching missing criteria & differential matrix..."):
                model = genai.GenerativeModel('gemini-1.5-pro')
                raw_text = extract_pdf_text(uploaded_files) if uploaded_files else ""
                
                prompt = f"""
                Act as a Senior Clinical Psychologist & DyEO Exam Expert.
                Category: {category} | Subject: {curr_subject} | Chapter: {curr_chapter}
                Topic: {target_topic} | Referenced Books: {book_names}
                Uploaded Context: {raw_text[:20000]}
                
                STRICT INSTRUCTIONS:
                1. DO NOT PROVIDE SUMMARIES OR SHORT OVERVIEWS.
                2. Provide line-by-line exhaustive detail required for entrance MCQs.
                3. Include Diagnostic Criteria (DSM-5-TR / ICD-11), Etiology, Neurobiology, Cut-offs & Interventions.
                4. Auto-search and fill missing standard textbook information if pdf context is partial.
                5. Add a dedicated 'Differential Diagnosis Matrix Table'.
                6. If bilingual, provide side-by-side Telugu & English formatting.
                """
                res = model.generate_content(prompt)
                st.session_state['current_notes'] = res.text
                st.markdown("### 📝 Detailed Line-by-Line Notes")
                st.write(res.text)
                
                # Audio & Download
                st.audio(generate_audio(res.text), format="audio/mp3")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.download_button("📥 Download PDF Notes", data=create_pdf(res.text), file_name=f"{target_topic}_Notes.pdf", mime="application/pdf")
                with col_d2:
                    st.download_button("📥 Download DOCX Notes", data=create_docx(res.text), file_name=f"{target_topic}_Notes.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# TAB 2: PYQ REPOSITORY
with tab2:
    st.header("📄 University Past Year Question (PYQ) Vault")
    uploaded_pyqs = st.file_uploader("Upload Question Papers (PDF):", type=["pdf"], accept_multiple_files=True, key="pyq_vault")
    if uploaded_pyqs:
        st.session_state['vault_pyq_text'] = extract_pdf_text(uploaded_pyqs)
        st.success(f"Stored {len(uploaded_pyqs)} PYQ files!")
        
    st.subheader("🧘 Untimed Stress-Free PYQ Practice")
    if st.button("🚀 Start Untimed PYQ Practice"):
        if not api_key or 'vault_pyq_text' not in st.session_state:
            st.error("Upload PYQ PDFs & enter API Key first!")
        else:
            model = genai.GenerativeModel('gemini-1.5-pro')
            prompt = f"Generate 5 PYQ-styled MCQs from context: {st.session_state['vault_pyq_text'][:15000]}. Return JSON format with question, options, answer, and distractor rationale."
            res = model.generate_content(prompt)
            st.write(res.text)

# TAB 3: CBT MOCK TEST ENGINE
with tab3:
    st.header("🎯 CBT Timed Live Mock Test Engine")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        num_q = st.slider("Select Question Count:", 5, 50, 10)
    with col2:
        test_mode = st.selectbox("Exam Pattern:", ["Conceptual & Vignette Mixed", "Direct Factual & Terminology", "PYQ Pattern"])
    with col3:
        enable_neg = st.checkbox("Enable Negative Marking (-0.25)", value=True)
        
    if st.button("🚀 Start CBT Live Exam") or st.button("🔄 Generate Next Fresh Set of MCQs"):
        if not api_key:
            st.error("Enter Gemini API Key!")
        else:
            with st.spinner("Compiling CBT Exam..."):
                model = genai.GenerativeModel('gemini-1.5-pro')
                prompt = f"""
                Generate {num_q} high-yield MCQs for {category}. Active Subject: {curr_subject}, Chapter: {curr_chapter}. Pattern: {test_mode}.
                Return JSON only: [{{"id":1, "question":"...", "options":["A) ..","B) ..","C) ..","D) .."], "answer":"A) ..", "rationale":"...", "subtopic":"{curr_subtopic}"}}]
                """
                try:
                    res = model.generate_content(prompt)
                    clean_json = res.text.replace("```json", "").replace("```", "").strip()
                    st.session_state['cbt_questions'] = json.loads(clean_json)
                    st.session_state['start_time'] = time.time()
                    st.session_state['duration'] = num_q * 60
                    st.session_state['user_answers'] = {}
                    st.rerun()
                except Exception as e:
                    st.error("Format error, please click Generate again.")

    if 'cbt_questions' in st.session_state:
        elapsed = int(time.time() - st.session_state['start_time'])
        rem = st.session_state['duration'] - elapsed
        st.warning(f"⏳ Timer Remaining: {max(0, rem) // 60} Min {max(0, rem) % 60} Sec")

        with st.form("cbt_form"):
            for idx, q in enumerate(st.session_state['cbt_questions']):
                st.markdown(f"**Q{idx+1}: {q['question']}**")
                st.session_state['user_answers'][idx] = st.radio("Select Answer:", q['options'], key=f"cbt_q_{idx}")
                st.divider()
            
            if st.form_submit_button("📊 Submit Test & View Results"):
                score, correct, wrong = 0.0, 0, 0
                weak_topics = []
                st.markdown("## 📈 Performance & Instant Weakness Set")
                for idx, q in enumerate(st.session_state['cbt_questions']):
                    user_ans = st.session_state['user_answers'].get(idx)
                    if user_ans == q['answer']:
                        score += 1.0
                        correct += 1
                        st.success(f"Q{idx+1}: Correct! Selected: {user_ans}")
                    else:
                        wrong += 1
                        if enable_neg: score -= 0.25
                        st.error(f"Q{idx+1}: Wrong! Selected: {user_ans} | Correct: {q['answer']}")
                        weak_topics.append(q.get('subtopic', curr_subtopic))
                    st.info(f"💡 Rationale: {q['rationale']}")
                
                st.metric("Final Score", f"{score:.2f} / {len(st.session_state['cbt_questions'])}")
                
                # IMMEDIATE WEAKNESS PRACTICE SET
                if weak_topics:
                    st.markdown("---")
                    st.subheader("🚨 Immediate Weakness Targeted Practice Set")
                    st.warning(f"Re-visiting weak areas identified in this test: {', '.join(set(weak_topics))}")

# TAB 4: TOPIC-WISE PRACTICE ENGINE
with tab4:
    st.header("🎮 Subject & Topic Practice Engine")
    practice_topic = st.text_input("Target Topic:", value=f"{curr_subject} - {curr_chapter}")
    practice_count = st.slider("MCQ Count:", 5, 30, 15)
    
    if st.button("⚡ Generate Practice MCQs"):
        if not api_key:
            st.error("Enter Gemini API Key!")
        else:
            model = genai.GenerativeModel('gemini-1.5-pro')
            prompt = f"Generate {practice_count} MCQs with distractor rationale covering all subtopics of '{practice_topic}' for {category}."
            res = model.generate_content(prompt)
            st.write(res.text)

# TAB 5: YOUTUBE LEARNING HUB
with tab5:
    st.header("📺 YouTube Video/Playlist Notes & MCQ Hub")
    yt_url = st.text_input("Enter YouTube Video URL:")
    
    if st.button("⚡ Process YouTube Video"):
        if yt_url:
            try:
                video_id = yt_url.split("v=")[-1].split("&")[0]
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                full_text = " ".join([t['text'] for t in transcript])
                st.session_state['yt_transcript'] = full_text
                
                model = genai.GenerativeModel('gemini-1.5-pro')
                prompt = f"Convert this YouTube transcript into exhaustive line-by-line notes for {category}: {full_text[:15000]}"
                res = model.generate_content(prompt)
                
                st.markdown("### 📝 Converted YouTube Notes")
                st.write(res.text)
                st.audio(generate_audio(res.text), format="audio/mp3")
            except Exception as e:
                st.error(f"Could not fetch transcript: {e}")

# TAB 6: ON-DEMAND REVISION CHEATSHEET
with tab6:
    st.header("⚡ On-Demand Last Minute Revision Cheatsheet")
    st.caption("Generates high-yield short revision tables and key points strictly on demand.")
    
    if st.button("🚀 Generate On-Demand Cheatsheet"):
        if not api_key:
            st.error("Enter Gemini API Key!")
        else:
            model = genai.GenerativeModel('gemini-1.5-pro')
            prompt = f"Generate a high-yield last-minute revision cheatsheet with bullet points, diagnostic cut-offs, and key terms for '{curr_chapter} - {curr_subtopic}'."
            res = model.generate_content(prompt)
            st.write(res.text)
            st.audio(generate_audio(res.text), format="audio/mp3")

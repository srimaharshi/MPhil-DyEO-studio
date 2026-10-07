import streamlit as st
import json
import re
import tempfile
import io
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS
import google.generativeai as genai
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 1. Page Configuration
st.set_page_config(
    page_title="MPhil & DyEO AI Exam Studio",
    page_icon="🎓",
    layout="wide"
)

# Custom Styling
st.markdown("""
    <style>
    .stApp { background-color: #0b132b; color: #f8fafc; }
    .stButton>button { width: 100%; background-color: #1c2541; color: #6fffe9; border: 1px solid #6fffe9; border-radius: 8px; font-weight: bold; }
    .stButton>button:hover { background-color: #3a506b; color: #ffffff; }
    .card { background: #1c2541; padding: 18px; border-radius: 12px; margin-bottom: 15px; border-left: 5px solid #6fffe9; }
    </style>
""", unsafe_allow_html=True)

st.title("🎓 MPhil Clinical Psychology & DyEO Target Studio")
st.caption("Integrated Exam Engine: Auto-Search, Audio Podcast, Downloadable Notes/MCQs, & Deep Rationale MCQs")

# Helper Functions for Downloads
def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(content)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_pdf(title, content):
    bio = io.BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=letter)
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.wordWrap = 'CJK'
    
    story = [Paragraph(f"<b>{title}</b>", styles['Heading1']), Spacer(1, 12)]
    
    # Process text paragraphs
    for line in content.split('\n'):
        if line.strip():
            # Basic cleanup for ReportLab XML compatibility
            clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(clean_line, normal_style))
            story.append(Spacer(1, 6))
            
    doc.build(story)
    return bio.getvalue()

def format_mcqs_as_text(mcqs):
    formatted = "EXAM PRACTICE MCQS & RATIONALES\n\n"
    for q in mcqs:
        formatted += f"Q{q['id']}: {q['question']}\n"
        for opt in q['options']:
            formatted += f"  - {opt}\n"
        formatted += f"\nCorrect Answer: {q['correct_option']}\n"
        formatted += f"Rationale: {q['deep_rationale']}\n"
        formatted += "Distractor Analysis:\n"
        for opt, reason in q['wrong_options_analysis'].items():
            formatted += f"  - {opt}: {reason}\n"
        formatted += "\n" + "="*40 + "\n\n"
    return formatted

# 2. Sidebar Setup
st.sidebar.header("⚙️ App Settings")
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
if api_key:
    genai.configure(api_key=api_key)

folder = st.sidebar.radio("📁 Target Exam Category", [
    "MPhil Clinical Psychology (Pure English)",
    "Telangana DyEO Paper-2 (Bilingual Te+En)",
    "Telangana DyEO Paper-1 GS (Bilingual Te+En)"
])

chapter_num = st.sidebar.number_input("Chapter / Module Number", min_value=1, max_value=30, value=1)

# Session States
if "unlocked_chapters" not in st.session_state:
    st.session_state["unlocked_chapters"] = {
        "MPhil Clinical Psychology (Pure English)": 1,
        "Telangana DyEO Paper-2 (Bilingual Te+En)": 1,
        "Telangana DyEO Paper-1 GS (Bilingual Te+En)": 1
    }

if "active_notes" not in st.session_state:
    st.session_state["active_notes"] = ""
if "active_mcqs" not in st.session_state:
    st.session_state["active_mcqs"] = []
if "quiz_submitted" not in st.session_state:
    st.session_state["quiz_submitted"] = False

is_unlocked = chapter_num <= st.session_state["unlocked_chapters"].get(folder, 1)

# Workspace Header
st.markdown(f"### Current Workspace: `{folder}` | Chapter {chapter_num}")
if is_unlocked:
    st.success("🟢 Chapter Status: UNLOCKED")
else:
    st.error("🔒 Chapter Status: LOCKED (Score >= 70% in previous chapter to unlock)")

# 3. Input Engine
st.subheader("📥 Input Study Material or Auto-Search")
tab_input1, tab_input2, tab_input3 = st.tabs(["🔍 Auto Search Topic", "📄 PDF Upload", "🎥 YouTube Link"])

raw_text = ""

with tab_input1:
    search_topic = st.text_input("Enter Topic Name (Auto-Search Web Knowledge)", placeholder="e.g., DSM-5 Criteria for Schizophrenia OR Telangana Movement 1969 Phase")
    if search_topic and api_key and is_unlocked:
        if st.button("🔎 Search & Synthesize Topic"):
            with st.spinner("Searching standard academic references online & synthesizing..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                search_prompt = f"Provide comprehensive, high-yield textbook level knowledge for exam preparation on topic: '{search_topic}'. Include clinical diagnostics, key theories, historical facts, and key concepts."
                res = model.generate_content(search_prompt)
                raw_text = res.text
                st.info("Topic knowledge extracted successfully!")

with tab_input2:
    pdf_file = st.file_uploader("Upload PDF Reference Book / Notes", type=["pdf"])
    if pdf_file:
        reader = PdfReader(pdf_file)
        raw_text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
        st.info("PDF content successfully loaded!")

with tab_input3:
    yt_url = st.text_input("Paste YouTube Video URL")
    if yt_url:
        try:
            video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", yt_url)
            if video_id_match:
                video_id = video_id_match.group(1)
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                try:
                    transcript = transcript_list.find_transcript(['en', 'hi', 'te'])
                except:
                    transcript = transcript_list.find_generated_transcript(['en', 'hi', 'te'])
                raw_text = " ".join([i['text'] for i in transcript.fetch()])
                st.info("YouTube transcript extracted successfully!")
            else:
                st.error("Invalid YouTube URL format.")
        except Exception as e:
            st.error(f"Error extracting transcript: {e}")

# 4. Processing Engine
if is_unlocked and raw_text and api_key:
    if st.button("⚡ Generate Integrated Notes, Audio Script, & Deep MCQs"):
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        is_bilingual = "Bilingual" in folder
        lang_instruction = "Produce output in Bilingual Format (English & Telugu)." if is_bilingual else "Produce output in Pure English."
        
        notes_prompt = f"""
        You are an expert exam strategist for MPhil Clinical Psychology & Telangana DyEO exams.
        Synthesize the material into Integrated Revision Notes.
        Language Constraint: {lang_instruction}
        
        Structure:
        - Core Concepts & Diagnostic Criteria / Policy Facts
        - Key Theories & Practical Applications
        - Audio Podcast Script (for conversational listening revision)
        
        Material:
        {raw_text[:12000]}
        """
        
        mcq_prompt = f"""
        Generate 5 high-yield exam level MCQs (60% Hard Case Scenarios, 30% Medium, 10% Easy).
        Language Constraint: {lang_instruction}
        
        Provide strict JSON array response in this format:
        [
          {{
            "id": 1,
            "question": "Question text...",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_option": "Option A",
            "topic_tag": "Topic Heading",
            "deep_rationale": "Detailed explanation why correct...",
            "wrong_options_analysis": {{
               "Option B": "Why wrong & relation to other concept",
               "Option C": "Why wrong & relation to other concept",
               "Option D": "Why wrong & relation to other concept"
            }}
          }}
        ]
        
        Material:
        {raw_text[:10000]}
        """
        
        with st.spinner("Processing Integrated Notes & Audio Script..."):
            res_notes = model.generate_content(notes_prompt)
            st.session_state["active_notes"] = res_notes.text

        with st.spinner("Generating Hard Exam MCQs with 4-Option Analysis..."):
            res_mcq = model.generate_content(mcq_prompt)
            try:
                clean_json = res_mcq.text.replace("```json", "").replace("```", "").strip()
                st.session_state["active_mcqs"] = json.loads(clean_json)
                st.session_state["quiz_submitted"] = False
            except Exception as e:
                st.warning("MCQ generation format error. Retry clicking generate.")

# 5. Output Tabs & Display Logic
if st.session_state["active_notes"]:
    out_tab1, out_tab2, out_tab3 = st.tabs(["📖 Integrated Notes", "🎧 Audio Series Player", "🎮 Real Exam Test & Explanations"])
    
    with out_tab1:
        st.markdown(st.session_state["active_notes"])
        st.divider()
        st.subheader("📥 Download Integrated Notes")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            docx_data = create_docx(f"Notes - Ch {chapter_num}", st.session_state["active_notes"])
            st.download_button(
                label="📄 Download Notes as DOCX",
                data=docx_data,
                file_name=f"Notes_Ch_{chapter_num}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        with col_d2:
            pdf_data = create_pdf(f"Notes - Ch {chapter_num}", st.session_state["active_notes"])
            st.download_button(
                label="📕 Download Notes as PDF",
                data=pdf_data,
                file_name=f"Notes_Ch_{chapter_num}.pdf",
                mime="application/pdf"
            )
        
    with out_tab2:
        st.subheader("🎙️ Audio Revision Player")
        st.write("Listen to the synthesized summary on-the-go for subconscious memory retention.")
        if st.button("🔊 Play / Generate Audio File"):
            with st.spinner("Creating audio file..."):
                clean_text = st.session_state["active_notes"][:3000].replace("*", "").replace("#", "")
                tts = gTTS(text=clean_text, lang='en' if "Pure English" in folder else 'te', slow=False)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    tts.save(fp.name)
                    st.audio(fp.name, format="audio/mp3")

    with out_tab3:
        st.subheader("🎯 Real Exam Practice & Deep Explanations")
        st.write("Pass with **>= 70%** to unlock the next chapter!")
        
        mcqs = st.session_state["active_mcqs"]
        if mcqs:
            with st.form("exam_quiz_form"):
                user_answers = {}
                for q in mcqs:
                    st.markdown(f"**Q{q['id']}: {q['question']}**")
                    user_answers[q['id']] = st.radio(f"Select option for Q{q['id']}", q["options"], key=f"q_{q['id']}")
                    st.divider()
                
                submit_btn = st.form_submit_button("Submit Exam & Check Score")
                
                if submit_btn:
                    st.session_state["quiz_submitted"] = True

            if st.session_state["quiz_submitted"]:
                correct_count = 0
                total_q = len(mcqs)
                
                st.markdown("### 📊 Test Analysis & Detailed Explanations")
                
                for q in mcqs:
                    user_ans = user_answers.get(q['id'])
                    is_correct = user_ans == q['correct_option']
                    if is_correct:
                        correct_count += 1
                        st.success(f"✅ Q{q['id']}: Correct! Selected: {user_ans}")
                    else:
                        st.error(f"❌ Q{q['id']}: Incorrect! Selected: {user_ans} | Correct Option: {q['correct_option']}")
                    
                    st.markdown(f"**💡 Why {q['correct_option']} is Correct:**\n{q['deep_rationale']}")
                    
                    st.markdown("**🔍 Distractor Analysis (Why rest of the options are wrong):**")
                    for opt, reason in q['wrong_options_analysis'].items():
                        st.caption(f"• **{opt}:** {reason}")
                    
                    st.divider()

                score_pct = (correct_count / total_q) * 100
                st.metric("Final Score", f"{score_pct:.1f}%")
                
                if score_pct >= 70:
                    st.balloons()
                    st.success(f"🎉 Chapter Cleared! Next chapter unlocked in {folder}.")
                    st.session_state["unlocked_chapters"][folder] = max(
                        st.session_state["unlocked_chapters"].get(folder, 1), chapter_num + 1
                    )
                else:
                    st.warning("Score is below 70%. Please review the notes and retake.")

            # Download Option for MCQs
            st.divider()
            st.subheader("📥 Download Generated MCQs & Rationales")
            mcq_text_content = format_mcqs_as_text(mcqs)
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                mcq_docx = create_docx(f"MCQs - Ch {chapter_num}", mcq_text_content)
                st.download_button(
                    label="📄 Download MCQs as DOCX",
                    data=mcq_docx,
                    file_name=f"MCQs_Ch_{chapter_num}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            with col_m2:
                mcq_pdf = create_pdf(f"MCQs - Ch {chapter_num}", mcq_text_content)
                st.download_button(
                    label="📕 Download MCQs as PDF",
                    data=mcq_pdf,
                    file_name=f"MCQs_Ch_{chapter_num}.pdf",
                    mime="application/pdf"
                )

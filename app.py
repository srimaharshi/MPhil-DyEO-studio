import streamlit as st
import google.generativeai as genai
import pypdf
import io
import docx
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import time
import json

st.set_page_config(page_title="MPhil & DyEO Target Studio", layout="wide", page_icon="🎓")

# Sidebar Configuration
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

# CHAPTER & SUB-TOPIC NAMES INTEGRATION
st.sidebar.subheader("📌 Syllabus Unit & Sub-topic Setup")
module_title = st.sidebar.text_input("Chapter / Unit Name:", value="Unit 1: Neurodevelopmental Disorders")
subtopic_title = st.sidebar.text_input("Sub-topic Name (Optional):", value="Autism Spectrum Disorder (ASD)")

st.title(f"🎓 Workspace: {category}")
st.subheader(f"📖 Current Focus: {module_title} 👉 {subtopic_title}")

# Tabs Navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "📚 Exhaustive Syllabus Notes", 
    "📄 PYQ Repository Vault", 
    "🎯 Interactive CBT Mock Test", 
    "🎮 Topic-wise Practice Engine"
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

# TAB 1: EXHAUSTIVE NOTES
with tab1:
    st.header("📖 Line-by-Line Exhaustive Topic Notes")
    st.caption("Includes Diagnostic Criteria, Etiology, Cut-offs & Differential Diagnosis Matrix.")
    
    # Auto-fill from Sidebar selection or allow custom override
    target_topic = st.text_input("Target Topic / Sub-topic for Notes:", value=f"{module_title} - {subtopic_title}")
    uploaded_files = st.file_uploader("Upload Reference PDFs (Optional)", type=["pdf"], accept_multiple_files=True)
    
    if st.button("⚡ Generate Line-by-Line Deep Notes"):
        if not api_key:
            st.error("Please enter Gemini API Key in Sidebar!")
        else:
            with st.spinner("Synthesizing exhaustive notes and differential matrix..."):
                model = genai.GenerativeModel('gemini-1.5-pro')
                raw_text = extract_pdf_text(uploaded_files) if uploaded_files else ""
                
                prompt = f"""
                Act as a Senior Clinical Psychologist & DyEO Exam Expert.
                Target Category: {category}
                Chapter/Unit: {module_title}
                Target Sub-topic: {target_topic}
                Reference Text: {raw_text[:20000]}
                
                STRICT INSTRUCTIONS:
                1. DO NOT PROVIDE SUMMARIES OR SHORT OVERVIEWS.
                2. Provide line-by-line exhaustive detail required for high-difficulty entrance MCQs.
                3. Cover diagnostic criteria (DSM-5-TR / ICD-11), etiology, neurobiology, psychometrics, and interventions.
                4. Include a dedicated "Differential Diagnosis Matrix Table" comparing closely related conditions to prevent exam traps.
                5. If bilingual category is selected, provide output in clear Telugu and English line-by-line format.
                """
                res = model.generate_content(prompt)
                st.session_state['current_notes'] = res.text
                st.markdown("### 📝 Detailed Notes & Differential Matrix")
                st.write(res.text)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("📥 Download PDF Notes", data=create_pdf(res.text), file_name=f"{subtopic_title}_Notes.pdf", mime="application/pdf")
                with col2:
                    st.download_button("📥 Download DOCX Notes", data=create_docx(res.text), file_name=f"{subtopic_title}_Notes.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# TAB 2: PYQ REPOSITORY
with tab2:
    st.header("📄 University Past Year Question (PYQ) Vault")
    st.caption("Upload RINPAS, IBHAS, CIP, NIMHANS, or TSPSC Papers to calibrate exam style.")
    
    uploaded_pyqs = st.file_uploader("Upload Question Papers (PDF):", type=["pdf"], accept_multiple_files=True, key="pyq_vault")
    if uploaded_pyqs:
        st.session_state['vault_pyq_text'] = extract_pdf_text(uploaded_pyqs)
        st.success(f"Successfully stored {len(uploaded_pyqs)} PYQ files for Mock Test Calibration!")

# TAB 3: INTERACTIVE CBT MOCK TEST
with tab3:
    st.header("🎯 Interactive CBT Real-Time Timed Mock Test")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        num_q = st.slider("Select Question Count:", 5, 50, 10)
    with col2:
        test_mode = st.selectbox("Exam Strategy:", ["University PYQ Pattern (RINPAS/IBHAS/CIP)", "Integrated Syllabus Full-Length Mock"])
    with col3:
        enable_neg_marking = st.checkbox("Enable Negative Marking (-0.25)", value=True)
        
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        start_test = st.button("🚀 Start CBT Live Exam")
    with btn_col2:
        regen_test = st.button("🔄 Generate Next Set of Fresh MCQs")

    if start_test or regen_test:
        if not api_key:
            st.error("Please enter Gemini API Key!")
        else:
            with st.spinner("Compiling Interactive CBT Test Paper..."):
                model = genai.GenerativeModel('gemini-1.5-pro')
                pyq_ref = st.session_state.get('vault_pyq_text', '')[:15000]
                
                prompt = f"""
                Generate {num_q} high-yield MCQs for {category}.
                Active Unit: {module_title}
                Active Sub-topic: {subtopic_title}
                Strategy: {test_mode}
                PYQ Style Reference: {pyq_ref}
                
                Output MUST be valid JSON format only like this:
                [
                  {{
                    "id": 1,
                    "question": "Question text here...",
                    "options": ["A) Opt 1", "B) Opt 2", "C) Opt 3", "D) Opt 4"],
                    "answer": "A) Opt 1",
                    "rationale": "Detailed explanation here...",
                    "subtopic": "{subtopic_title}"
                  }}
                ]
                Do not add markdown backticks like ```json. Pure JSON array only.
                """
                try:
                    res = model.generate_content(prompt)
                    clean_json = res.text.replace("```json", "").replace("```", "").strip()
                    st.session_state['cbt_questions'] = json.loads(clean_json)
                    st.session_state['start_time'] = time.time()
                    st.session_state['duration'] = num_q * 60
                    st.session_state['user_answers'] = {}
                    st.experimental_rerun()
                except Exception as e:
                    st.error("Formatting error, please click 'Generate Next Set' again.")

    if 'cbt_questions' in st.session_state:
        elapsed = int(time.time() - st.session_state['start_time'])
        rem = st.session_state['duration'] - elapsed
        
        if rem > 0:
            st.warning(f"⏳ CBT Live Timer: {rem // 60} Min {rem % 60} Sec Remaining")
        else:
            st.error("⏰ TIME EXPIRED! Please submit your answers for evaluation.")

        with st.form("cbt_form"):
            for idx, q in enumerate(st.session_state['cbt_questions']):
                st.markdown(f"**Q{idx+1}: {q['question']}**")
                st.session_state['user_answers'][idx] = st.radio(
                    "Select Answer:", q['options'], key=f"cbt_q_{idx}"
                )
                st.divider()
            
            submitted = st.form_submit_button("📊 Submit Test & Calculate Results")
            
            if submitted:
                score = 0.0
                correct_cnt = 0
                wrong_cnt = 0
                weak_topics = []
                
                st.markdown("## 📈 Performance & Results Dashboard")
                for idx, q in enumerate(st.session_state['cbt_questions']):
                    user_ans = st.session_state['user_answers'].get(idx)
                    if user_ans == q['answer']:
                        score += 1.0
                        correct_cnt += 1
                        st.success(f"Q{idx+1}: Correct! Selected: {user_ans}")
                    else:
                        wrong_cnt += 1
                        if enable_neg_marking:
                            score -= 0.25
                        st.error(f"Q{idx+1}: Incorrect! Selected: {user_ans} | Correct Answer: {q['answer']}")
                        if 'subtopic' in q:
                            weak_topics.append(q['subtopic'])
                    st.info(f"💡 Rationale: {q['rationale']}")
                
                total_qs = len(st.session_state['cbt_questions'])
                max_score = float(total_qs)
                percentage = (score / max_score) * 100
                
                st.metric(label="Final Exam Score", value=f"{score:.2f} / {total_qs}", delta=f"{percentage:.1f}%")
                st.write(f"✅ Correct Answers: {correct_cnt} | ❌ Wrong Answers: {wrong_cnt}")
                
                if weak_topics:
                    st.warning(f"⚠️ **Topics to Re-visit & Revision:** {', '.join(set(weak_topics))}")

# TAB 4: TOPIC-WISE PRACTICE ENGINE
with tab4:
    st.header("🎮 Topic-wide Complete Practice Engine")
    practice_topic = st.text_input("Enter Topic / Sub-topic Name:", value=f"{module_title} - {subtopic_title}")
    practice_count = st.slider("Select Practice MCQ Count:", 5, 30, 15)
    
    if st.button("⚡ Generate Complete Topic MCQs"):
        if not api_key:
            st.error("Please enter Gemini API Key!")
        else:
            with st.spinner("Generating sub-topic aligned practice questions..."):
                model = genai.GenerativeModel('gemini-1.5-pro')
                prompt = f"""
                Generate {practice_count} detailed MCQs covering ALL sub-topics of '{practice_topic}' for {category}.
                Ensure complete coverage of diagnostic criteria, etiology, psychometrics, and treatment.
                Provide question, options, correct answer, and detailed distractor rationale for each question.
                """
                res = model.generate_content(prompt)
                st.write(res.text)

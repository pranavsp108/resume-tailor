import streamlit as st
import google.generativeai as genai

# --- 1. CONFIG & SECRETS ---
st.set_page_config(page_title="Resume Tailor Pro", layout="wide", page_icon="🎯")

# Pulls from Streamlit Cloud Secrets (Advanced Settings)
# Fallback to sidebar input if secrets aren't set up yet
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Enter Gemini API Key:", type="password")

# Pulls your base LaTeX from secrets to keep this file light
# Fallback to a placeholder if not found
base_resume = st.secrets.get("MY_RESUME_LATEX", "% Paste your base LaTeX here or add to Secrets")

st.title("🎯 Strategic Resume Tailor")
st.markdown("---")

# --- 2. USER INTERFACE ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Base Resume (LaTeX)")
    resume_text = st.text_area("Edit your base code if needed:", value=base_resume, height=500)

with col2:
    st.subheader("Target Job Description")
    jd_text = st.text_area("Paste the JD here:", height=500, placeholder="Copy the full job posting text...")

# --- 3. THE LOGIC ---
if st.button("🔥 Analyze & Tailor for this Role"):
    if not api_key:
        st.error("Missing API Key. Please add it to Streamlit Secrets or the sidebar.")
    elif not jd_text:
        st.warning("Please paste a Job Description first.")
    else:
        with st.spinner("🧠 Senior Recruiter is analyzing the JD and pivoting your resume..."):
            try:
                genai.configure(api_key=api_key)
                # Using 3.1 Pro for high-level strategic reasoning
                model = genai.GenerativeModel('gemini-3.1-pro-preview')

                prompt = rf"""
                You are a Senior Career Coach and Expert Technical Recruiter specializing in Data Science, Machine Learning, and Analytics.
                Your goal is to strategically rewrite the candidate's LaTeX resume bullets and skills section so they closely align with the provided Job Description (JD) while maintaining absolute truthfulness to their core experience.

                CONTEXT FOR THE CANDIDATE:
                - Currently a Master's in Data Science student at the University of Minnesota (with a Minor in Business Management).
                - Professional Experience: Data Science Intern at Daikin Applied Americas, Data Analyst at TCS (client: Pandora), and Graduate Teaching Assistant for Statistics & AI.
                - Technical Stack: Python, Advanced SQL, PySpark, AWS, Azure, and modern ML frameworks (Scikit-learn, PyTorch, Hugging Face).
                - Academic Background: Bachelor's in Mechanical Engineering.

                STRICT TAILORING STRATEGY & OUTPUT FORMAT:
                1. PURE CODE OUTPUT: Your entire response should be formatted as a single LaTeX code block. Do not include conversational text outside the code block.
                2. FIT ASSESSMENT: The very first line of your output must be a LaTeX comment containing the Match Score and a brief summary of the fit.
                   Format: % Match Assessment: [Score]/10 - [Brief summary of fit and gaps]
                3. STRATEGIC PIVOTING & BULLETS: For every bullet point you change, you must use the following strict 4-line structure:
                   Line 1: % Section: [Education, Work Experience, Skills, or Projects]
                   Line 2: % Subsection: [e.g., TCS, Daikin, U of M, GlobalMarket AI, End-to-End Recommender System]
                   Line 3: % Bullet: [e.g., 1st bullet] - [Explain exactly WHY you are changing it based on the JD]
                   Line 4: \item [The rewritten LaTeX code with keywords in \textbf{{}}]
                4. TERMINOLOGY SWAP & METRICS: Ensure every tweaked bullet point includes a metric (%, $, or time) if the original had one. Swap base terms for JD-specific keywords.
                5. IMPLICIT NEEDS ANALYSIS: Analyze the JD for implicit requirements (things they don't say but probably want, like 'attention to detail' for a Finance-adjacent role or 'cross-functional collaboration' for enterprise teams) and weave those soft skills or secondary technical traits into the experience points.
                6. SKILLS SECTION OPTIMIZATION: You MUST maintain the EXACT SAME NUMBER of skills per subsection as the base resume. If you add a required JD skill, you must remove the least relevant base skill to maintain the count. Format each skills line exactly like this:
                   \textbf{{Subsection Title}} & Skill 1, Skill 2, Skill 3, .... \\[1 pt]
                7. HALLUCINATION GUARD: You may reframe, emphasize, or shift the focus of a task, but you may NOT invent new job titles, new companies, fake metrics, or unearned degrees.

                Resume LaTeX:
                {resume_text}

                Job Description:
                {jd_text}
                """

                response = model.generate_content(prompt)
                
                st.subheader("🚀 Your Tailored LaTeX Updates")
                st.code(response.text, language='latex')
                st.success("Analysis Complete! Copy the snippets above into Overleaf.")
                st.info("💡 The match score is in the top line of the code block above.")

            except Exception as e:
                st.error(f"Error: {e}")

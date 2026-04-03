import streamlit as st
import google.generativeai as genai

# --- 1. CONFIG & SECRETS ---
st.set_page_config(page_title="Resume Tailor Pro", layout="wide", page_icon="🎯")

# Pulls from Streamlit Cloud Secrets (Advanced Settings)
# Fallback to sidebar input if secrets aren't set up yet
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Enter Gemini API Key:", type="password")

# Pulls your base LaTeX from secrets to keep this file light
# Fallback to a placeholder if not found
# Line 13
base_resume = r"""
%% Pranav Padmannavar — Resume LaTeX Source
%% Font: Computer Modern (LaTeX default), sizes scaled down slightly

\documentclass[10pt,letterpaper]{article}

% ---------- Packages ----------
\usepackage[
  top=0.4in, bottom=0.4in,
  left=0.6in, right=0.6in
]{geometry}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{hyperref}
\usepackage{microtype}
\usepackage{array}
\usepackage{tabularx}

% Suppress parskip — we control all spacing manually
\setlength{\parskip}{0pt}
\setlength{\parindent}{0pt}

% ---------- Hyperlink styling ----------
\hypersetup{
  colorlinks=true,
  urlcolor=black,
  linkcolor=black
}

% ---------- No page numbers ----------
\pagestyle{empty}

% ---------- Section formatting ----------
\titleformat{\section}
  {\normalfont\normalsize\bfseries}
  {}{0em}{}
  [\vspace{-9pt}\rule{\linewidth}{0.4pt}]
\titlespacing{\section}{0pt}{4pt}{0pt}

% ---------- List settings ----------
\setlist[itemize]{
  leftmargin=1.2em,
  topsep=1pt,
  itemsep=0pt,
  parsep=0pt,
  partopsep=0pt,
  label=\textbullet
}

% ---------- Custom commands ----------
\newcommand{\roleonly}[2]{%
  \noindent
  \begin{tabularx}{\linewidth}{@{}X r@{}}
    \textit{#1} & \textit{#2}
  \end{tabularx}\vspace{0pt}%
}

\newcommand{\projectheader}[2]{%
  \noindent
  \begin{tabularx}{\linewidth}{@{}X r@{}}
    \textbf{#1} & \textit{#2}
  \end{tabularx}\vspace{0pt}%
}

% Separator between entries
\newcommand{\entrysep}{\vspace{2pt}}

% ======================================================
\begin{document}
% ======================================================

% ---------- Header ----------
\begin{center}
  {\large\textbf{Pranav Padmannavar}} \\[2pt]
  \small
    Minneapolis, MN \ $|$ \ (763)-900-3044 \ $|$ \ 
    \href{mailto:padma062@umn.edu}{padma062@umn.edu} \ $|$ \ 
    \href{https://www.linkedin.com/in/pranavpadmannavar/}{LinkedIn} \ $|$ \ 
    \href{https://github.com/pranavsp108}{github} \ $|$ \ 
    \href{https://pranavsp108.github.io/}{Portfolio}
\end{center}

\vspace{1pt}

% ---------- Education ----------
\section{EDUCATION}
\noindent
\begin{tabularx}{\linewidth}{@{}X r@{}}
  \textbf{University of Minnesota Twin Cities} & \textit{Sep 2024 -- May 2026 } \\[-1pt]
  Master of Science in Data Science \;|\; Minor in Business Management & 3.7 / 4.0
\end{tabularx}
\vspace{1pt}
\noindent
\begin{tabularx}{\linewidth}{@{}X r@{}}
  \textbf{Visvesvaraya Technological University} & \textit{Sep 2017 -- May 2021 } \\[-1pt]
  Bachelor of Engineering in Mechanical Engineering & 3.4 / 4.0
\end{tabularx}

% ---------- Work Experience ----------
\section{WORK EXPERIENCE}
% --- Daikin ---
\noindent \begin{tabularx}{\linewidth}{@{} X r@{} }
{\fontsize{11pt}{13pt}\selectfont \textbf{Daikin Applied Americas} } & \textit{Minneapolis, U.S.}
\end{tabularx}\vspace{-2pt}
\roleonly{Data Science and Optimization Intern}{Aug 2025 -- Dec 2025 }
\begin{itemize}
  \item Identified \textbf{\$1.5M+ in annual manufacturing cost savings} (4-5\% reduction per unit) by automating the analysis of 2,000+ design parameters and recommending optimal material configurations.
  \item Engineered a \textbf{predictive optimization framework (LightGBM, Scikit-learn)} for flagship HVAC lines, accelerating simulation runtime by \textbf{90\%} (reducing compute time from hours to minutes).
  \item Saved \textbf{1,000+ engineering hours} annually (~\$150k productivity) by enabling rapid validation of complex thermal scenarios and significantly shortening the \textbf{R\&D feedback loop}.
\end{itemize}

\entrysep

% --- TCS ---
\noindent \begin{tabularx}{\linewidth}{@{} X r@{} }
{\fontsize{11pt}{13pt}\selectfont \textbf{Tata Consultancy Services} $|$ \textit{Client: Pandora}} & \textit{Bangalore, India} 
\end{tabularx}\vspace{-2pt}
\roleonly{Data Analyst }{Feb 2022 -- Jul 2024 }
\begin{itemize}
  \item Automated 30+ mission-critical \textbf{Python}-based reports for \textbf{global retail operations} (\$4.5B revenue), eliminating 1,000+ manual hours and accelerating \textbf{strategic decision-making}.
  \item Orchestrated the migration of legacy BizTalk workflows to Azure (Logic Apps, Functions) , reducing data processing workloads by 35\% and slashing operational latency by 20\%.
  \item Optimized high-volume \textbf{SQL queries} on multi-terabyte \textbf{Big Data} sets, slashing \textbf{dashboard} response times by 40\% for 50+ \textbf{business stakeholders}.
  \item Fortified \textbf{data integrity} by implementing automated \textbf{validation scripts}, improving \textbf{data accuracy} by 15\% and mitigating \$50k+ in annual revenue leakage.
  \item Developed a suite of \textbf{Power BI} dashboards for Pandora's executive leadership , translating complex \textbf{ETL} outputs into actionable insights that identified a \textbf{12\% growth opportunity} in underperforming regional markets.
\end{itemize}
\entrysep

% --- UMN Teaching Assistant ---
\noindent \begin{tabularx}{\linewidth}{@{} X r@{} }
{\fontsize{11pt}{13pt}\selectfont \textbf{University of Minnesota}} & \textit{Minneapolis, U.S.} 
\end{tabularx}\vspace{-2pt}
\roleonly{Graduate Teaching Assistant \ $|$ \; Statistics \& AI Hub}{Jan 2025 -- Present }
\begin{itemize}
  \item Directed 230+ students and 20+ teams through end-to-end \textbf{AI capstones} and \textbf{statistical modeling}, achieving a \textbf{100\% project completion rate}.
  \item Co-designed assessments and provided technical consultation on \textbf{Python, R}, and \textbf{Responsible AI} principles for undergraduate and graduate cohorts.
\end{itemize}

% ---------- Skills ----------
\section{SKILLS}
\noindent
\begin{tabularx}{\linewidth}{@{}lX@{}}
  \textbf{Languages:} & Python, Advanced SQL, R, Bash, Git \\[1pt]
  \textbf{ML \& Frameworks:} & Pandas, NumPy, Scikit-learn, PyTorch, TensorFlow, Hugging Face, XGBoost, LightGBM \\[1pt]
  \textbf{Statistics \& Modeling:} & A/B Testing, Hypothesis Testing, Causal Inference, Time-Series, Statistical Modeling, LSTM \\[1pt]
  \textbf{Big Data \& MLOps:} & PySpark, Databricks, Airflow, Kafka, MLflow, Docker, Kubernetes, CI/CD, Github Actions \\[1pt]
  \textbf{Databases \& Cloud:} & Azure, AWS (S3, EC2, SageMaker), GCP (BigQuery, Vertex AI), PostgreSQL, MySQL \\[1pt]
  \textbf{Data Visualization:} & Tableau, Power BI, Data Storytelling \\
\end{tabularx}

% ---------- Academic Project Experience ----------
\section{ACADEMIC PROJECT EXPERIENCE}

% --- GlobalMarket AI ---
\projectheader{\href{\detokenize{https://github.com/pranavsp108/stock-market-pipeline}}{{\fontsize{11pt}{13pt}\selectfont GlobalMarket AI: Autonomous MLOps Pipeline for Predictive Finance}}}{Jan 2026 -- Mar 2026}
\begin{itemize}
  \item Engineered an automated pipeline using \textbf{Kafka} and \textbf{GitHub Actions} to ingest 26+ years of market data into an \textbf{S3-backed Data Lake}.
  \item Developed a stacked \textbf{LSTM Neural Network (TensorFlow)} on \textbf{AWS EC2}, utilizing a "zero-touch" \textbf{MLOps} workflow for daily model retraining.
\end{itemize}

\entrysep

% --- Recommender System ---
\projectheader{End-to-End Recommender System}{Jun 2025 -- Aug 2025 }
\begin{itemize}
  \item Engineered a \textbf{PySpark} data pipeline and trained a \textbf{Scikit-learn} collaborative filtering model, increasing user engagement by \textbf{25\%}.
  \item Deployed the model as a containerized \textbf{(Docker) REST API} on \textbf{Azure} to serve real-time predictions.
\end{itemize}

\entrysep

% --- Demand Forecasting ---
\projectheader{Demand Forecasting \& Inventory Optimization}{Aug 2024 -- Dec 2024 }
\begin{itemize}
  \item Developed \textbf{time-series forecasting} models that projected a \textbf{15\% reduction in inventory costs} and improved order fulfillment rates by \textbf{28\%}.
\end{itemize}

% ======================================================
\end{document}
"""

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

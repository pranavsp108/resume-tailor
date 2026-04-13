import streamlit as st
import google.generativeai as genai
import openai
import json
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# --- 1. CONFIG & SECRETS ---
st.set_page_config(page_title="Pranav's Resume Tailor", layout="wide", page_icon="🎯")
st.caption("v4.0 - efficient multi-step tailoring + job tracker")

api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Enter Gemini API Key:", type="password")
openai_key = st.secrets.get("OPENAI_API_KEY") or st.sidebar.text_input("Enter OpenAI API Key:", type="password")

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Strategy Level")
strategy_mode = st.sidebar.radio(
    "Select Priority:",
    ["Daily Driver (GPT-4o-mini)", "Dream Job (Gemini 3.1 Pro)"],
    index=0,
    help="Use GPT-4o-mini for cost-efficient daily tailoring. Use Gemini only for high-stakes roles."
)

# Optional premium pass, off by default to save cost
st.sidebar.markdown("---")
enable_critique = st.sidebar.checkbox(
    "Add premium critique pass",
    value=False,
    help="Runs one extra cheap scoring pass after tailoring. Leave off to minimize cost."
)

# Pulls your base LaTeX from secrets to keep this file light
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
    \href{mailto:pranavsp108@gmail.com}{pranavsp108@gmail.com} \ $|$ \ 
    \href{https://www.linkedin.com/in/pranavsp108/}{LinkedIn} \ $|$ \ 
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

# --- 1B. GOOGLE SHEETS HELPERS ---
def get_gsheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(st.secrets["GOOGLE_SHEET_ID"])
    worksheet = spreadsheet.sheet1
    return worksheet


def initialize_sheet_headers(sheet):
    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row([
            "Application Date",
            "Role Title",
            "Company",
            "Location",
            "Experience Level",
            "Tools Needed",
            "Match Score",
            "Role Domain",
            "Top Keywords",
            "Job Description"
        ])


def save_job_to_gsheet(job_data, jd_text, match_score=""):
    try:
        sheet = get_gsheet()
        initialize_sheet_headers(sheet)

        row = [
            datetime.today().strftime("%Y-%m-%d"),
            str(job_data.get("role_title", "")),
            str(job_data.get("company", "")),
            str(job_data.get("location", "")),
            str(job_data.get("experience_years", "")),
            ", ".join([str(x) for x in job_data.get("tools", [])]),
            str(match_score),
            str(job_data.get("role_domain", "")),
            ", ".join([str(x) for x in job_data.get("top_keywords", [])]),
            str(jd_text)
        ]

        return sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        raise RuntimeError(f"Google Sheets save failed: {type(e).__name__}: {e}")


def fetch_saved_jobs():
    sheet = get_gsheet()
    records = sheet.get_all_records()
    return pd.DataFrame(records)


# --- 2. LIGHTWEIGHT HELPERS ---
def clean_code_fence(text: str) -> str:
    return text.replace("```latex", "").replace("```json", "").replace("```", "").strip()


def extract_json_from_response(text: str):
    text = text.strip()

    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    match = re.search(r"```\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    raise ValueError("No valid JSON object found in model response.")


def infer_header_location(job_location: str) -> str:
    location = (job_location or "").lower()
    mapping = {
        "california": "Dublin, CA",
        "ca": "Dublin, CA",
        "washington": "Seattle, WA",
        "wa": "Seattle, WA",
        "texas": "Dallas, TX",
        "tx": "Dallas, TX",
        "georgia": "Atlanta, GA",
        "ga": "Atlanta, GA",
        "north carolina": "High Point, NC",
        "nc": "High Point, NC",
    }
    for key, value in mapping.items():
        if key in location:
            return value
    return "Minneapolis, MN"


def infer_degree_title(role_domain: str, jd_text: str) -> str:
    domain = (role_domain or "").lower()
    jd_lower = (jd_text or "").lower()

    if any(term in domain for term in ["operations research", "optimization", "industrial", "supply chain"]):
        return "Master of Science in Industrial Engineering"
    if any(term in domain for term in ["marketing analytics", "product analytics", "business intelligence", "analytics", "data analyst"]):
        return "Master of Science in Analytics"
    if any(term in domain for term in ["machine learning", "data science", "ai", "nlp"]):
        return "Master of Science in Data Science"

    if any(term in jd_lower for term in ["machine learning", "artificial intelligence", "predictive", "nlp"]):
        return "Master of Science in Data Science"
    if any(term in jd_lower for term in ["operations research", "optimization", "industrial engineering", "supply chain"]):
        return "Master of Science in Industrial Engineering"
    return "Master of Science in Analytics"


def get_openai_client():
    if not openai_key:
        raise ValueError("Missing OpenAI API key.")
    return openai.OpenAI(api_key=openai_key)


def get_jd_intelligence(jd_text: str) -> dict:
    """
    One cheap structured pass reused for:
    - role/domain understanding
    - prompt grounding
    - job tracker extraction
    This replaces the old separate tracker extraction call.
    """
    extraction_prompt = f"""
You are an expert recruiter.
Analyze the job description and return ONLY valid JSON.

Required schema:
{{
  "role_title": "",
  "company": "",
  "location": "",
  "experience_years": "",
  "tools": [],
  "role_domain": "",
  "top_keywords": [],
  "top_responsibilities": [],
  "top_business_skills": []
}}

Rules:
- role_title: exact or closest title.
- company: employer name if available.
- location: city/state/remote/hybrid if available.
- experience_years: concise string like "0-2 years", "2+ years", "3-5 years".
- tools: max 10 normalized tools/technologies.
- role_domain: choose the single best fit such as Marketing Analytics, Product Analytics, Business Intelligence, Data Science, Machine Learning, Data Engineering, Operations Research, General Analytics.
- top_keywords: max 10 ATS keywords actually important for fit.
- top_responsibilities: max 5 action-oriented responsibilities.
- top_business_skills: max 4 business or soft skills.
- Return JSON only.

Job Description:
{jd_text}
"""
    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You extract structured job information accurately and concisely."},
            {"role": "user", "content": extraction_prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)


def build_daily_driver_prompt(resume_text: str, jd_text: str, jd_info: dict, header_location: str, degree_title: str) -> str:
    return rf"""
You are a precise resume tailoring assistant for analytics and data roles.

Your task is to tailor the LaTeX resume for the job description using the structured JD summary below.
Be efficient, truthful, and selective. Improve only lines that materially increase fit.

CANDIDATE FACTS YOU MUST RESPECT:
- University of Minnesota graduate program is truthfully closest to one of: Master of Science in Industrial Engineering, Master of Science in Analytics, or Master of Science in Data Science.
- Do not invent titles, companies, metrics, locations, tools, projects, or degrees.
- Preserve existing metrics if they already exist.
- Keep the overall one-page LaTeX structure intact.

DETERMINISTIC SETTINGS ALREADY CHOSEN:
- Header location to use: {header_location}
- Education title to use: {degree_title}

STRUCTURED JD SUMMARY:
- Role title: {jd_info.get('role_title', '')}
- Company: {jd_info.get('company', '')}
- Location: {jd_info.get('location', '')}
- Role domain: {jd_info.get('role_domain', '')}
- Top keywords: {', '.join(jd_info.get('top_keywords', []))}
- Top responsibilities: {' | '.join(jd_info.get('top_responsibilities', []))}
- Top business skills: {', '.join(jd_info.get('top_business_skills', []))}
- Important tools: {', '.join(jd_info.get('tools', []))}

DOMAIN GUIDANCE:
- If the role domain is Marketing Analytics, emphasize customer behavior, segmentation, campaign or channel insights, business intelligence, dashboards, and stakeholder decision support.
- If the role domain is Business Intelligence or General Analytics, emphasize SQL, dashboards, KPIs, reporting, business partnership, and decision support.
- If the role domain is Data Science or Machine Learning, emphasize modeling, experimentation, prediction, and technical depth.
- If the role domain is Data Engineering, emphasize pipelines, warehousing, reliability, and scale.

BULLET REWRITE RULE:
Every rewritten bullet should follow this pattern as closely as the original facts allow:
[Action] + [Tool or method] + [business problem or analysis] + [quantified impact] + [JD-aligned outcome]

IMPORTANT STYLE RULES:
- Prefer natural recruiter language over copying long JD phrases.
- Use JD terminology selectively, not mechanically.
- Prioritize the TCS / Pandora bullets first for business-facing analyst roles.
- Reduce unnecessary MLOps emphasis if the role is analyst or BI oriented.
- Maintain the exact same number of skills in each skills subsection.
- If you add a JD-relevant skill, remove a less relevant one from the same subsection.

LATEX RULES:
- Return only the final LaTeX inside a single code block.
- First line must be a LaTeX comment in this format:
  % Match Assessment: [score]/10 - [brief summary]
- Do not add prose outside the code block.
- Keep LaTeX valid. Do not add markdown formatting inside the code.
- Preserve special characters carefully.

BASE RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}
"""


def build_dream_job_prompt(resume_text: str, jd_text: str, jd_info: dict, header_location: str, degree_title: str) -> str:
    return rf"""
You are a Senior Career Coach and Expert Technical Recruiter specializing in Data Science, Machine Learning, Analytics, Product Analytics, and Business Intelligence roles.
Your job is to strategically tailor the candidate's LaTeX resume so it aligns closely with the job description while staying fully truthful to the candidate's real experience.

CANDIDATE CONTEXT:
- University of Minnesota graduate program should be represented truthfully using this chosen title: {degree_title}
- Professional experience includes Daikin Applied Americas, Tata Consultancy Services (client: Pandora), and University of Minnesota teaching work.
- Technical stack includes Python, SQL, R, PySpark, AWS, Azure, analytics, dashboards, and modern ML frameworks.
- Header location has already been chosen and must be used exactly as: {header_location}

STRUCTURED JD INTELLIGENCE:
{json.dumps(jd_info, indent=2)}

TAILORING GOALS:
1. Improve ATS keyword coverage.
2. Improve responsibility alignment.
3. Improve domain alignment for the role domain: {jd_info.get('role_domain', '')}.
4. Keep the output natural and recruiter-believable.
5. Avoid obvious copy-paste phrasing from the JD.

REWRITE STRATEGY:
- Rewrite only where useful; keep strong original bullets when they already fit.
- Prioritize the most relevant bullets and skills first.
- Keep metrics whenever they already exist.
- Use this bullet formula where possible:
  [Action] + [Tool/Method] + [Business Problem] + [Quantified Impact] + [JD-aligned outcome]
- If the role is analyst, BI, or marketing-facing, emphasize dashboards, stakeholder partnership, data quality, business insights, and decision support.
- If the role is DS/ML-heavy, emphasize modeling, experimentation, statistical rigor, and predictive impact.
- Keep the exact same number of skills within each skill subsection.

OUTPUT RULES:
- Return the full final LaTeX resume inside a single ```latex code block.
- The first line must be:
  % Match Assessment: [score]/10 - [brief fit summary]
- Do not include commentary outside the code block.
- Keep LaTeX valid.
- Do not invent facts.

BASE RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}
"""


def run_tailoring_model(prompt: str, strategy_mode: str) -> str:
    if strategy_mode == "Daily Driver (GPT-4o-mini)":
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": "You tailor resumes carefully, truthfully, and efficiently."},
                {"role": "user", "content": prompt},
            ],
        )
        return clean_code_fence(response.choices[0].message.content)

    if not api_key:
        raise ValueError("Missing Gemini API key.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.1-pro-preview')
    response = model.generate_content(prompt)
    return clean_code_fence(response.text)


def run_optional_critique(tailored_text: str, jd_info: dict, jd_text: str) -> dict:
    critique_prompt = f"""
You are a recruiter evaluating a tailored resume.
Return ONLY valid JSON in this schema:
{{
  "keyword_match": 0,
  "business_alignment": 0,
  "domain_relevance": 0,
  "overall_score": 0,
  "top_gaps": [],
  "top_improvements": []
}}

Scoring rules:
- Each score is an integer from 1 to 10.
- Keep top_gaps to max 4 items.
- Keep top_improvements to max 3 items.
- Be concise and specific.

JD summary:
{json.dumps(jd_info)}

Job Description:
{jd_text}

Tailored Resume:
{tailored_text}
"""
    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You evaluate resume fit clearly and concisely."},
            {"role": "user", "content": critique_prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)


# --- 3. USER INTERFACE ---
st.title("🎯 Strategic Resume Tailor")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Base Resume (LaTeX)")
    resume_text = st.text_area("Edit your base code if needed:", value=base_resume, height=500)

with col2:
    st.subheader("Target Job Description")
    jd_text = st.text_area("Paste the JD here:", height=500, placeholder="Copy the full job posting text...")

st.markdown("### 📌 Job Tracking")
save_job_only = st.checkbox("Save this JD to Job Tracker after analysis", value=True)
show_tracker = st.checkbox("Show saved job tracker table", value=False)

# --- 4. APP LOGIC ---
if st.button("🔥 Analyze & Tailor for this Role"):
    if strategy_mode == "Daily Driver (GPT-4o-mini)" and not openai_key:
        st.error("Missing OpenAI API key. Please add it to Streamlit Secrets or the sidebar.")
    elif strategy_mode == "Dream Job (Gemini 3.1 Pro)" and not (api_key and openai_key):
        st.error("Dream Job mode uses Gemini for tailoring and GPT-4o-mini for cheap JD extraction. Please provide both API keys.")
    elif not jd_text:
        st.warning("Please paste a Job Description first.")
    else:
        try:
            with st.spinner("Analyzing the JD and building a lean tailoring plan..."):
                jd_info = get_jd_intelligence(jd_text)
                header_location = infer_header_location(jd_info.get("location", ""))
                degree_title = infer_degree_title(jd_info.get("role_domain", ""), jd_text)

            st.subheader("📋 JD Intelligence")
            st.json({
                "role_title": jd_info.get("role_title", ""),
                "company": jd_info.get("company", ""),
                "location": jd_info.get("location", ""),
                "role_domain": jd_info.get("role_domain", ""),
                "top_keywords": jd_info.get("top_keywords", []),
                "top_responsibilities": jd_info.get("top_responsibilities", []),
                "tools": jd_info.get("tools", []),
                "header_location_selected": header_location,
                "degree_title_selected": degree_title,
            })

            with st.spinner("Tailoring the resume..."):
                if strategy_mode == "Daily Driver (GPT-4o-mini)":
                    prompt = build_daily_driver_prompt(
                        resume_text=resume_text,
                        jd_text=jd_text,
                        jd_info=jd_info,
                        header_location=header_location,
                        degree_title=degree_title,
                    )
                else:
                    prompt = build_dream_job_prompt(
                        resume_text=resume_text,
                        jd_text=jd_text,
                        jd_info=jd_info,
                        header_location=header_location,
                        degree_title=degree_title,
                    )

                tailored_text = run_tailoring_model(prompt, strategy_mode)

            st.subheader("🚀 Tailored LaTeX Resume")
            st.code(tailored_text, language='latex')
            st.success("Tailoring complete. Copy the LaTeX into Overleaf.")

            match_score = ""
            score_match = re.search(r"Match Assessment:\s*([0-9.]+/10)", tailored_text)
            if score_match:
                match_score = score_match.group(1)
                st.info(f"Estimated fit from tailoring model: {match_score}")

            if enable_critique:
                with st.spinner("Running one extra critique pass..."):
                    critique = run_optional_critique(tailored_text, jd_info, jd_text)
                st.subheader("🧪 Critique Summary")
                st.json(critique)

            if save_job_only:
                save_job_to_gsheet(jd_info, jd_text, match_score)
                st.success("✅ Job application saved to Google Sheets.")

        except Exception as e:
            st.error(f"Error: {e}")

if show_tracker:
    try:
        tracker_df = fetch_saved_jobs()
        st.subheader("📊 Saved Job Applications")
        st.dataframe(tracker_df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load tracker data: {e}")

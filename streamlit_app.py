import streamlit as st
import google.generativeai as genai
import openai
import json
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from pathlib import Path

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

# --- 1A. BASE RESUME SELECTION ---
RESUME_FILES = {
    "Data Scientist": "Pranav_DS.tex",
    "Data Analyst": "Pranav_DA.tex",
}

resume_profile = st.sidebar.radio(
    "📄 Base Resume",
    ["Data Scientist", "Data Analyst"],
    index=0,
    help="Manually choose the base resume to tailor. This keeps tailoring focused and avoids mixing DS and DA positioning."
)

@st.cache_data(show_spinner=False)
def load_resume_template(resume_profile: str) -> str:
    """
    Loads the selected base LaTeX resume from a local .tex file.
    Keep Pranav_DS.tex and Pranav_DA.tex in the same folder as streamlit_app.py.
    """
    app_dir = Path(__file__).parent
    resume_filename = RESUME_FILES[resume_profile]
    resume_path = app_dir / resume_filename

    if not resume_path.exists():
        raise FileNotFoundError(
            f"Could not find {resume_filename}. Make sure it is in the same folder as streamlit_app.py."
        )

    return resume_path.read_text(encoding="utf-8")

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
    """
    Deterministic resume header location mapping.

    Rules:
    - CA / California -> Dublin, CA
    - WA / Washington State -> Seattle, WA
    - TX / Texas -> Dallas, TX
    - GA / Georgia -> Atlanta, GA
    - NC / North Carolina -> High Point, NC
    - Everything else -> Minneapolis, MN

    Important:
    - Washington, DC should NOT map to Seattle.
    - South Carolina should NOT map to CA or NC.
    - Chicago should NOT map to CA.
    """
    location = (job_location or "").lower()
    location = re.sub(r"[^a-z,\s]", " ", location)
    location = re.sub(r"\s+", " ", location).strip()

    # Explicitly handle DC first so "Washington, DC" does not become Seattle.
    if re.search(r"\b(dc|d c|district of columbia)\b", location):
        return "Minneapolis, MN"

    # Multi-word states first
    if re.search(r"\bnorth\s+carolina\b", location):
        return "High Point, NC"

    # Full state names
    full_state_mapping = {
        "california": "Dublin, CA",
        "texas": "Dallas, TX",
        "georgia": "Atlanta, GA",
    }

    for state, resume_location in full_state_mapping.items():
        if re.search(rf"\b{state}\b", location):
            return resume_location

    # Washington only if it clearly means Washington State
    if re.search(r"\bwashington\s+state\b|\bstate\s+of\s+washington\b", location):
        return "Seattle, WA"

    # State abbreviations as standalone tokens only
    abbrev_mapping = {
        "ca": "Dublin, CA",
        "wa": "Seattle, WA",
        "tx": "Dallas, TX",
        "ga": "Atlanta, GA",
        "nc": "High Point, NC",
    }

    tokens = re.findall(r"\b[a-z]{2}\b", location)
    for token in tokens:
        if token in abbrev_mapping:
            return abbrev_mapping[token]

    return "Minneapolis, MN"

def apply_deterministic_resume_overrides(tailored_text: str, header_location: str, degree_title: str) -> str:
    """
    Hard override final LaTeX output after the model responds.
    This prevents the model from accidentally changing deterministic fields.
    """

    # Force header location before phone number
    tailored_text = re.sub(
        r"(\s*)[A-Za-z .,-]+\\\s*\$\|\$\s*\\\s*\(763\)-900-3044",
        lambda m: f"{m.group(1)}{header_location} \\ $|$ \\ (763)-900-3044",
        tailored_text,
        count=1
    )

    # Force selected education title
    tailored_text = re.sub(
        r"Master of Science in (Data Science|Analytics|Industrial Engineering)\s*\\;\|\\;\s*Minor in Business Management",
        lambda m: f"{degree_title} \\;|\\; Minor in Business Management",
        tailored_text,
        count=1
    )

    return tailored_text

def get_openai_client():
    if not openai_key:
        raise ValueError("Missing OpenAI API key.")
    return openai.OpenAI(api_key=openai_key)


def get_jd_intelligence(jd_text: str) -> dict:
    """
    Cheap structured JD analysis pass.
    Goal: extract only the signals needed for focused resume tailoring.
    Does NOT choose DS vs DA because base resume selection is manual.
    """

    cleaned_jd = re.sub(r"\s+", " ", jd_text).strip()

    # Keeps cost/token usage lower without losing the important JD content.
    # Most useful job details appear in the first several thousand characters.
    cleaned_jd = cleaned_jd[:12000]

    extraction_prompt = f"""
You are an expert US data-role recruiter and ATS analyst.

Analyze the job description and return ONLY valid JSON.

Your goal is to extract concise, high-value signals for resume tailoring.
Do NOT over-extract.
Do NOT include generic soft skills unless they are clearly emphasized.
Do NOT infer tools that are not mentioned or strongly implied.

Required JSON schema:
{{
  "role_title": "",
  "company": "",
  "location": "",
  "experience_years": "",
  "role_domain": "",
  "seniority": "",
  "tools": [],
  "top_keywords": [],
  "top_responsibilities": [],
  "top_business_skills": [],
  "tailoring_focus": [],
  "possible_skill_substitutions": [],
  "low_priority_or_risky_keywords": []
}}

Field rules:
- role_title: exact or closest role title.
- company: employer name if available; otherwise empty string.
- location: city/state/remote/hybrid if available.
- experience_years: concise string like "0-2 years", "2+ years", "3-5 years", or empty string.
- role_domain: choose ONE best fit:
  "Data Science", "Product Analytics", "Data Analytics", "Business Intelligence",
  "Marketing Analytics", "Risk Analytics", "Operations Analytics",
  "Machine Learning", "Data Engineering", or "Other".
- seniority: choose ONE:
  "Entry Level", "Early Career", "Mid Level", "Senior", or "Unclear".
- tools: max 8 important tools/platforms/languages explicitly mentioned or strongly implied.
- top_keywords: max 8 ATS keywords that matter most for this role.
- top_responsibilities: max 4 concrete responsibilities from the JD.
- top_business_skills: max 4 business/domain skills such as stakeholder management, product insights, experimentation, reporting, decision support.
- tailoring_focus: max 4 short phrases describing what the resume should emphasize.
- possible_skill_substitutions: max 3 safe adjacent substitutions that could help ATS fit.
  Examples:
  "Power BI -> Tableau", "PostgreSQL -> BigQuery", "LightGBM -> XGBoost", "SQL -> Snowflake".
  Only include substitutions if they are realistic and adjacent.
- low_priority_or_risky_keywords: max 4 JD keywords that should NOT be overemphasized unless already supported.

Return JSON only.

Job Description:
{cleaned_jd}
"""

    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=900,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You extract concise, accurate job-description intelligence for focused resume tailoring."
            },
            {
                "role": "user",
                "content": extraction_prompt
            },
        ],
    )

    return json.loads(response.choices[0].message.content)


def build_daily_driver_prompt(
    resume_text: str,
    jd_text: str,
    jd_info: dict,
    header_location: str,
    degree_title: str,
    resume_profile: str,
) -> str:
    """
    Lean OpenAI prompt for GPT-4o-mini.
    Goal: controlled micro-tailoring, not full resume rewriting.
    """

    if resume_profile == "Data Scientist":
        profile_guidance = """
SELECTED RESUME IDENTITY: DATA SCIENTIST

Keep the resume focused on:
- Python, SQL, predictive modeling, statistical analysis, experimentation, optimization, forecasting, recommendation systems, and business impact.
- Good DS tailoring can emphasize: Scikit-learn, LightGBM, XGBoost, TensorFlow, feature engineering, model evaluation, A/B testing, causal inference, BigQuery, PySpark, Databricks, AWS, Azure, Tableau, Power BI.
- Do NOT drift into a broad ML Engineer, Data Engineer, MLOps Engineer, or GenAI Engineer resume.
- Avoid adding unsupported infrastructure-heavy tools such as Kubernetes, Airflow, Kafka, MLflow, Docker, SageMaker, Vertex AI, Hugging Face, or PyTorch unless already present in the selected base resume or clearly required by the JD and strongly supported by a project.
"""
    else:
        profile_guidance = """
SELECTED RESUME IDENTITY: DATA ANALYST

Keep the resume focused on:
- SQL, Python, dashboards, KPI reporting, data quality, funnel/cohort analysis, customer segmentation, A/B testing, business insights, and stakeholder decision support.
- Good DA tailoring can emphasize: Excel, Tableau, Power BI, BigQuery, PostgreSQL, MySQL, Azure, PySpark, ETL workflows, executive reporting, dashboard design, revenue analysis, product analytics, and data storytelling.
- Do NOT make this resume ML-heavy or turn it into a Data Scientist, Data Engineer, MLOps, or GenAI resume.
- Avoid adding unsupported ML/cloud tools such as TensorFlow, PyTorch, Hugging Face, Kubernetes, MLflow, SageMaker, Vertex AI, or deep learning unless already present in the selected base resume.
"""

    return rf"""
You are a senior resume tailoring assistant for US data roles.

Your job is to make CONTROLLED, RECRUITER-BELIEVABLE micro-edits to the selected base resume so it aligns better with the job description.

This is NOT a full rewrite.
This is NOT keyword stuffing.
This is NOT a generic ATS rewrite.

The candidate already has separate focused base resumes. Your job is to preserve the selected resume identity and make small, high-impact adjustments.

{profile_guidance}

FIXED FACTS — DO NOT CHANGE:
- Candidate name, phone number, email, links, companies, dates, degree, GPA, and section order.
- Degree title must remain exactly: {degree_title}
- Do NOT change the Education section except preserving formatting.
- Header location must be exactly: {header_location}
- Keep the resume one-page friendly.
- Keep LaTeX valid.

STRUCTURED JD SUMMARY:
- Role title: {jd_info.get('role_title', '')}
- Company: {jd_info.get('company', '')}
- Location: {jd_info.get('location', '')}
- Role domain: {jd_info.get('role_domain', '')}
- Seniority: {jd_info.get('seniority', '')}
- Experience years: {jd_info.get('experience_years', '')}
- Important tools: {', '.join(jd_info.get('tools', []))}
- Top keywords: {', '.join(jd_info.get('top_keywords', []))}
- Top responsibilities: {' | '.join(jd_info.get('top_responsibilities', []))}
- Business skills: {', '.join(jd_info.get('top_business_skills', []))}
- Tailoring focus: {', '.join(jd_info.get('tailoring_focus', []))}
- Possible safe skill substitutions: {', '.join(jd_info.get('possible_skill_substitutions', []))}
- Low-priority or risky keywords: {', '.join(jd_info.get('low_priority_or_risky_keywords', []))}

MICRO-TAILORING RULES:
1. Preserve the selected resume's core identity: {resume_profile}.
2. Rewrite only bullets that materially improve fit for this JD.
3. Keep the same sections, same jobs, same projects, same bullet count, and similar bullet length.
4. Start every bullet with a strong action verb.
5. Keep measurable outcomes and quantified impact wherever already present.
6. Prefer sharper wording over adding more words.
7. Do not make vague claims such as "leveraged data" or "worked with stakeholders" without a clear outcome.
8. Do not copy long phrases from the JD.

SKILL TAILORING RULES:
- You may add or replace at most 1-2 skills total in the Skills section if they are highly relevant to the JD.
- Use "Possible safe skill substitutions" as guidance for the 1-2 allowed skill changes.
- Avoid emphasizing "Low-priority or risky keywords" unless they are already strongly supported by the selected base resume.
- Use "Tailoring focus" to decide which bullets deserve small edits.
- Only add a skill if it is adjacent to the candidate's existing experience or can be credibly defended through the listed work/projects.

CONTROLLED TOOL SUBSTITUTION RULE:
- If the JD strongly prefers a tool that is very close to an existing tool, you may make a careful substitution in the Skills section or a project bullet.
- Examples of acceptable adjacent substitutions:
  - BigQuery / Snowflake / PostgreSQL / MySQL for SQL warehouse/database context, only when SQL analytics is already central.
  - Tableau / Power BI / Looker Studio for BI dashboarding context, only when dashboarding is already central.
  - XGBoost / LightGBM / Scikit-learn for tree-based modeling context, only when modeling is already central.
  - AWS / Azure for cloud analytics context, only when cloud/data workflows are already present.
- Do NOT claim production ownership of a tool if the base resume does not support it.
- Do NOT add Kubernetes, production MLOps, GenAI, LLMs, or deep learning unless the selected base resume already supports it.

BULLET STYLE:
Each rewritten bullet should follow:
[Action Verb] + [Tool/Method] + [Business or analytical problem] + [Quantified result or decision impact]

OUTPUT RULES:
- Return only the final LaTeX resume inside a single ```latex code block.
- First line must be:
  % Match Assessment: [score]/10 - [brief fit summary]
- Do not add prose outside the code block.
- Keep LaTeX valid.
- Preserve special characters and escaping.

SELECTED BASE RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}
"""


def build_dream_job_prompt(
    resume_text: str,
    jd_text: str,
    jd_info: dict,
    header_location: str,
    degree_title: str,
    resume_profile: str,
) -> str:
    """
    Premium single-pass tailoring prompt for Dream Job mode.
    Goal: higher-quality strategic tailoring without extra critique passes.
    """

    if resume_profile == "Data Scientist":
        profile_guidance = """
SELECTED RESUME IDENTITY: DATA SCIENTIST

Preserve a focused applied Data Scientist profile:
- Core strengths: Python, SQL, statistical modeling, predictive modeling, feature engineering, model evaluation, experimentation, optimization, forecasting, anomaly detection, recommendation systems, and business impact.
- Strong supported tools/concepts: Scikit-learn, XGBoost, LightGBM, TensorFlow, A/B Testing, Causal Inference, PySpark, Databricks, BigQuery, AWS, Azure, Tableau, Power BI.
- Good tailoring direction: emphasize modeling, experimentation, statistical rigor, prediction, optimization, and measurable decision impact.
- Do NOT turn this into a Data Analyst, Data Engineer, MLOps Engineer, ML Engineer, or GenAI resume.
"""
        avoid_guidance = """
Avoid unsupported or distracting DS breadth:
- Do not add Kubernetes, production MLOps, Airflow, Kafka, MLflow, Docker, SageMaker, Vertex AI, Hugging Face, PyTorch, LLMs, or GenAI unless already present in the selected base resume or directly defensible through a listed project.
"""
    else:
        profile_guidance = """
SELECTED RESUME IDENTITY: DATA ANALYST

Preserve a focused Data Analyst / Product Analyst / BI Analyst profile:
- Core strengths: SQL, Python, dashboards, KPI reporting, data cleaning, data quality, ETL workflows, funnel analysis, cohort analysis, customer segmentation, A/B testing, revenue analysis, and stakeholder decision support.
- Strong supported tools/concepts: Tableau, Power BI, Excel, BigQuery, PostgreSQL, MySQL, Azure, PySpark, Pandas, NumPy, Executive Reporting, Dashboard Design, Data Storytelling.
- Good tailoring direction: emphasize business insights, reporting automation, metric design, dashboarding, product/customer analytics, and measurable business outcomes.
- Do NOT turn this into a Data Scientist, ML Engineer, Data Engineer, MLOps Engineer, or GenAI resume.
"""
        avoid_guidance = """
Avoid unsupported or distracting DA breadth:
- Do not add TensorFlow, PyTorch, Hugging Face, LSTM, deep learning, Kubernetes, MLflow, SageMaker, Vertex AI, production MLOps, or GenAI unless already present in the selected base resume.
"""

    return rf"""
You are a senior US technical recruiter, resume strategist, and ATS-aware editor for data roles.

This is DREAM JOB mode, so your task is to make the selected resume highly aligned to the job description while remaining focused, believable, and interview-defensible.

Do this in ONE high-quality pass.
Do not produce analysis, notes, explanations, or a critique.
Return only the final tailored LaTeX resume.

The candidate now has separate focused base resumes. Your most important job is to preserve the selected resume identity and make high-return edits only.

{profile_guidance}

{avoid_guidance}

FIXED FACTS — NEVER CHANGE:
- Candidate name, phone number, email, links, companies, dates, degree, GPA, and section order.
- Degree title must remain exactly: {degree_title}
- Do NOT modify the Education section except preserving formatting.
- Header location must be exactly: {header_location}
- Keep the resume one-page friendly.
- Keep LaTeX valid.

STRUCTURED JD INTELLIGENCE:
{json.dumps(jd_info, indent=2)}

HIGH-VALUE TAILORING SIGNALS:
- Tailoring focus: {', '.join(jd_info.get('tailoring_focus', []))}
- Possible safe skill substitutions: {', '.join(jd_info.get('possible_skill_substitutions', []))}
- Low-priority or risky keywords: {', '.join(jd_info.get('low_priority_or_risky_keywords', []))}

Use the tailoring focus to decide which bullets deserve edits.
Use possible safe skill substitutions only for 1-2 controlled skill changes.
Avoid low-priority or risky keywords unless already supported by the selected base resume.

PREMIUM TAILORING OBJECTIVE:
Make this resume look like a focused, credible fit for the role by improving:
1. Role alignment
2. Keyword coverage
3. Business relevance
4. Bullet specificity
5. Recruiter trust

But avoid over-tailoring. The final resume should still look like the same candidate, not a JD copy.

EDITING SCOPE:
- Keep the same jobs, same projects, same section order, and same number of bullets.
- Rewrite only the bullets where the JD fit can be materially improved.
- You may improve up to 6 bullets across the resume if useful.
- You may add or replace at most 1-2 skills total in the Skills section.
- Do not expand the Skills section length.
- Do not add new projects or remove existing projects.
- Do not change quantified results unless the resume already contains those metrics.

SKILL AND TOOL RULES:
- Prioritize skills that are both important in the JD and supported by the selected resume.
- You may make 1-2 adjacent substitutions when they improve ATS fit and remain defensible.
- Acceptable adjacent substitutions:
  - SQL warehouse/database context: BigQuery, Snowflake, PostgreSQL, MySQL
  - BI/dashboard context: Tableau, Power BI, Looker Studio
  - DS modeling context: Scikit-learn, XGBoost, LightGBM
  - Cloud analytics context: AWS, Azure
  - Product analytics context: GA4, A/B Testing, Funnel Analysis, Cohort Analysis
- If adding one skill, remove a less relevant skill from the same row.
- Do not add tools that make the resume look wider than the selected profile.
- Do not add a JD skill if there is no credible way to support it through work experience or projects.

BULLET WRITING RULES:
Every rewritten bullet should be crisp and follow this pattern where possible:
[Strong action verb] + [tool/method] + [business or analytical problem] + [quantified impact or decision outcome]

Good bullet qualities:
- Starts with an action verb
- Uses specific tools/methods naturally
- Has measurable output or impact
- Avoids vague phrasing
- Avoids obvious JD copy-paste
- Sounds believable in an interview

ROLE-SPECIFIC PRIORITIZATION:
- For Data Scientist roles: prioritize modeling, experimentation, statistical rigor, feature engineering, forecasting, optimization, anomaly detection, and model evaluation.
- For Product DS / Decision Scientist roles: prioritize experimentation, causal inference, segmentation, funnel/cohort analysis, and product/business impact.
- For Data Analyst / BI roles: prioritize SQL, dashboards, KPI reporting, data quality, stakeholder reporting, Tableau/Power BI, and business insights.
- For Product Analyst roles: prioritize funnel analysis, cohort retention, segmentation, experimentation, revenue metrics, and product decision support.

QUALITY BAR:
Before finalizing, silently check:
- Does the resume still match the selected profile: {resume_profile}?
- Are all added skills supported or adjacent enough to defend?
- Did the resume become too broad?
- Did the Education section remain fixed?
- Did bullet count and structure stay the same?
- Is the final output concise enough for a one-page resume?

OUTPUT RULES:
- Return the full final LaTeX resume inside a single ```latex code block.
- The first line must be:
  % Match Assessment: [score]/10 - [brief fit summary]
- Do not include commentary outside the code block.
- Keep LaTeX valid.
- Preserve special characters and escaping.

SELECTED BASE RESUME:
{resume_text}

FULL JOB DESCRIPTION:
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
    try:
        selected_base_resume = load_resume_template(resume_profile)
        st.subheader(f"Base Resume: {resume_profile}")
        st.caption(f"Loaded from: {RESUME_FILES[resume_profile]}")

        show_resume_editor = st.checkbox(
            "Show/edit base resume LaTeX",
            value=False,
            help="Leave unchecked for a lighter, faster interface."
        )

        if show_resume_editor:
            resume_text = st.text_area(
                "Edit your selected base resume if needed:",
                value=selected_base_resume,
                height=500,
                key=f"resume_text_{resume_profile}"
            )
        else:
            resume_text = selected_base_resume
            st.info("Base resume loaded. Editor hidden for faster use.")

    except Exception as e:
        st.error(f"Resume loading failed: {e}")
        st.stop()

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
                degree_title = r"Master of Science in Analytics"

            with st.spinner("Tailoring the resume..."):
                if strategy_mode == "Daily Driver (GPT-4o-mini)":
                    prompt = build_daily_driver_prompt(
                        resume_text=resume_text,
                        jd_text=jd_text,
                        jd_info=jd_info,
                        header_location=header_location,
                        degree_title=degree_title,
                        resume_profile=resume_profile,
                    )
                else:
                    prompt = build_dream_job_prompt(
                        resume_text=resume_text,
                        jd_text=jd_text,
                        jd_info=jd_info,
                        header_location=header_location,
                        degree_title=degree_title,
                        resume_profile=resume_profile,
                    )

                tailored_text = run_tailoring_model(prompt, strategy_mode)

                tailored_text = apply_deterministic_resume_overrides(
                    tailored_text=tailored_text,
                    header_location=header_location,
                    degree_title=degree_title,
                )
            st.subheader("🚀 Tailored LaTeX Resume")
            st.code(tailored_text, language='latex')
            st.success("Tailoring complete. Copy the LaTeX into Overleaf.")

            st.subheader("📋 JD Intelligence")
            st.json({
                "selected_base_resume": resume_profile,
                "role_title": jd_info.get("role_title", ""),
                "company": jd_info.get("company", ""),
                "location": jd_info.get("location", ""),
                "experience_years": jd_info.get("experience_years", ""),
                "role_domain": jd_info.get("role_domain", ""),
                "seniority": jd_info.get("seniority", ""),
                "tools": jd_info.get("tools", []),
                "top_keywords": jd_info.get("top_keywords", []),
                "top_responsibilities": jd_info.get("top_responsibilities", []),
                "top_business_skills": jd_info.get("top_business_skills", []),
                "tailoring_focus": jd_info.get("tailoring_focus", []),
                "possible_skill_substitutions": jd_info.get("possible_skill_substitutions", []),
                "low_priority_or_risky_keywords": jd_info.get("low_priority_or_risky_keywords", []),
                "header_location_selected": header_location,
                "degree_title_fixed": degree_title,
            })

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

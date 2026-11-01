
import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None

# Page settings
st.set_page_config(
    page_title="FlowMetric AI",
    page_icon="📊",
    layout="wide"
)

# Database connection
def get_connection():
    return sqlite3.connect("flowmetric.db")

# Create database table
def create_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee TEXT,
            project TEXT,
            progress INTEGER,
            status TEXT,
            update_text TEXT,
            blockers TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

create_table()

# Save project update
def save_update(employee, project, progress,
                status, update_text, blockers):

    conn = get_connection()

    conn.execute("""
        INSERT INTO project_updates
        (employee, project, progress, status,
         update_text, blockers, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        employee,
        project,
        progress,
        status,
        update_text,
        blockers,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()
    conn.close()
def analyze_update(employee, project, progress, status, update_text, blockers):

    if client is None:
        return "Gemini API key not configured."

    prompt = f"""
    You are an AI project management assistant.

    Analyse this project update:

    Employee: {employee}
    Project: {project}
    Progress: {progress}%
    Status: {status}
    Update: {update_text}
    Blockers: {blockers}

    Provide:
    1. Manager-friendly summary.
    2. Risk level: Low, Medium, or High.
    3. Recommended next action.
    Important rules:
- Use only the information provided above.
- Never claim employee or project details are missing when they are supplied.
- Do not invent blockers, delays, or project information.
- If information is insufficient, clearly mention what needs clarification.
- Make recommendations specific and practical.
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )
        return response.text

    except Exception as e:
        return f"AI analysis failed: {str(e)}"
# Application heading
st.title("📊 FlowMetric AI")
st.subheader("Turning scattered updates into measurable progress.")

st.write(
    "An AI-powered assistant that helps managers "
    "track project progress, identify blockers, "
    "and generate project reports."
)

st.divider()

# Project update form
st.header("📝 Submit Project Update")

with st.form("project_update"):

    employee = st.text_input("Employee Name")
    project = st.text_input("Project Name")

    progress = st.slider(
        "Project Completion (%)", 0, 100, 50
    )

    status = st.selectbox(
        "Project Status",
        ["On Track", "At Risk", "Delayed"]
    )

    update_text = st.text_area(
        "Describe your latest progress"
    )

    blockers = st.text_area(
        "Any blockers or challenges?"
    )

    submitted = st.form_submit_button(
        "Submit Update"
    )

    if submitted:
        if not employee.strip() or not project.strip():
            st.error("Please enter employee and project names.")

        elif not update_text.strip():
            st.error("Please describe the latest progress.")

        else:
            save_update(
                employee, project, progress,
                status, update_text, blockers
            )

            
            st.success("Project update saved successfully!")

with st.spinner("AI is analysing your project update..."):
    ai_result = analyze_update(
        employee, project, progress,
        status, update_text, blockers
    )

st.subheader("🤖 AI Project Analysis")
st.write(ai_result)




# Manager Dashboard
st.divider()
st.header("📊 Manager Dashboard")
conn = get_connection()

df = pd.read_sql_query(
    "SELECT * FROM project_updates ORDER BY id DESC",
    conn
)

conn.close()
if not df.empty:

    total_updates = len(df)
    avg_progress = round(df["progress"].mean(), 1)

    on_track = len(df[df["status"] == "On Track"])
    at_risk = len(df[df["status"] == "At Risk"])
    delayed = len(df[df["status"] == "Delayed"])

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Updates", total_updates)
    col2.metric("Average Progress", f"{avg_progress}%")
    col3.metric("At Risk", at_risk)
    col4.metric("Delayed", delayed)

    st.subheader("Project Status Overview")

    status_data = pd.DataFrame({
        "Status": ["On Track", "At Risk", "Delayed"],
        "Count": [on_track, at_risk, delayed]
    })

    st.bar_chart(status_data.set_index("Status"))

    st.subheader("Project-wise Progress")

    project_data = df.groupby("project")["progress"].mean().reset_index()

    st.bar_chart(
        project_data.set_index("project")
    )

    st.subheader("Reported Blockers")

    blocker_data = df[
        df["blockers"].str.strip().str.lower().isin(
            ["", "no", "none", "nil", "n/a"]
        ) == False
    ]

    if not blocker_data.empty:
        st.dataframe(
            blocker_data[["employee", "project", "status", "blockers"]],
            width="stretch"
        )
    else:
        st.success("No blockers reported.")

else:
    st.info("Submit project updates to view the dashboard.") 
st.divider()
st.header("📋 Project Update History")

conn = get_connection()

df = pd.read_sql_query(
    "SELECT * FROM project_updates ORDER BY id DESC",
    conn
)# Display saved updates

conn.close()
conn = get_connection()

df = pd.read_sql_query(
    "SELECT * FROM project_updates ORDER BY id DESC",
    conn
)

conn.close()
if not df.empty:
    st.metric("Total Updates Submitted", len(df))

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No project updates have been submitted yet.")

    # Manager-Ready Project Report
st.divider()
st.header("📋 Manager-Ready Project Report")

if not df.empty:
    st.subheader("Overall Project Health")

    if delayed > 0:
        st.warning(f"{delayed} delayed update(s) need immediate attention.")
    elif at_risk > 0:
        st.warning(f"{at_risk} update(s) are at risk and need monitoring.")
    else:
        st.success("All reported updates are currently on track.")

    st.subheader("Projects Requiring Attention")

    attention_data = df[df["status"].isin(["At Risk", "Delayed"])]

    if not attention_data.empty:
        st.dataframe(
            attention_data[
                ["project", "employee", "progress", "status", "blockers"]
            ],
            hide_index=True,
            width="stretch"
        )
    else:
        st.success("No projects currently require attention.")

    st.subheader("Manager's Action Summary")

    if delayed > 0:
        st.write("1. Review delayed projects and identify reasons for delays.")

    if at_risk > 0:
        st.write("2. Contact teams working on at-risk projects.")

    st.write("3. Review reported blockers and assign owners for resolution.")
    st.write("4. Monitor project progress through regular status updates.")

else:
    st.info("Submit project updates to generate the manager report.")

    # Export Project Updates
st.divider()
st.subheader("📥 Export Project Report")

if not df.empty:
    csv_data = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Project Report (CSV)",
        data=csv_data,
        file_name="FlowMetric_Project_Report.csv",
        mime="text/csv"
    )
else:
    st.info("No data available to export.")

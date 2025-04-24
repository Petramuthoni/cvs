import streamlit as st
import requests
import pandas as pd
import base64
from io import BytesIO
import re
import os
from thefuzz import fuzz  # Fuzzy matching

# ---------------------- RChilli Config ----------------------
RCHILLI_API_URL = "https://rest.rchilli.com/RChilliParser/Rchilli/parseResumeBinary"
USER_KEY = "F7KNYZOZ"
VERSION = "8.0.0"
SUBSCRIPTION_ID = "petra kibugu"

# ---------------------- Webhook Config ----------------------
WEBHOOK_URL = "https://prod-186.westeurope.logic.azure.com:443/workflows/48a27f0ee7ae48c7b74600725ff9d823/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=smEXR63w3emvWl-zPwG-9z0PG8YK7JTS3I9TVk3KqyA"

# ---------------------- Options ----------------------
SKILLS =[
    "Capacity Building","Climate Health","Communication","Communication and presentation","Computer Science","Data Analysis","Data Science","Finance, Accounting","Financial Management","Fundraising & Strategic Partnership","Gender and social inclusion","General Management","Grant and contracts management", "Health Economics","Health Insurance","Health Systems Strengthening","Health financing","HR Management & Expertise","Human Resources for Health",
    "Internationally Funded Programs & resource mobilization","Leadership Management and Governance","Machine Learning","mHealth/Digital Health",
    "Monitoring, Evaluation and Learning","Multi-stakeholder coordination","Policy and Advocacy","Programming","Project Management","Python",
    "Quality Improvement","Quantitative research and implementation","RMNCH","Research and data analysis","Software Development"
]
COUNTRY_OPTIONS = [
    "AFD", "AHI", "ETHIOPIA", "FMD", "HQ", "ITALY", "KCO",
    "MALAWI", "SENEGAL", "SOUTH SUDAN", "TANZANIA", "UGANDA", "ZAMBIA"
]
NATIONALITY_OPTIONS = [
    "Afghan", "Albanian", "Algerian", "American", "Andorran", "Angolan", "Antiguan and Barbudan", "Argentine", "Armenian", "Australian", "Austrian", "Azerbaijani",
    "Bahamian", "Bahraini", "Bangladeshi", "Barbadian", "Belarusian", "Belgian", "Belizean", "Beninese", "Bhutanese", "Bolivian", "Bosnian and Herzegovinian", "Botswanan", "Brazilian",
    "British", "Bruneian", "Bulgarian", "Burkinabé", "Burmese", "Burundian", "Cabo Verdean", "Cambodian", "Cameroonian", "Canadian", "Central African", "Chadian", "Chilean",
    "Chinese", "Colombian", "Comoran", "Congolese", "Costa Rican", "Croatian", "Cuban", "Cypriot", "Czech", "Danish", "Djiboutian", "Dominican", "Dutch", "Ecuadorian", "Egyptian",
    "Salvadoran", "Equatorial Guinean", "Eritrean", "Estonian", "Ethiopian", "Fijian", "Finnish", "French", "Gabonese", "Gambian", "Georgian", "German", "Ghanaian", "Greek",
    "Grenadian", "Guatemalan", "Guinean", "Guyanese", "Haitian", "Honduran", "Hungarian", "Icelandic", "Indian", "Indonesian", "Iranian", "Iraqi", "Irish", "Israeli", "Italian",
    "Ivorian", "Jamaican", "Japanese", "Jordanian", "Kazakhstani", "Kenyan", "Kiribati", "Kuwaiti", "Kyrgyzstani", "Lao", "Latvian", "Lebanese", "Lesotho", "Liberian", "Libyan",
    "Liechtenstein", "Lithuanian", "Luxembourgish", "Macedonian", "Malagasy", "Malawian", "Malaysian", "Maldivian", "Malian", "Maltese", "Marshallese", "Mauritanian", "Mauritian",
    "Mexican", "Micronesian", "Moldovan", "Monacan", "Mongolian", "Montenegrin", "Moroccan", "Mozambican", "Namibian", "Nauruan", "Nepalese", "New Zealander", "Nicaraguan", "Nigerien",
    "Nigerian", "North Korean", "Norwegian", "Omani", "Pakistani", "Palauan", "Palestinian", "Panamanian", "Papua New Guinean", "Paraguayan", "Peruvian", "Filipino", "Polish", "Portuguese",
    "Qatari", "Romanian", "Russian", "Rwandan", "Saint Lucian", "Samoan", "Saudi", "Senegalese", "Serbian", "Seychellois", "Singaporean", "Slovak", "Slovenian", "Solomon Islander", "Somali",
    "South African", "South Korean", "South Sudanese", "Spanish", "Sri Lankan", "Sudanese", "Surinamese", "Swazi", "Swedish", "Swiss", "Syrian", "Taiwanese", "Tajik", "Tanzanian", "Thai",
    "Timorese", "Togolese", "Tongan", "Trinidadian and Tobagonian", "Tunisian", "Turkish", "Turkmen", "Tuvaluan", "Ugandan", "Ukrainian", "Emirati", "Uruguayan", "Uzbek", "Vanuatuan",
    "Venezuelan", "Vietnamese", "Yemeni", "Zambian", "Zimbabwean"
]
DEPARTMENT_OPTIONS = [
    "Advocacy & Policy", "Audit & Compliance","Business Development","Climate & Health","Communications","Digital Health & Data","Finance & Operations",
    "Fundraising","Health Systems Strengthening","ICT","Monitoring, Evaluation & Learning","Partnerships & External Affairs", "People & Culture (HR)",
    "Procurement & Administration","Public Health & Programs","Research Development & Innovation","Social Determinants of Health"
]
PROFICIENCY_LEVELS = ["Beginner", "Intermediate", "Advanced"]

# ---------------------- Utility Functions ----------------------
def encode_file_to_base64(file):
    return base64.b64encode(file.read()).decode("utf-8")

def parse_resume(file):
    file_base64 = encode_file_to_base64(file)
    payload = {
        "filedata": file_base64,
        "filename": file.name,
        "userkey": USER_KEY,
        "version": VERSION,
        "subuserid": SUBSCRIPTION_ID
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(RCHILLI_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to parse CV. API Response: {response.text}")
        return None

def extract_fields(parsed_data):
    if not parsed_data or "ResumeParserData" not in parsed_data:
        return None
    resume_data = parsed_data["ResumeParserData"]
    name = resume_data.get("Name", {}).get("FormattedName", "N/A")
    current_job_role = resume_data.get("JobProfile", "N/A")
    total_years_experience = resume_data.get("WorkedPeriod", {}).get("TotalExperienceInYear", "N/A")

    highest_education = "N/A"
    if "SegregatedQualification" in resume_data and isinstance(resume_data["SegregatedQualification"], list):
        highest_education = resume_data["SegregatedQualification"][0].get("Degree", {}).get("DegreeName", "N/A")

    extracted_skills = set()
    if "SkillBlock" in resume_data:
        extracted_skills.update(skill.strip().lower() for skill in re.split(r"[•,;|\n]", resume_data["SkillBlock"]) if skill.strip())
    if "SkillKeywords" in resume_data:
        extracted_skills.update(skill.strip().lower() for skill in resume_data["SkillKeywords"].split(",") if skill.strip())

    def is_skill_match(skill):
        for extracted_skill in extracted_skills:
            if fuzz.partial_ratio(skill.lower(), extracted_skill) > 80:
                return "✔"
        return "✘"

    skills_match = {skill: is_skill_match(skill) for skill in SKILLS}

    return {
        "Name": name,
        "Highest Education": highest_education,
        "Current Job Role": current_job_role,
        "Total Years of Experience": total_years_experience,
        **skills_match
    }

UPLOADS_DIR = "C:/StreamlitUploads"
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR, exist_ok=True)

def save_uploaded_file(uploaded_file):
    file_path = os.path.join(UPLOADS_DIR, uploaded_file.name)
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except PermissionError:
        st.error(f"Permission denied to save file: {file_path}")
        return None

def generate_download_link(file_path):
    file_path = file_path.replace("\\", "/")
    return f'=HYPERLINK("{file_path}", "{os.path.basename(file_path)}")'

def push_to_webhook(data_row):
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(WEBHOOK_URL, json=data_row, headers=headers)
        if response.status_code in [200, 201]:
            st.success("Data saved in CRM successfully!")
        else:
            st.error(f"Webhook error: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Failed to send data to webhook: {e}")

# ---------------------- Streamlit UI ----------------------
st.title("CV Parser")

col1, col2 = st.columns(2)
with col1:
    employee_no = st.text_input("Employee No:")
    gender = st.selectbox("Gender", ["Male", "Female"], index=None)
    department = st.selectbox("Select Department/Programme", DEPARTMENT_OPTIONS, index=None)
    country = st.selectbox("Select Country", COUNTRY_OPTIONS, index=None)
    nationality = st.selectbox("Select Nationality", NATIONALITY_OPTIONS, index=None)

upload_disabled = not all([employee_no, gender, department, country, nationality])

with col2:
    selected_skills = st.multiselect("Select up to 5 skills", SKILLS, max_selections=5)
    skill_proficiency = {skill: st.selectbox(f"{skill} Proficiency", PROFICIENCY_LEVELS) for skill in selected_skills}
    uploaded_file = st.file_uploader("Upload a CV (PDF)", type=["pdf"], disabled=upload_disabled)

if uploaded_file:
    st.info("Parsing the CV...")
    parsed_data = parse_resume(uploaded_file)
    extracted_data = extract_fields(parsed_data)
    file_path = save_uploaded_file(uploaded_file)
    download_link = generate_download_link(file_path)

    if extracted_data:
        extracted_data.update({
            "Employee No": employee_no,
            "Gender": gender,
            "Department/Programme": department,
            "Country": country,
            "Nationality": nationality,
            "Resume": download_link
        })

        # Update Skill Proficiency as array of objects
        nested_proficiency = [
            {"name": skill, "proficiency": level}
            for skill, level in skill_proficiency.items()
        ]
        extracted_data["Skill_Proficiency"] = nested_proficiency

        # Prepare display data with proficiency fields for table
        display_data = extracted_data.copy()
        if "Skill Proficiency" in display_data:
            for item in display_data["Skill_Proficiency"]:
                display_data[f"{item['name']} Proficiency"] = item["proficiency"]

        column_order = [
            "Resume", "Employee No", "Name", "Gender", "Department/Programme",
            "Country", "Nationality", "Highest Education", "Current Job Role", "Total Years of Experience"
        ] + [f"{skill} Proficiency" for skill in selected_skills] + SKILLS

        df = pd.DataFrame([display_data])
        for col in column_order:
            if col not in df.columns:
                df[col] = ""
        df = df[column_order]

        st.write("### Extracted Information")
        st.dataframe(df)

        #st.subheader("📦 JSON Payload Preview")
        #st.json(extracted_data)

        push_to_webhook(extracted_data)

        # Download CSV
        csv_file_path = os.path.abspath("Parsed_CV.csv")
        df.to_csv(csv_file_path, index=False, header=True, encoding="utf-8-sig")
        with open(csv_file_path, "rb") as f:
            csv_bytes = f.read()

        st.download_button("Download Excel File", data=csv_bytes, file_name="Parsed_CV.csv", mime="text/csv")

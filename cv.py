import streamlit as st
import requests
import pandas as pd
import base64
from io import BytesIO
import re
import os
from thefuzz import fuzz  # Fuzzy matching

# RChilli API credentials
RCHILLI_API_URL = "https://rest.rchilli.com/RChilliParser/Rchilli/parseResumeBinary"
USER_KEY = "F7KNYZOZ"
VERSION = "8.0.0"
SUBSCRIPTION_ID = "petra kibugu"

# Predefined Skills List
SKILLS = [
    "Python", "Data Analysis", "Machine Learning", "Project Management", "Communication",
    "Health financing", "Health Insurance", "Health Economics",
    "Internationally Funded Programs & resource mobilization", "Capacity Building",
    "General Management", "Leadership Management and Governance", "Health Systems Strengthening",
    "Grant and contracts management", "Finance, Accounting", "Monitoring, Evaluation and Learning",
    "Quantitative research and implementation", "Multi-stakeholder coordination", "Gender and social inclusion",
    "mHealth/Digital Health", "Quality Improvement", "Climate Health", "Fundraising & Strategic Partnership",
    "RMNCH", "Data Science", "Computer Science", "Programming", "Software Development",
    "Research and data analysis", "HR Management & Expertise", "Financial Management",
    "Policy and Advocacy", "Human Resources for Health", "Communication and presentation"
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

DEPARTMENT_OPTIONS = ["Public Health & Programs","Health Systems Strengthening","Climate & Health","Social Determinants of Health","Digital Health & Data",
"Monitoring, Evaluation & Learning","Research Development & Innovation","Partnerships & External Affairs","Business Development","Fundraising","Advocacy & Policy","Communications","ICT","People & Culture (HR)","Finance & Operations","Procurement & Administration","Audit & Compliance"]

PROFICIENCY_LEVELS = ["Beginner", "Intermediate", "Advanced"]

# Function to convert file to base64
def encode_file_to_base64(file):
    return base64.b64encode(file.read()).decode("utf-8")

# Function to parse CV using RChilli
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

# Function to extract required fields
def extract_fields(parsed_data):
    if not parsed_data or "ResumeParserData" not in parsed_data:
        return None

    resume_data = parsed_data["ResumeParserData"]
    
    # Extract Name
    name = resume_data.get("Name", {}).get("FormattedName", "N/A")

    # Extract Current Job Role
    current_job_role = resume_data.get("JobProfile", "N/A")

    # Extract Total Years of Experience
    total_years_experience = resume_data.get("WorkedPeriod", {}).get("TotalExperienceInYear", "N/A")

    # Extract Highest Level of Education
    highest_education = "N/A"
    if "SegregatedQualification" in resume_data and isinstance(resume_data["SegregatedQualification"], list):
        highest_education = resume_data["SegregatedQualification"][0].get("Degree", {}).get("DegreeName", "N/A")

    # Extract skills from both SkillBlock and SkillKeywords
    extracted_skills = set()

    # Process SkillBlock
    if "SkillBlock" in resume_data:
        skill_text = resume_data["SkillBlock"]
        extracted_skills.update(
            skill.strip().lower()
            for skill in re.split(r"[•,;|\n]", skill_text) if skill.strip()
        )

    # Process SkillKeywords
    if "SkillKeywords" in resume_data:
        keyword_text = resume_data["SkillKeywords"]
        extracted_skills.update(
            skill.strip().lower()
            for skill in keyword_text.split(",") if skill.strip()
        )

    # Function for fuzzy skill matching
    def is_skill_match(skill):
        for extracted_skill in extracted_skills:
            if fuzz.partial_ratio(skill.lower(), extracted_skill) > 80:  # 80% similarity threshold
                return "✔"
        return "✘"

    # Match predefined skills using fuzzy matching
    skills_match = {skill: is_skill_match(skill) for skill in SKILLS}

    # Return extracted data with skills match results
    return {
        "Name": name,
        "Highest Education": highest_education,
        "Current Job Role": current_job_role,
        "Total Years of Experience": total_years_experience,
        **skills_match  # Add all skill columns dynamically
    }
# Define a folder that Streamlit always has access to
UPLOADS_DIR = "C:/StreamlitUploads"  # Windows path
# UPLOADS_DIR = "/home/user/streamlit_uploads"  # Linux/Mac path

# Ensure the uploads directory exists with proper permissions
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR, exist_ok=True)  # Ensure it's created

def save_uploaded_file(uploaded_file):
    """Save the uploaded file in the dedicated uploads folder."""
    file_path = os.path.join(UPLOADS_DIR, uploaded_file.name)  # Save path

    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())  # Save the file
        return file_path
    except PermissionError:
        st.error(f"Permission denied: Unable to save file to {file_path}. Check folder permissions.")
        return None

# Function to generate a valid Excel hyperlink
def generate_download_link(file_path):
    file_path = file_path.replace("\\", "/")  # Ensure Excel reads it correctly
    file_name = os.path.basename(file_path)
    return f'=HYPERLINK("{file_path}", "{file_name}")'

# Streamlit UI
st.title("CV Parser")

# User input fields
col1, col2 = st.columns([2, 2])

with col1:
    employee_no = st.text_input("Employee No:")
    gender = st.selectbox("Gender", ["Male", "Female"], index=None, placeholder="Select Gender")
    department = st.selectbox("Select Department/Programme", DEPARTMENT_OPTIONS, index=None, placeholder="Select Department")
    country = st.selectbox("Select Country", COUNTRY_OPTIONS, index=None, placeholder="Select Country")
    nationality = st.selectbox("Select Nationality", NATIONALITY_OPTIONS, index=None, placeholder="Select Nationality")
    
# Disable file uploader until all fields are filled
upload_disabled = not all([employee_no, gender, department, country, nationality])

with col2:
    selected_skills = st.multiselect("Select up to 5 skills", SKILLS, max_selections=5)
    skill_proficiency = {skill: st.selectbox(f"{skill} Proficiency", PROFICIENCY_LEVELS) for skill in selected_skills}

    uploaded_file = st.file_uploader("Upload a CV (PDF)", type=["pdf"], disabled=upload_disabled)

# Handle CV processing if uploaded
if uploaded_file:
    st.info("Processing the CV...")
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
        
        # Add selected skills proficiency
        for skill, level in skill_proficiency.items():
            extracted_data[f"{skill} Proficiency"] = level

        # Define column order
        column_order = [
            "Resume","Employee No", "Name", "Gender", "Department/Programme", 
            "Country", "Nationality", "Highest Education", 
            "Current Job Role", "Total Years of Experience"
        ] + [f"{skill} Proficiency" for skill in selected_skills] + SKILLS 
        
        df = pd.DataFrame([extracted_data])[column_order]

        # Display extracted data
        st.write("### Extracted Information")
        st.dataframe(df)
        #st.write(df.to_html(escape=False), unsafe_allow_html=True) 
        
        # Convert to Excel
        csv_file_path = os.path.abspath("Parsed_CV.csv")
        df.to_csv(csv_file_path, index=False, header=True, encoding="utf-8-sig")
        with open (csv_file_path, "rb") as f:
            csv_bytes = f.read()
            
       
            
        
        st.download_button(
            label="Download Excel File",
            data=csv_bytes,
            file_name="Parsed_CV.csv",
            mime="text/csv"
        )

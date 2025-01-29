import re
import os
#import shutil
import pytesseract
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
import gender_guesser.detector as gender_detector
from transformers import pipeline
import streamlit as st
from dateutil import parser
import pandas as pd
from datetime import datetime

# Initialize NLP models and gender detector
ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", grouped_entities=True)
gender_detector = gender_detector.Detector()
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

# Function to extract text from a single CV file
def extract_text_from_file(file_path):
    extracted_text = ""
    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if not text.strip():  # Fallback to OCR if text is empty
                images = convert_from_path(file_path)
                text = "".join([pytesseract.image_to_string(image) for image in images])
            extracted_text += text
    return extracted_text

# Function to extract entities using the NLP model
def extract_entities(text):
    entities = ner_pipeline(text)
    extracted = {"PER": [], "ORG": [], "LOC": [], "MISC": []}
    for entity in entities:
        entity_group = entity["entity_group"]
        extracted[entity_group].append(entity["word"])
    return extracted

# Function to extract name from entities
def extract_name(entities):
    if "PER" in entities and entities["PER"]:
        full_name = " ".join(entities["PER"]).strip()
        if full_name.count(" ") > 1:
            return " ".join(full_name.split()[:2])
        return full_name
    return "Unknown Applicant"

# Function to infer gender from name
def extract_gender(name):
    first_name = name.split()[0] if name != "Unknown Applicant" else ""
    gender = gender_detector.get_gender(first_name)
    if gender in ["male", "female"]:
        return gender.capitalize()
    return "Not Specified"

# Function to extract email from text
def extract_email(text):
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        return email_match.group(0)
    return "Not Provided"

# Function to extract highest education
def extract_education(text):
    education_section_pattern = r"(?i)education\s*(.*?)\s*(work experience|skills|$)"
    match = re.search(education_section_pattern, text, re.DOTALL)
    
    if match:
        education_section = match.group(1).strip()
        lines = education_section.split("\n")
        
        # Define priority of education levels
        education_levels = [
            (r"\b(ph\.?d|doctorate)\b", "PhD/Doctorate"),
            (r"\b(masters?|msc|m\.sc|ma|mba|mph|m\.eng|mtech|m\.tech|mcom)\b", "Master's"),
            (r"\b(bachelors?|bsc|b\.sc|ba|bcom|btech|b\.tech|beng)\b", "Bachelor's")
        ]
        
        # Iterate through lines and check for the highest degree with its domain
        for pattern, degree_label in education_levels:
            for line in lines:
                if re.search(pattern, line, re.IGNORECASE):
                    return f"{degree_label} {line.strip()}"  # Return full line for context
        
    return "Not Specified"

# Function to extract the latest job position
def extract_latest_job(cv_text):
    work_section_pattern = r"(?i)(professional experience|work experience|employment history)\s*(.*?)(education|skills|$)"
    match = re.search(work_section_pattern, cv_text, re.DOTALL)
    if match:
        work_section = match.group(2).strip()
        lines = work_section.split("\n")
        for line in lines:
            if line.strip():
                return line.strip()
    return "Not Specified"

# Function to calculate total years of experience
def extract_experience(cv_text):
    # Extract the work experience section and stop at common headings
    work_section_pattern = r"(?i)(?:professional experience|work experience|employment history)\s*(.*?)(?:education|skills|certifications|referees|projects|$)"
    match = re.search(work_section_pattern, cv_text, re.DOTALL)
    
    if match:
        work_section = match.group(1).strip()  # Extract work experience text
        
        # Regex pattern to capture start years in job date ranges
        experience_pattern = r"(\b\w+\s\d{4})\s*[-–]\s*(?:\b(?:\w+\s\d{4}|Present|To Date))"
        matches = re.findall(experience_pattern, work_section)

        if matches:
            try:
                # Convert all start dates to years and find the earliest one
                start_years = [parser.parse(date).year for date in matches]
                earliest_year = min(start_years)
                current_year = datetime.now().year
                
                # Calculate total years of experience
                total_experience = current_year - earliest_year
                return total_experience if total_experience > 0 else "Not Specified"
            
            except Exception as e:
                print(f"Error parsing dates: {e}")
    
    return "Not Specified"



# Function to extract skills
def extract_skills(cv_text):
    cv_tokens = cv_text.lower().split()  # Tokenize CV text
    matched_skills = {}
    for skill in SKILLS:
        skill_tokens = skill.lower().split()
        if all(token in cv_tokens for token in skill_tokens):  # Match all skill tokens
            matched_skills[skill] = "✔"
        else:
            matched_skills[skill] = "✘"

    return matched_skills

# Function to process individual CV text
def process_cv_text(cv_text):
    entities = extract_entities(cv_text)
    name = extract_name(entities)
    gender = extract_gender(name)
    #email = extract_email(cv_text)
    education = extract_education(cv_text)
    latest_job = extract_latest_job(cv_text)
    experience = extract_experience(cv_text)
    skills = extract_skills(cv_text)

    result = {
        "Full Name": name,
        "Gender": gender,
        #"Email": email,
        "Highest Education": education,
        "Latest Job Position": latest_job,
        "Total Years of Experience": experience,
    }
    result.update(skills)  # Add skill matches to the result
    return result

# Function to process uploaded CVs
def process_cvs(uploaded_files):
    rows = []
    for uploaded_file in uploaded_files:
        file_path = os.path.join("temp", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        cv_text = extract_text_from_file(file_path)
        rows.append(process_cv_text(cv_text))

        os.remove(file_path)
    return pd.DataFrame(rows)

# Streamlit App
st.title("CV Processing App")
st.write("Upload CVs in PDF format to extract and analyze applicant information.")

uploaded_files = st.file_uploader("Upload CVs", type=["pdf"], accept_multiple_files=True)

if st.button("Process CVs"):
    if uploaded_files:
        os.makedirs("temp", exist_ok=True)
        with st.spinner("Processing files..."):
            df = process_cvs(uploaded_files)
        st.success("Processing complete!")
        st.write(df)

        # Save to Excel
        output_path = "cv_analysis_with_skills.xlsx"
        df.to_excel(output_path, index=False)
        with open(output_path, "rb") as f:
            st.download_button(
                label="Download Excel File",
                data=f,
                file_name="cv_analysis_with_skills.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        # Cleanup
       # shutil.rmtree("temp")
    else:
        st.error("Please upload at least one CV file.")

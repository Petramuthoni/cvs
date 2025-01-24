import os
import pandas as pd
import zipfile
from PyPDF2 import PdfReader
import spacy
from fuzzywuzzy import process
import streamlit as st
import shutil  # Import shutil for removing non-empty directories

# Load NLP model
nlp = spacy.load("en_core_web_sm")

# Predefined skill list
SKILLS = ["Python", "Data Analysis", "Machine Learning", "Project Management", "Communication","Health financing","Health Insurance","Health Economics",	"Internationally Funded Programs & resource mobilization","Capacity Building","General Management","Leadership Management and Governance","Health Systems Stengthening","Grant  and contracts management","Finance, Accounting","Monitoring, Evaluation and Learning","Quantitative research and implementation","Multi-stakeholder cordination","Gender ad social inclusion","mHealth/Digital Health","Quality Improvement","Climate Health","Fundraising & Strategic Partnership","RMNCH","Data Science","Computer Science" ,"Programming","Software Development","Research and data analysis","HR Management & Expertise",	"Financial Management",	"Policy and Advocacy","Human Resources for Health","Communication and presentation"]

# Function to extract text from CVs
def extract_text_from_file(file_path):
    extracted_text = ""
    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted_text += page.extract_text()
    elif file_path.endswith(".zip"):
        extracted_texts = []  # List to store extracted text from all PDFs in the ZIP
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith(".pdf"):
                    # Create a full temporary path for the extracted file
                    temp_path = os.path.join("temp", os.path.basename(file))
                    with zip_ref.open(file) as f:
                        # Ensure the temporary directory exists
                        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                        with open(temp_path, "wb") as temp_file:
                            temp_file.write(f.read())
                    # Extract text from the temporary PDF file
                    extracted_texts.append(extract_text_from_file(temp_path))
                    # Clean up the temporary file
                    os.remove(temp_path)
        return extracted_texts  # Return all extracted texts as a list
    return extracted_text

# Function to extract applicant's name
def extract_name(cv_text):
    doc = nlp(cv_text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            if "Curriculum Vitae" not in ent.text:
                return ent.text.strip()
    lines = cv_text.split("\n")
    for line in lines[:10]:
        if len(line) < 3 or "Curriculum Vitae" in line:
            continue
        words = line.strip().split()
        if len(words) in [2, 3] and all(word.istitle() for word in words):
            return line.strip()
    return "Unknown Applicant"

# Function to extract skills
def extract_skills(cv_text):
    doc = nlp(cv_text)
    tokens = [token.text for token in doc]
    matched_skills = {}
    for skill in SKILLS:
        match, score = process.extractOne(skill, tokens)
        matched_skills[skill] = "Match" if score > 80 else "Not Match"
    return matched_skills

# Function to process uploaded CVs and generate results
def process_cvs(cv_files):
    data = []
    for file_path in cv_files:
        cv_texts = extract_text_from_file(file_path)  # This can now be a string or a list
        if isinstance(cv_texts, str):
            cv_texts = [cv_texts]  # Wrap single CV text into a list for consistency
        
        for cv_text in cv_texts:  # Loop through each CV text (multiple PDFs in ZIP)
            name = extract_name(cv_text)
            skills = extract_skills(cv_text)
            row = {"Full Name": name, "CV File Name": os.path.basename(file_path)}
            row.update(skills)
            data.append(row)
    df = pd.DataFrame(data)
    return df

# Streamlit App
st.title("CV Skill Matcher")
st.write("Upload CVs (PDF or ZIP format) to match skills and generate a report.")

# File uploader
uploaded_files = st.file_uploader("Upload CVs", type=["pdf", "zip"], accept_multiple_files=True)

if st.button("Generate Report"):
    if not uploaded_files:
        st.error("Please upload at least one file.")
    else:
        # Ensure temp directory exists
        os.makedirs("temp", exist_ok=True)
        
        # Process uploaded files
        temp_files = []
        for uploaded_file in uploaded_files:
            temp_path = os.path.join("temp", uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())
            temp_files.append(temp_path)
        
        # Generate results
        with st.spinner("Processing CVs..."):
            df = process_cvs(temp_files)
        
        # Save results to an Excel file
        output_file = "matched_skills_output.xlsx"
        df.to_excel(output_file, index=False)
        
        # Provide download link
        st.success("Processing complete! Download the report below:")
        with open(output_file, "rb") as f:
            st.download_button(
                label="Download Excel Report",
                data=f,
                file_name="matched_skills_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        
        # Clean up temporary files
        for temp_file in temp_files:
            os.remove(temp_file)
        shutil.rmtree("temp", ignore_errors=True)  # Safely remove the temp directory
        os.remove(output_file)

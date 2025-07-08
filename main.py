from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json_repair
import uuid
from datetime import datetime
import traceback
import re

# Use reportlab instead of fpdf for better Unicode support
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === Setup ===
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY not set in environment variables.")

client = genai.Client(api_key=api_key)
app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js
        "http://localhost:5173",  # Vite
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory and mount it
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# === Utility Functions ===
def clean_text(text):
    """Clean and sanitize text for PDF generation"""
    if not text:
        return ""

    # Convert to string and handle None values
    text = str(text) if text is not None else ""

    # Remove or replace problematic characters
    text = re.sub(r'[^\w\s\-.,;:()@/\\&%$#!?+=*<>{}[\]|~`"\'°]', '', text)

    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    # Strip whitespace
    text = text.strip()

    return text


def safe_get(data, key, default=""):
    """Safely get value from dictionary with cleaning"""
    try:
        value = data.get(key, default) if isinstance(data, dict) else default
        return clean_text(value)
    except Exception:
        return clean_text(default)


def safe_list_get(data, key, default=None):
    """Safely get list from dictionary"""
    try:
        if default is None:
            default = []
        value = data.get(key, default) if isinstance(data, dict) else default
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            try:
                parsed = json_repair.loads(value)
                return parsed if isinstance(parsed, list) else default
            except:
                return default
        else:
            return default
    except Exception:
        return default if default is not None else []


# === Resume Parser ===
def parse_resume(content: bytes) -> dict:
    try:
        system_instruction = """You are a resume parser. Extract resume data from PDF and return a single JSON OBJECT. Use this schema:
{
  "first_name": "", "last_name": "", "email": "", "phone": "", "location": "",
  "social": {"linkedin": "", "github": ""},
  "skills": "",
  "work": [{"company":"","title":"","startDate":"","endDate":"","description":""}],
  "education": [{"degree":"","institution":"","startDate":"","endDate":"","percentage/gpa":""}],
  "projects": [{"name":"","description":""}],
  "certifications": [{"name":"","description":""}],
  "achievements": [{"name":"","description":""}],
  "other": {"Hobbies":"","Languages":""},
  "summary": ""
}

IMPORTANT: Use only basic ASCII characters in your response. Avoid special Unicode characters, emojis, or non-Latin scripts.
If data is missing, use empty strings or empty arrays.
Return valid JSON only. No comments or explanations.
        """

        file_part = types.Part.from_bytes(data=content, mime_type="application/pdf")
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=["Parse the resume and use only ASCII characters in response", file_part],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0,
                response_mime_type="application/json"
            )
        )

        raw_json = response.candidates[0].content.parts[0].text
        parsed_data = json_repair.loads(raw_json)

        # Clean all text fields
        cleaned_data = {}
        for key, value in parsed_data.items():
            if isinstance(value, str):
                cleaned_data[key] = clean_text(value)
            elif isinstance(value, dict):
                cleaned_data[key] = {k: clean_text(v) for k, v in value.items()}
            elif isinstance(value, list):
                cleaned_data[key] = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_data[key].append({k: clean_text(v) for k, v in item.items()})
                    else:
                        cleaned_data[key].append(clean_text(item))
            else:
                cleaned_data[key] = value

        return cleaned_data

    except Exception as e:
        print(f"Error parsing resume: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        # Return a safe default structure
        return {
            "first_name": "", "last_name": "", "email": "", "phone": "", "location": "",
            "social": {}, "skills": "", "work": [], "education": [], "projects": [],
            "certifications": [], "achievements": [], "other": {}, "summary": "",
            "parsing_error": f"Parsing failed: {str(e)}"
        }


# === PDF Generator with ReportLab ===
def generate_pdf_reportlab(data, path):
    """Generate PDF using ReportLab with proper Unicode support"""
    try:
        # Create document
        doc = SimpleDocTemplate(path, pagesize=letter, topMargin=0.5 * inch)
        story = []

        # Get styles
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=6,
            spaceBefore=12,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.darkblue,
            borderPadding=3
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6
        )

        # Title
        story.append(Paragraph("Processed Resume", title_style))
        story.append(Spacer(1, 12))

        # Contact Information
        name = f"{safe_get(data, 'first_name')} {safe_get(data, 'last_name')}".strip()
        if name.strip():
            story.append(Paragraph("Contact Information", heading_style))

            contact_data = []
            if name.strip():
                contact_data.append(["Name:", name])
            if safe_get(data, 'email'):
                contact_data.append(["Email:", safe_get(data, 'email')])
            if safe_get(data, 'phone'):
                contact_data.append(["Phone:", safe_get(data, 'phone')])
            if safe_get(data, 'location'):
                contact_data.append(["Location:", safe_get(data, 'location')])

            if contact_data:
                contact_table = Table(contact_data, colWidths=[1.5 * inch, 4 * inch])
                contact_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(contact_table)
                story.append(Spacer(1, 12))

        # Social Links
        social = data.get("social", {})
        if social and isinstance(social, dict):
            social_data = []
            for platform, link in social.items():
                if link and clean_text(link):
                    social_data.append([f"{platform.title()}:", clean_text(link)])

            if social_data:
                story.append(Paragraph("Social Links", heading_style))
                social_table = Table(social_data, colWidths=[1.5 * inch, 4 * inch])
                social_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(social_table)
                story.append(Spacer(1, 12))

        # Summary
        summary = safe_get(data, 'summary')
        if summary:
            story.append(Paragraph("Summary", heading_style))
            story.append(Paragraph(summary, normal_style))
            story.append(Spacer(1, 12))

        # Skills
        skills = safe_get(data, 'skills')
        if skills:
            story.append(Paragraph("Skills", heading_style))
            story.append(Paragraph(skills, normal_style))
            story.append(Spacer(1, 12))

        # Work Experience
        work = safe_list_get(data, 'work')
        if work:
            story.append(Paragraph("Work Experience", heading_style))
            for job in work:
                if isinstance(job, dict):
                    company = safe_get(job, 'company')
                    title = safe_get(job, 'title')
                    start_date = safe_get(job, 'startDate')
                    end_date = safe_get(job, 'endDate')
                    description = safe_get(job, 'description')

                    if company or title:
                        job_header = f"<b>{title}</b> at <b>{company}</b>" if title and company else f"<b>{title or company}</b>"
                        story.append(Paragraph(job_header, normal_style))

                        if start_date or end_date:
                            date_range = f"{start_date} - {end_date}" if start_date and end_date else (
                                        start_date or end_date)
                            story.append(Paragraph(f"<i>{date_range}</i>", normal_style))

                        if description:
                            story.append(Paragraph(description, normal_style))

                        story.append(Spacer(1, 6))

        # Education
        education = safe_list_get(data, 'education')
        if education:
            story.append(Paragraph("Education", heading_style))
            for edu in education:
                if isinstance(edu, dict):
                    degree = safe_get(edu, 'degree')
                    institution = safe_get(edu, 'institution')
                    start_date = safe_get(edu, 'startDate')
                    end_date = safe_get(edu, 'endDate')
                    gpa = safe_get(edu, 'percentage/gpa')

                    if degree or institution:
                        edu_header = f"<b>{degree}</b> - <b>{institution}</b>" if degree and institution else f"<b>{degree or institution}</b>"
                        story.append(Paragraph(edu_header, normal_style))

                        if start_date or end_date:
                            date_range = f"{start_date} - {end_date}" if start_date and end_date else (
                                        start_date or end_date)
                            story.append(Paragraph(f"<i>{date_range}</i>", normal_style))

                        if gpa:
                            story.append(Paragraph(f"GPA/Percentage: {gpa}", normal_style))

                        story.append(Spacer(1, 6))

        # Projects
        projects = safe_list_get(data, 'projects')
        if projects:
            story.append(Paragraph("Projects", heading_style))
            for project in projects:
                if isinstance(project, dict):
                    name = safe_get(project, 'name')
                    description = safe_get(project, 'description')

                    if name:
                        story.append(Paragraph(f"<b>{name}</b>", normal_style))
                        if description:
                            story.append(Paragraph(description, normal_style))
                        story.append(Spacer(1, 6))

        # Certifications
        certifications = safe_list_get(data, 'certifications')
        if certifications:
            story.append(Paragraph("Certifications", heading_style))
            for cert in certifications:
                if isinstance(cert, dict):
                    name = safe_get(cert, 'name')
                    description = safe_get(cert, 'description')

                    if name:
                        cert_text = f"• {name}"
                        if description:
                            cert_text += f": {description}"
                        story.append(Paragraph(cert_text, normal_style))

        # Achievements
        achievements = safe_list_get(data, 'achievements')
        if achievements:
            story.append(Paragraph("Achievements", heading_style))
            for achievement in achievements:
                if isinstance(achievement, dict):
                    name = safe_get(achievement, 'name')
                    description = safe_get(achievement, 'description')

                    if name:
                        ach_text = f"• {name}"
                        if description:
                            ach_text += f": {description}"
                        story.append(Paragraph(ach_text, normal_style))

        # Other Information
        other = data.get("other", {})
        if other and isinstance(other, dict):
            other_data = []
            for key, value in other.items():
                clean_value = clean_text(value)
                if clean_value:
                    other_data.append([f"{clean_text(key)}:", clean_value])

            if other_data:
                story.append(Paragraph("Other Information", heading_style))
                other_table = Table(other_data, colWidths=[1.5 * inch, 4 * inch])
                other_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(other_table)

        # Build PDF
        doc.build(story)
        return True

    except Exception as e:
        print(f"Error generating PDF with ReportLab: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


# === Routes ===
@app.get("/")
async def root():
    return {"message": "Resume processor API is running!", "status": "healthy"}


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read file content
        pdf_bytes = await file.read()
        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        if len(pdf_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")

        # Parse resume
        print("Parsing resume...")
        data = parse_resume(pdf_bytes)

        # Parse JSON string fields to actual objects/arrays with error handling
        for field in ['work', 'education', 'projects', 'achievements', 'certifications']:
            if field in data and isinstance(data[field], str):
                try:
                    parsed_field = json_repair.loads(data[field])
                    data[field] = parsed_field if isinstance(parsed_field, list) else []
                except Exception as e:
                    print(f"Error parsing {field}: {e}")
                    data[field] = []

        # Parse 'other' field
        if 'other' in data and isinstance(data['other'], str):
            try:
                parsed_other = json_repair.loads(data['other'])
                data['other'] = parsed_other if isinstance(parsed_other, dict) else {}
            except Exception as e:
                print(f"Error parsing other field: {e}")
                data['other'] = {}

        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = re.sub(r'[^\w\-_.]', '_', file.filename)
        pdf_filename = f"resume_{timestamp}_{unique_id}_{safe_filename}"
        pdf_path = f"static/{pdf_filename}"

        # Generate PDF
        print("Generating PDF...")
        pdf_success = generate_pdf_reportlab(data, pdf_path)

        if not pdf_success:
            # Fallback: create a simple text-based PDF
            print("Fallback: Creating simple PDF...")
            try:
                from reportlab.platypus import SimpleDocTemplate, Paragraph
                from reportlab.lib.styles import getSampleStyleSheet

                doc = SimpleDocTemplate(pdf_path, pagesize=letter)
                styles = getSampleStyleSheet()
                story = [
                    Paragraph("Resume Processing Failed", styles['Title']),
                    Paragraph("The resume was uploaded but PDF generation encountered an error.", styles['Normal']),
                    Paragraph("Please check the JSON data for extracted information.", styles['Normal'])
                ]
                doc.build(story)
                pdf_success = True
            except Exception as fallback_error:
                print(f"Fallback PDF generation also failed: {fallback_error}")
                raise HTTPException(status_code=500, detail="Failed to generate PDF")

        # Return response with direct PDF URL
        return JSONResponse({
            "message": "Resume processed successfully",
            "json": data,
            "pdf_url": f"/static/{pdf_filename}",
            "download_url": f"/download-pdf/{pdf_filename}",
            "original_filename": file.filename,
            "processed_at": datetime.now().isoformat(),
            "file_size": len(pdf_bytes)
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")


@app.get("/download-pdf/{filename}")
def download_pdf(filename: str):
    """Download endpoint for PDFs"""
    # Sanitize filename
    safe_filename = re.sub(r'[^\w\-_.]', '_', filename)
    pdf_path = f"static/{safe_filename}"

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"processed_{safe_filename}"
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Resume processor API is working correctly",
        "timestamp": datetime.now().isoformat()
    }


# Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
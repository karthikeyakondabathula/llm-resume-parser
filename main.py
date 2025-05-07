import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json_repair
from fpdf import FPDF

# === Load environment ===
env_loaded = load_dotenv()
if not env_loaded:
    print("Warning: .env file not found or failed to load.")

# === Initialize Gemini Client ===
def get_client():
    api_key = " "
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in environment variables.")
    return genai.Client(api_key=api_key)

# === Parse Resume ===
def parse_resume(content: bytes, client) -> str:
    system_instruction = '''
You are a resume parser. You will be given a resume in PDF format. Your job is to extract the relevant information from the resume and return it in JSON format.
Follow this JSON schema:
{
  "first_name": "first_name",
  "last_name": "last_name",
  "email": "email",
  "phone": "phone",
  "location": "location",
  "social": {
    "link_name1": "link_url1",
    "link_name2": "link_url2",
    "link_name3": "link_url3"
  },
  "skills": "comma separated list of skills",
  "work": "[{\"company\":\"company\",\"title\":\"title\",\"startDate\":\"start_date\",\"endDate\":\"end_date\",\"description\":\"description\"}]",
  "education": "[{\"degree\":\"degree\",\"institution\":\"institution\",\"startDate\":\"start_date\",\"endDate\":\"end_date\", \"percentage/gpa\":\"percentage/gpa\"}]",
  "projects": "[{\"name\":\"name\",\"description\":\"description\"}]",
  "certifications": "[{\"name\":\"name\",\"description\":\"description\"}]",
  "achievements": "[{\"name\":\"name\",\"description\":\"description\"}]",
  "other": "{\"Hobbies\":\"\",\"Languages\":\"\"}",
  "summary": "summary in the resume"
}
Only respond with valid JSON. Use empty strings or empty arrays if missing data.
    '''
    file_part = types.Part.from_bytes(data=content, mime_type="application/pdf")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=["Parse the resume", file_part],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=1,
            response_mime_type="application/json"
        )
    )
    return response.candidates[0].content.parts[0].text

# === Pretty PDF Writer ===
class PrettyPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        self.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)

    def header(self):
        self.set_font("DejaVu", 'B', 16)
        self.cell(0, 10, self.title, ln=True, align='C')
        self.ln(5)

    def section_title(self, title):
        self.set_font("DejaVu", 'B', 14)
        self.cell(0, 10, title, ln=True)
        self.ln(1)
        self.line(10, self.get_y(), 200, self.get_y())  # Draw horizontal line
        self.ln(5)

    def field_label(self, label, value):
        self.set_font("DejaVu", 'B', 12)
        self.cell(40, 8, f"{label}: ", ln=0)
        self.set_font("DejaVu", '', 12)
        self.multi_cell(0, 8, value if value else "")
        self.ln(1)

    def bullet_item(self, label, value):
        self.set_font("DejaVu", 'B', 12)
        self.cell(10, 8, "•", ln=0)
        self.set_font("DejaVu", '', 12)
        self.multi_cell(0, 8, f"{label}: {value}")
        self.ln(1)

    def simple_bullet(self, text):
        self.set_font("DejaVu", '', 12)
        self.cell(10, 8, "•", ln=0)
        self.multi_cell(0, 8, text)
        self.ln(1)

# === Main ===
if __name__ == "__main__":
    resume_path = " "
    output_pdf_path = "parsed_resume_pretty.pdf"

    if not os.path.isfile(resume_path):
        print(f"Error: File not found at '{resume_path}'.")
        exit(1)

    try:
        client = get_client()
        with open(resume_path, 'rb') as f:
            pdf_bytes = f.read()

        raw_json = parse_resume(pdf_bytes, client)
        data = json_repair.loads(raw_json)

        for field in ['other', 'work', 'education', 'projects', 'achievements', 'certifications']:
            if field in data:
                data[field] = json_repair.loads(data[field])

        # Load Unicode font → Download DejaVu fonts if not already
        if not os.path.isfile('DejaVuSans.ttf') or not os.path.isfile('DejaVuSans-Bold.ttf'):
            import urllib.request
            print("Downloading DejaVuSans fonts...")
            urllib.request.urlretrieve('https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf', 'DejaVuSans.ttf')
            urllib.request.urlretrieve('https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf', 'DejaVuSans-Bold.ttf')

        pdf = PrettyPDF()
        pdf.title = f"Resume: {data.get('first_name', '')} {data.get('last_name', '')}"
        pdf.add_page()

        pdf.section_title("Contact Information")
        pdf.field_label("Name", f"{data.get('first_name', '')} {data.get('last_name', '')}")
        pdf.field_label("Email", data.get("email", ""))
        pdf.field_label("Phone", data.get("phone", ""))
        pdf.field_label("Location", data.get("location", ""))

        pdf.section_title("Social Links")
        for key, url in data.get("social", {}).items():
            pdf.bullet_item(key, url)

        pdf.section_title("Summary")
        pdf.set_font("Times", '', 12)  # Set font size to 12 for content
        pdf.multi_cell(0, 8, data.get("summary", ""))
        pdf.ln(3)

        pdf.section_title("Skills")
        pdf.set_font("Times", '', 12)  # Set font size to 12 for content
        pdf.multi_cell(0, 8, data.get("skills", ""))
        pdf.ln(3)

        pdf.section_title("Work Experience")
        for work in data.get("work", []):
            pdf.field_label("Title", work.get("title", ""))
            pdf.field_label("Company", work.get("company", ""))
            pdf.field_label("Duration", f"{work.get('startDate', '')} - {work.get('endDate', '')}")
            pdf.multi_cell(0, 8, work.get("description", ""))
            pdf.ln(2)

        pdf.section_title("Education")
        for edu in data.get("education", []):
            pdf.field_label("Degree", edu.get("degree", ""))
            pdf.field_label("Institution", edu.get("institution", ""))
            pdf.field_label("Duration", f"{edu.get('startDate', '')} - {edu.get('endDate', '')}")
            pdf.field_label("GPA/Percentage", edu.get("percentage/gpa", ""))
            pdf.ln(2)

        pdf.section_title("Projects")
        for proj in data.get("projects", []):
            pdf.field_label("Name", proj.get("name", ""))
            pdf.multi_cell(0, 8, proj.get("description", ""))
            pdf.ln(2)

        pdf.section_title("Certifications")
        for cert in data.get("certifications", []):
            pdf.field_label("Name", cert.get("name", ""))
            pdf.multi_cell(0, 8, cert.get("description", ""))
            pdf.ln(2)

        pdf.section_title("Achievements")
        for ach in data.get("achievements", []):
            pdf.field_label("Name", ach.get("name", ""))
            pdf.multi_cell(0, 8, ach.get("description", ""))
            pdf.ln(2)

        pdf.section_title("Other")
        for key, value in data.get("other", {}).items():
            pdf.field_label(key, value)

        pdf.output(output_pdf_path)
        print(f"✅ Pretty PDF saved: {output_pdf_path}")

    except Exception as e:
        print(f"Error parsing resume: {e}")
        exit(1)

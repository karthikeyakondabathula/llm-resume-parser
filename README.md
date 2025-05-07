
# LLM-PDF-Parser

A **Resume Parser** powered by **Google Gemini API (genai)** that reads PDF resumes and extracts structured information in **JSON** and a **pretty printable PDF**.

> ✅ Helps companies standardize all incoming resumes to a **common format for easier evaluation**!

---

## ✨ Features

- 📝 Parse resumes in PDF format
- 🧠 Uses **Gemini 2.0 Flash model** to extract structured data
- 📄 Outputs **JSON** + a pretty **PDF** with formatted content
- 🎯 CLI tool with simple arguments
- 💼 Companies can collect resumes in different formats and convert them all into a **single standardized structure** for ATS, HR dashboards, or internal systems.

Includes example files:
- `sample_input.pdf` → Example resume
- `sample_output.pdf` → Example output from parser

---

## 🏗️ Setup

1. **Clone the repo**
   ```bash
   git clone <repo-url>
   cd llm-pdf-parser
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # on Linux/macOS
   .\venv\Scripts\activate  # on Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set your Google API Key**

You can either:

✅ Put it in a `.env` file:
```
GOOGLE_API_KEY=your_api_key_here
```

or

✅ Export as environment variable (temporary for session):

- On Linux/macOS:
  ```bash
  export GOOGLE_API_KEY=your_api_key_here
  ```
- On Windows (CMD):
  ```cmd
  set GOOGLE_API_KEY=your_api_key_here
  ```
- On Windows (PowerShell):
  ```powershell
  $env:GOOGLE_API_KEY="your_api_key_here"
  ```

---

## 🚀 Running the parser

Run the script using **command-line arguments**:

```bash
python main.py --input sample_input.pdf --output_json parsed_resume.json --output_pdf sample_output.pdf
```

✅ `--input`: Path to input PDF resume  
✅ `--output_json`: (optional) Output JSON filename (default: `parsed_resume.json`)  
✅ `--output_pdf`: (optional) Output PDF filename (default: `output.pdf`)



---

## 💡 Why use this?

✅ Standardizes resumes from **multiple formats & templates** into a **common JSON schema**  
✅ Makes it easy to integrate into **Applicant Tracking Systems (ATS)** or other HR pipelines  
✅ Output PDF lets you **reformat resumes for internal review, sharing, or printing**

---

## 📌 Notes

- Requires **Google Gemini API Key** (Generative AI access)
- Supports multilingual text with **DejaVu fonts** (handles Unicode)

---

## 🏆 Example

Input: `sample_input.pdf`  
Output: `parsed_resume.json` + `sample_output.pdf`

---

## 🙌 Contribution

Feel free to fork, add improvements, or adapt for other document types!

MIT License.

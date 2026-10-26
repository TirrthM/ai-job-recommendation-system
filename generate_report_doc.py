import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_report():
    doc = docx.Document()

    # Page Margins: 1 inch everywhere
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    # Title
    title = doc.add_paragraph()
    title_run = title.add_run("AI-Based Job Recommendation System")
    title_run.font.size = Pt(24)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0x11, 0x18, 0x27)
    title.paragraph_format.space_after = Pt(2)

    # Subtitle
    sub = doc.add_paragraph()
    sub_run = sub.add_run("Comprehensive Project & Pipeline Engineering Report · Recommender Systems")
    sub_run.font.size = Pt(12)
    sub_run.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)
    sub.paragraph_format.space_after = Pt(16)

    # Divider line
    p_div = doc.add_paragraph()
    p_div_run = p_div.add_run("―" * 55)
    p_div_run.font.color.rgb = RGBColor(0xD1, 0xD5, 0xDB)
    p_div.paragraph_format.space_after = Pt(18)

    # Helper for headings
    def add_h1(text):
        h = doc.add_paragraph()
        run = h.add_run(text)
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A) # Deep navy
        h.paragraph_format.space_before = Pt(18)
        h.paragraph_format.space_after = Pt(6)
        return h

    def add_h2(text):
        h = doc.add_paragraph()
        run = h.add_run(text)
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(4)
        return h

    def add_bullet(p_or_text, bold_prefix="", text=""):
        p = doc.add_paragraph(style='List Bullet')
        if bold_prefix:
            r1 = p.add_run(bold_prefix)
            r1.font.bold = True
            r1.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
        r2 = p.add_run(text)
        r2.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
        p.paragraph_format.space_after = Pt(3)
        return p

    def add_para(text):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.font.size = Pt(11)
        r.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.15
        return p

    def style_table(table, col_widths, headers, data):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        # Header Row
        hdr_cells = table.rows[0].cells
        for i, h_text in enumerate(headers):
            hdr_cells[i].text = h_text
            set_cell_background(hdr_cells[i], "1E3A8A")
            set_cell_margins(hdr_cells[i], 120, 120, 150, 150)
            p = hdr_cells[i].paragraphs[0]
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(10)
            p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        # Data Rows
        for r_idx, row_data in enumerate(data):
            row_cells = table.rows[r_idx + 1].cells
            fill_color = "F9FAFB" if r_idx % 2 == 1 else "FFFFFF"
            for c_idx, val in enumerate(row_data):
                row_cells[c_idx].text = str(val)
                set_cell_background(row_cells[c_idx], fill_color)
                set_cell_margins(row_cells[c_idx], 100, 100, 150, 150)
                p = row_cells[c_idx].paragraphs[0]
                p.runs[0].font.size = Pt(10)
                p.runs[0].font.color.rgb = RGBColor(0x37, 0x41, 0x51)

        # Column widths
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Inches(width)

    # 1. Executive Summary
    add_h1("1. Project Overview & Executive Summary")
    add_para(
        "The AI-Based Job Recommendation System is an intelligent end-to-end platform engineered to bridge "
        "the gap between alumni job seekers and industry job openings. Instead of requiring candidates to "
        "spend hours manually searching across disparate job boards, the system analyzes candidate skill sets, "
        "professional background (bio), and years of experience, and uses Machine Learning to predict the best-fitting "
        "job role, match corresponding vacancies from an active database, and push automated match alerts to the user."
    )
    add_para(
        "The system combines Natural Language Processing (TF-IDF Vectorization) with Probabilistic Supervised "
        "Learning (Multinomial Naive Bayes) alongside deterministic Rule-Based Experience Verification. "
        "All data and notifications are persisted in an enterprise NoSQL database (MongoDB)."
    )

    # 2. Pipeline Architecture
    add_h1("2. End-to-End System Pipeline (5 Stages)")
    add_para("The system functions through a sequential 5-stage pipeline:")

    add_h2("Stage 1: Data Ingestion & Storage (MongoDB)")
    add_para(
        "Candidate profiles and job descriptions are maintained as structured documents inside MongoDB (alumni_database):"
    )
    add_bullet("", "profiles collection: ", "Contains 99 candidate records with attributes: name, skills (comma-separated), experience (years), bio, location, and email.")
    add_bullet("", "jobs collection: ", "Contains 99 job vacancy records with attributes: title (role target), company, required_skills, experience_required, location, and description.")
    add_bullet("", "notifications collection: ", "Stores system-generated recommendation alerts when high-confidence matches are found.")

    add_h2("Stage 2: Feature Extraction via TF-IDF Vectorization")
    add_para(
        "Machine learning algorithms cannot directly process raw text. We convert raw skill keywords and descriptions "
        "into dense numeric vectors using Term Frequency – Inverse Document Frequency (TF-IDF):"
    )
    add_bullet("", "Term Frequency (TF): ", "Measures the relative frequency of a skill keyword within a job requirement or candidate profile.")
    add_bullet("", "Inverse Document Frequency (IDF): ", "Penalizes frequent generic words (such as 'and', 'the', 'with') and scales up rare, domain-specific technical competencies (such as 'PyTorch', 'Kubernetes', 'Docker').")
    add_para(
        "Formula: TF-IDF(t, d, D) = TF(t, d) × log(|D| / (1 + |{d ∈ D : t ∈ d}|))\n"
        "This creates a mathematical vector space representing the technical profile of each candidate and job."
    )

    add_h2("Stage 3: Probabilistic Role Classification (Multinomial Naive Bayes)")
    add_para(
        "A Multinomial Naive Bayes (MNB) classifier is trained on the TF-IDF feature vectors of all database jobs. "
        "When candidate skills and bio are evaluated:"
    )
    add_bullet("", "Posterior Probability: ", "The model calculates P(Role | Candidate_Skills) for all known job roles using Bayes' Theorem:")
    add_para("        P(Role | Skills) ∝ P(Role) × ∏ P(skill_i | Role)")
    add_bullet("", "Prediction & Confidence: ", "The job role yielding the highest posterior probability is predicted. The associated probability serves as the AI Confidence Score.")

    add_h2("Stage 4: Rule-Based Qualification & Experience Post-Filtering")
    add_para(
        "Pure machine learning models often ignore hard constraints (e.g., predicting 'Lead Cloud Architect' "
        "for a fresh graduate with 0 years of experience who listed cloud buzzwords in their resume). "
        "To prevent misleading recommendations, our pipeline implements a post-classification deterministic filter:"
    )
    add_bullet("", "Hard Constraint Rule: ", "Candidate Experience ≥ Job Minimum Experience Required.")
    add_bullet("", "Fallback Handling: ", "If the candidate does not have enough years of experience for available openings under the predicted title, the system flags the experience shortfall clearly rather than issuing an invalid recommendation.")

    add_h2("Stage 5: Notification Persistence & Push System")
    add_para(
        "Upon identifying a qualified match, a structured notification document is written to the database with fields: "
        "user_name, job_title, company, location, description, and status ('unread'). This notification is immediately "
        "visible in the web dashboard's Alerts management console."
    )

    # 3. RS Theory
    add_h1("3. Recommender Systems Theory & Categorization")
    add_para(
        "In Recommender System (RS) theory, filtering strategies are divided into three primary categories:"
    )

    # RS Table
    table_rs = doc.add_table(rows=4, cols=3)
    table_rs_widths = [1.8, 3.4, 1.3]
    table_rs_headers = ["Paradigm", "Methodology & Characteristics", "Applied in Project?"]
    table_rs_data = [
        ["Content-Based Filtering (CBF)", "Recommends items based on intrinsic item features (skills, requirements) and user profiles. Does NOT require user interaction logs.", "YES (Primary Engine)"],
        ["Collaborative Filtering (CF)", "Recommends items based on user behavior patterns, ratings, clicks, or purchase co-occurrence matrices.", "NO (No user rating data available)"],
        ["Hybrid Recommender System", "Combines Content-Based and Collaborative mechanisms to balance individual features with crowd trends.", "NO (Out of current scope)"]
    ]
    style_table(table_rs, table_rs_widths, table_rs_headers, table_rs_data)

    add_para("")
    add_h2("Why Content-Based Filtering Solves the 'Cold-Start' Problem:")
    add_para(
        "In university alumni or enterprise hiring scenarios, newly graduated candidates have no prior job application "
        "or rating history. Collaborative Filtering completely fails in such situations because it relies on past user interactions. "
        "Content-Based Filtering directly compares user profile content against job posting requirements, ensuring that new candidates "
        "receive instant, highly accurate recommendations from day one."
    )

    # 4. Tech Stack Table
    add_h1("4. Technology Stack & Component Justification")
    table_tech = doc.add_table(rows=7, cols=3)
    table_tech_widths = [1.8, 1.7, 3.0]
    table_tech_headers = ["Layer / Component", "Technology Used", "Role in System"]
    table_tech_data = [
        ["Programming Language", "Python 3.11", "Unified backend, data science pipeline, and web server."],
        ["Machine Learning", "scikit-learn", "TF-IDF Vectorizer, Multinomial Naive Bayes, Label Encoder."],
        ["Database Management", "MongoDB (NoSQL)", "Stores flexible JSON schema for jobs, profiles, and alerts."],
        ["Database Driver", "PyMongo", "Fast, thread-safe Python interface to MongoDB collections."],
        ["Web Application Framework", "Flask", "Lightweight HTTP server serving REST API endpoints."],
        ["Frontend User Interface", "HTML5, CSS3, Vanilla JS", "Responsive, professional, zero-bloat interactive UI."]
    ]
    style_table(table_tech, table_tech_widths, table_tech_headers, table_tech_data)

    # 5. File Structure
    add_h1("5. Project Repository Structure")
    add_para("The codebase is organized into cleanly separated functional modules:")
    code_text = (
        "ai-job-recommendation/\n"
        "├── config.py              # MongoDB connection URI & database settings\n"
        "├── engine.py              # ML Engine: TF-IDF, Naive Bayes classifier & filters\n"
        "├── app.py                 # Flask server & REST API endpoints\n"
        "├── import_data.py         # Batch data ingestion script for JSON -> MongoDB\n"
        "├── AIjobrecommendation.py # Original standalone CLI recommendation script\n"
        "├── jobs.json              # 99 curated job vacancy records\n"
        "├── profiles.json          # 99 alumni candidate profiles\n"
        "├── requirements.txt       # Python project dependencies\n"
        "├── templates/\n"
        "│   └── index.html         # Web dashboard layout\n"
        "└── static/\n"
        "    ├── style.css          # Clean professional CSS (with Light/Dark modes)\n"
        "    └── app.js             # Client-side reactivity, API calls & modal management"
    )
    p_code = doc.add_paragraph()
    r_code = p_code.add_run(code_text)
    r_code.font.name = 'Consolas'
    r_code.font.size = Pt(9.5)
    r_code.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    p_code.paragraph_format.left_indent = Inches(0.2)

    # 6. REST API Reference
    add_h1("6. REST API Endpoints Specification")
    table_api = doc.add_table(rows=8, cols=3)
    table_api_widths = [1.2, 2.5, 2.8]
    table_api_headers = ["Method", "Endpoint", "Description"]
    table_api_data = [
        ["GET", "/api/stats", "Returns total job, profile, notification counts and top skills/roles."],
        ["GET", "/api/jobs", "Retrieves job postings (supports query 'q' and 'role' parameters)."],
        ["GET", "/api/profiles", "Retrieves candidate profiles (supports keyword search)."],
        ["GET", "/api/notifications", "Fetches generated recommendation alerts in reverse chronological order."],
        ["GET", "/api/notification-detail", "Returns complete candidate profile and matched job data for modal view."],
        ["POST", "/api/recommend", "Executes AI inference for input skills, bio, experience."],
        ["POST", "/api/run-batch", "Executes recommendation for all 99 candidates in database."],
    ]
    style_table(table_api, table_api_widths, table_api_headers, table_api_data)

    # 7. Step by Step Guide
    add_h1("7. Step-by-Step Setup & Execution Guide")
    add_para("To run and test the complete system locally:")
    add_bullet("1. Navigate to Project Directory: ", "cd 'd:\\RS Mini Project\\ai-job-recommendation'")
    add_bullet("2. Activate Virtual Environment: ", ".\\venv\\Scripts\\Activate.ps1")
    add_bullet("3. Ingest Data into MongoDB: ", "python import_data.py (loads 99 jobs & 99 profiles)")
    add_bullet("4. Launch Web Server: ", "python app.py (starts dashboard on http://127.0.0.1:5000)")
    add_bullet("5. Test Live Recommender: ", "Select any candidate or type skills -> Click 'Run AI Recommendation'.")
    add_bullet("6. Test Batch Matching: ", "Navigate to Alerts tab -> Click 'Run Batch' to evaluate all 99 profiles.")
    add_bullet("7. Test Interactive Details: ", "Click any row in the Alerts table to open the full side-by-side profile and job inspection modal.")

    # 8. Limitations and Future Scope
    add_h1("8. Limitations & Future Roadmap")
    add_bullet("", "Dataset Size: ", "The current prototype uses 99 curated jobs and profiles. Scaling up to 10,000+ postings will enhance classification coverage.")
    add_bullet("", "Semantic Embeddings: ", "TF-IDF relies on exact term overlap. Transitioning to dense vector embeddings (e.g., Sentence-BERT or OpenAI text-embedding) would enable true semantic matching (e.g., recognizing that 'NLP' implies 'Text Mining' and 'Language Models').")
    add_bullet("", "Explicit Feedback Loop: ", "Adding user actions ('Apply', 'Bookmark', 'Dismiss') will enable Reinforcement Learning / Collaborative re-ranking over time.")

    # Save
    out_path = r"d:\RS Mini Project\ai-job-recommendation\AI_Job_Recommendation_Project_Report.docx"
    doc.save(out_path)
    print(f"Report successfully saved to: {out_path}")

if __name__ == '__main__':
    create_report()

import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

OUTPUT_DIR = r"c:\Users\hp\Desktop\cv_ATS\synsetic_data"

def ensure_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def create_01_clean_single_column():
    """Gold standard. Single column, standard headers, standard fonts, extractable text."""
    filepath = os.path.join(OUTPUT_DIR, "01_clean_single_column.pdf")
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 750, "Jane Doe")
    c.setFont("Helvetica", 12)
    c.drawString(72, 730, "jane.doe@example.com | 555-0101")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 690, "Experience")
    c.setFont("Helvetica", 12)
    c.drawString(72, 670, "Software Engineer at TechCorp (2020-Present)")
    c.drawString(72, 650, "- Developed scalable backend microservices.")
    c.drawString(72, 630, "- Improved ATS matching algorithms by 40%.")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 590, "Education")
    c.setFont("Helvetica", 12)
    c.drawString(72, 570, "B.S. Computer Science, University of Example (2016-2020)")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 530, "Skills")
    c.setFont("Helvetica", 12)
    c.drawString(72, 510, "Python, FastAPI, ReportLab, Docker")
    
    c.save()
    print(f"Created {filepath}")

def create_02_multi_column_overlap():
    """Uses a complex two-column layout. Tests `has_multi_column_layout`."""
    filepath = os.path.join(OUTPUT_DIR, "02_multi_column_overlap.pdf")
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 750, "John Smith - Two Column Layout")
    
    # Left column
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 700, "Experience (Left Column)")
    c.setFont("Helvetica", 12)
    c.drawString(72, 680, "Company A")
    c.drawString(72, 660, "- Did some work here.")
    
    # Right column (overlaps Y, different X)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(350, 700, "Education (Right Column)")
    c.setFont("Helvetica", 12)
    c.drawString(350, 680, "University B")
    c.drawString(350, 660, "B.A. Something")
    
    c.save()
    print(f"Created {filepath}")

def create_03_table_heavy():
    """Embeds education and skills directly inside a drawn PDF table. Tests `has_tables`."""
    filepath = os.path.join(OUTPUT_DIR, "03_table_heavy.pdf")
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>Table Heavy Resume</b>", styles['Title']))
    elements.append(Spacer(1, 0.2 * inch))
    
    data = [
        ['Degree', 'Institution', 'Year'],
        ['B.S. CS', 'State Uni', '2019'],
        ['M.S. AI', 'Tech Institute', '2021']
    ]
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    
    elements.append(Paragraph("<b>Education History:</b>", styles['Heading2']))
    elements.append(t)
    
    doc.build(elements)
    print(f"Created {filepath}")

def create_04_text_in_images():
    """Renders a graphical skill bar instead of text. Tests `has_text_in_images` (vector shapes)."""
    filepath = os.path.join(OUTPUT_DIR, "04_text_in_images.pdf")
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 750, "Visual Resume Designer")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 700, "Skills (Visual)")
    
    # Draw vector graphics (skill bars)
    # Python
    c.setFont("Helvetica", 12)
    c.drawString(72, 670, "Python")
    c.setFillColorRGB(0, 0, 1) # Blue filled rect
    c.rect(150, 670, 200, 10, fill=1) 
    
    # React
    c.setFillColorRGB(0, 0, 0)
    c.drawString(72, 640, "React")
    c.setFillColorRGB(1, 0, 0) # Red filled rect
    c.rect(150, 640, 150, 10, fill=1)
    
    c.save()
    print(f"Created {filepath}")

def create_05_scanned_no_text():
    """Simulates a scanned document using an image with no text layer."""
    filepath = os.path.join(OUTPUT_DIR, "05_scanned_no_text.pdf")
    # First create a temporary image using Pillow, then embed it into the PDF.
    temp_img_path = os.path.join(OUTPUT_DIR, "temp_scan.png")
    img = PILImage.new('RGB', (800, 1000), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # Just draw some text on the IMAGE, not the PDF
    d.text((50, 50), "SCANNED RESUME DATA", fill=(0,0,0))
    d.text((50, 100), "No extractable text here!", fill=(0,0,0))
    img.save(temp_img_path)
    
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawImage(temp_img_path, 0, 0, width=letter[0], height=letter[1])
    c.save()
    
    os.remove(temp_img_path)
    print(f"Created {filepath}")

def create_06_creative_headers():
    """Standard single-column resume, but uses creative section headers. Tests missing_sections."""
    filepath = os.path.join(OUTPUT_DIR, "06_creative_headers.pdf")
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 750, "Creative Candidate")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 690, "My Journey") # Instead of Experience
    c.setFont("Helvetica", 12)
    c.drawString(72, 670, "I did some things at TechCorp (2020-Present)")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 590, "Where I Studied") # Instead of Education
    c.setFont("Helvetica", 12)
    c.drawString(72, 570, "University of Example (2016-2020)")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 530, "What I Know") # Instead of Skills
    c.setFont("Helvetica", 12)
    c.drawString(72, 510, "Python, Magic, Sorting Algorithms")
    
    c.save()
    print(f"Created {filepath}")

def create_07_header_footer_contact():
    """Places contact info only in headers. Tests contact_info_in_header_footer."""
    filepath = os.path.join(OUTPUT_DIR, "07_header_footer_contact.pdf")
    c = canvas.Canvas(filepath, pagesize=letter)
    
    # Top 5% of the page
    c.setFont("Helvetica", 10)
    c.drawString(72, letter[1] - 30, "Email: hidden.header@example.com | Phone: 555-9999")
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 700, "Normal Person")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 650, "Experience")
    c.setFont("Helvetica", 12)
    c.drawString(72, 630, "Standard content here.")
    
    c.save()
    print(f"Created {filepath}")

def main():
    ensure_dir()
    create_01_clean_single_column()
    create_02_multi_column_overlap()
    create_03_table_heavy()
    create_04_text_in_images()
    create_05_scanned_no_text()
    create_06_creative_headers()
    create_07_header_footer_contact()
    print("\n✅ All ATS test fixtures generated successfully.")

if __name__ == "__main__":
    main()

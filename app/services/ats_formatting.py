import pymupdf
import re
from typing import List, Set, Tuple
from app.core.models import ATSFormattingReport

class DeterministicATSChecker:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def analyze(self) -> ATSFormattingReport:
        doc = pymupdf.open(self.pdf_path)
        report = ATSFormattingReport()
        
        report.page_count = doc.page_count
        
        all_text = ""
        fonts: Set[Tuple[str, float]] = set()
        
        email_regex = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
        phone_regex = re.compile(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]')
        
        contact_in_body = False
        contact_in_header_footer = False
        
        for pno in range(doc.page_count):
            page = doc[pno]
            
            # Check for tables
            tabs = page.find_tables()
            if tabs and len(tabs.tables) > 0:
                report.has_tables = True
                
            # Check for images / vector graphics which could hide text/skill bars
            # Only flag if they have meaningful dimensions (not just thin divider lines or tiny bullets)
            image_info = page.get_image_info()
            for img in image_info:
                bbox = img["bbox"]
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                if width > 30 and height > 30:
                    report.has_text_in_images = True
                    break
                    
            if not report.has_text_in_images:
                drawings = page.get_drawings()
                for d in drawings:
                    bbox = d["rect"]
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]
                    if width > 30 and height > 15:
                        report.has_text_in_images = True
                        break
                
            text_dict = page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)
            blocks = text_dict.get("blocks", [])
            
            # Column detection
            # Check if we have text blocks that overlap vertically but are separated horizontally
            text_blocks = []
            for b in blocks:
                if "lines" not in b: 
                    continue
                bbox = b["bbox"]
                # Only consider blocks with significant height and width to avoid noise
                if bbox[3] - bbox[1] > 15 and bbox[2] - bbox[0] > 50:
                    text_blocks.append(bbox)
                    
            if not report.has_multi_column_layout:
                for i, b1 in enumerate(text_blocks):
                    for b2 in text_blocks[i+1:]:
                        # vertical overlap: max(y0, y0) < min(y1, y1)
                        y_overlap = max(b1[1], b2[1]) < min(b1[3], b2[3])
                        # horizontal separation: b1_x1 < b2_x0 or b2_x1 < b1_x0
                        x_separated = b1[2] < b2[0] or b2[2] < b1[0]
                        if y_overlap and x_separated:
                            report.has_multi_column_layout = True
                            break
                    if report.has_multi_column_layout:
                        break
            
            # Font collection & Text extraction
            page_text = ""
            for b in blocks:
                if "lines" not in b: 
                    continue
                bbox = b["bbox"]
                
                # Check if block is in the top 10% or bottom 10% of the page
                is_header_footer = False
                if bbox[1] < page.rect.height * 0.1 or bbox[3] > page.rect.height * 0.9:
                    is_header_footer = True
                    
                block_text = ""
                for line in b["lines"]:
                    for span in line["spans"]:
                        fonts.add((span["font"], round(span["size"], 1)))
                        block_text += span["text"] + " "
                
                page_text += block_text + "\n"
                all_text += block_text + "\n"
                
                # Contact info check
                has_email = bool(email_regex.search(block_text))
                has_phone = bool(phone_regex.search(block_text))
                
                if has_email or has_phone:
                    if is_header_footer:
                        contact_in_header_footer = True
                    else:
                        contact_in_body = True
                        
        doc.close()
        
        # Scanned PDF check
        if len(all_text.strip()) < 50: # If less than 50 chars of extractable text, probably scanned
            report.is_scanned_pdf = True
            
        report.font_count = len(fonts)
        report.word_count = len(all_text.split())
        
        # If contact info was ONLY found in header/footer, flag it
        if contact_in_header_footer and not contact_in_body:
            report.contact_info_in_header_footer = True
            
        # Missing Sections detection
        all_text_lower = all_text.lower()
        standard_sections = ["summary", "experience", "education", "skills", "projects"]
        missing = []
        for sec in standard_sections:
            # Look for the section title anywhere within a short heading-like line (under 40 chars)
            if not re.search(r'^.{0,40}\b' + sec + r'\b', all_text_lower, re.MULTILINE):
                missing.append(sec.capitalize())
        report.missing_sections = missing
        
        return report

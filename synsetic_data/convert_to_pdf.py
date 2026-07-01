import os
import glob
from fpdf import FPDF

def create_pdf_from_text(input_file, output_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=10)

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Strip metadata and scoring tips at the bottom
    cleaned_lines = []
    for line in lines:
        if line.startswith("# ── TEST METADATA"):
            break
        cleaned_lines.append(line)

    for line in cleaned_lines:
        # FPDF encodes strings as latin-1 by default, handle encoding nicely or fallback to replace
        pdf.cell(0, 5, txt=line.encode('latin-1', 'replace').decode('latin-1').rstrip('\n'), ln=True)

    pdf.output(output_file)
    print(f"Created {output_file}")

def main():
    directory = r"c:\Users\hp\Desktop\cv_ATS\synsetic_data"
    txt_files = glob.glob(os.path.join(directory, "*.txt"))

    for txt_file in txt_files:
        pdf_file = txt_file.replace(".txt", ".pdf")
        create_pdf_from_text(txt_file, pdf_file)

if __name__ == "__main__":
    main()

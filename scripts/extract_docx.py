#!/usr/bin/env python3
"""Extract text from DOCX files for processing."""
import docx
from pathlib import Path
import json

def extract_docx_text(filepath):
    """Extract all text from a DOCX file."""
    try:
        doc = docx.Document(filepath)
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text.strip())
        return '\n\n'.join(text)
    except Exception as e:
        return f"Error reading {filepath}: {e}"

def main():
    base_dir = Path(__file__).parent.parent
    thesis_dir = base_dir / 'thesis'
    
    files = {
        'thesis_structure': thesis_dir / 'Thesis Structure.docx',
        'synopsis': thesis_dir / 'BAMoT-Final-synopis.docx',
        'research_1': thesis_dir / 'Research-Part-1.docx',
        'research_2': thesis_dir / 'Research-Part-2.docx',
        'research_3': thesis_dir / 'Research-Part-3.docx',
    }
    
    extracted = {}
    for key, filepath in files.items():
        if filepath.exists():
            print(f"Extracting {filepath.name}...")
            extracted[key] = extract_docx_text(filepath)
        else:
            print(f"⚠️  {filepath.name} not found")
            extracted[key] = None
    
    # Save extracted text
    output_file = thesis_dir / 'extracted_content.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Extracted content saved to {output_file}")
    
    # Also save as readable text files
    for key, content in extracted.items():
        if content:
            txt_file = thesis_dir / f'{key}_extracted.txt'
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  → {txt_file.name}")

if __name__ == '__main__':
    main()


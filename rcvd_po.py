import os
import re
import glob
import subprocess
import sys

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

# ==========================================
# PUBLIC-SAFE EXTENSIBLE VENDOR MAPPING DICTIONARY
# Replace these placeholders with your actual vendor names and abbreviations.
# ==========================================
VENDOR_MAPPING = {
    "SAMPLE VENDOR ONE TRADING": "VENDOR-A",
    "SAMPLE VENDOR TWO IMPORT": "VENDOR-B",
    "SAMPLE VENDOR THREE EXPO": "VENDOR-C",
    "SAMPLE VENDOR FOUR PRODUCTS": "VENDOR-D",
    "SAMPLE VENDOR FIVE LIMITED": "VENDOR-E",
    # ADD NEW VENDORS HERE:
    # "YOUR VENDOR NAME": "SHORTNAME",
}

def normalize_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def extract_po_from_filename(filename):
    # Matches 'PO' followed by 7 to 13 digits
    match = re.search(r'PO[-_\s]*(\d{7,13})', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def clean_po_number(po_str):
    # Remove leading zeros before the non-zero digit
    return str(int(po_str)) if po_str.isdigit() else po_str

def process_fpo_pdf(pdf_path):
    print(f"\n[INFO] Processing FPO PDF: {pdf_path}")
    filename = os.path.basename(pdf_path)
    file_po = extract_po_from_filename(filename)
    
    if not file_po:
        print(f"[WARNING] Could not extract PO number from filename: {filename}")
        file_po = input("Please enter the PO number manually: ").strip()
    
    clean_po = clean_po_number(file_po)
    
    if not PdfReader:
        print("[ERROR] pypdf or PyPDF2 is not installed. Please install via 'pip install pypdf'.")
        sys.exit(1)
        
    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        print(f"[ERROR] Failed to read PDF {filename}: {e}")
        return None, None
    
    page_po_list = []
    page_xfty_list = []
    page_vendor_list = []
    
    for page in reader.pages:
        text = page.extract_text() or ""
        
        # Extract PO #
        po_match = re.search(r'(?:PO\s*#|Buyer\'?s\s*PO\s*#)\s*[:#]?\s*(\d{7,13})', text, re.IGNORECASE)
        if not po_match:
            po_match = re.search(r'\b(\d{7,13})\b', text)
        page_po = po_match.group(1) if po_match else None
        page_po_list.append(page_po)
        
        # Extract XFTY date (Format: MM-DD-YYYY or similar)
        xfty_match = re.search(r'XFTY\s*[:]?\s*(\d{2}[-/]\d{2}[-/]\d{4})', text, re.IGNORECASE)
        if not xfty_match:
            xfty_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{4})', text)
        page_xfty = xfty_match.group(1) if xfty_match else "MM-DD-YYYY"
        page_xfty_list.append(page_xfty)
        
        # Extract Vendor name
        vendor_match = re.search(r'Vendor\s+([A-Za-z0-9\s,\.-]+)', text, re.IGNORECASE)
        if vendor_match:
            vendor_lines = [l.strip() for l in vendor_match.group(1).split('\n') if l.strip()]
            page_vendor = vendor_lines[0] if vendor_lines else "UNKNOWN VENDOR"
        else:
            page_vendor = "UNKNOWN VENDOR"
        page_vendor_list.append(normalize_text(page_vendor))

    # Consistency checks & mapping
    extracted_vendor = page_vendor_list[0] if page_vendor_list else "UNKNOWN VENDOR"
    converted_vendor = extracted_vendor
    for v_key, v_val in VENDOR_MAPPING.items():
        if v_key in extracted_vendor.upper():
            converted_vendor = v_val
            break
            
    xfty_date = page_xfty_list[0] if page_xfty_list else "MM-DD-YYYY"

    # Prompt user for Customer name
    customer_name = input("Please provide the customer name (e.g., CUSTOMER A): ").strip().upper()
    while not customer_name:
        print("[WARNING] Customer name cannot be empty.")
        customer_name = input("Please provide the customer name: ").strip().upper()

    # Combined info format: PO {clean_po}- {customer_name}-{converted_vendor}- {xfty_date}
    combined_info = f"PO {clean_po}- {customer_name}-{converted_vendor}- {xfty_date}"
    
    # Display all extracted details at once for single confirmation
    print("\n========================================")
    print("        FPO EXTRACTION SUMMARY          ")
    print("========================================")
    print(f" Filename PO #      : {file_po}")
    print(f" Clean PO #         : {clean_po}")
    print(f" All Pages POs      : {page_po_list}")
    print(f" XFTY Date          : {xfty_date}")
    print(f" Extracted Vendor   : {extracted_vendor}")
    print(f" Converted Vendor   : {converted_vendor}")
    print(f" Customer Name      : {customer_name}")
    print("----------------------------------------")
    print(f" Combined FPO Info  : {combined_info}")
    print("========================================")
    
    confirm = input("Are all extracted details and combined info correct? (Y/N): ").strip().upper()
    if confirm != 'Y':
        print("[INFO] FPO processing aborted by user due to verification mismatch.")
        return None, None
        
    return combined_info, os.path.dirname(pdf_path)

def main():
    print("=== FPO Receiving Automation Script (Public Safe) ===")
    default_dir = r"C:\Path\To\FPO\Directory"
    fpo_dir = input(f"Enter FPO directory path [Default: {default_dir}]: ").strip()
    if not fpo_dir:
        fpo_dir = default_dir
        
    if not os.path.exists(fpo_dir):
        print(f"[ERROR] Directory does not exist: {fpo_dir}")
        sys.exit(1)
        
    pdf_files = glob.glob(os.path.join(fpo_dir, "**", "*PO*[0-9]*.pdf"), recursive=True)
    if not pdf_files:
        pdf_files = glob.glob(os.path.join(fpo_dir, "*.pdf"))
        
    if not pdf_files:
        print("[ERROR] No PDF files found in directory or subdirectories.")
        sys.exit(1)
        
    print("\nMatching FPO PDF files found:")
    for idx, pdf in enumerate(pdf_files, 1):
        print(f"  {idx}. {pdf}")
        
    selection = input("\nEnter the number(s) of the FPO file(s) to process (comma separated, or press Enter for all): ").strip()
    
    selected_pdfs = []
    if not selection:
        selected_pdfs = pdf_files
    else:
        indices = [int(x.strip()) - 1 for x in selection.split(',') if x.strip().isdigit()]
        selected_pdfs = [pdf_files[i] for i in indices if 0 <= i < len(pdf_files)]
        
    for pdf_path in selected_pdfs:
        result, folder_path = process_fpo_pdf(pdf_path)
        if result and folder_path:
            parent_dir = os.path.dirname(folder_path)
            new_folder_path = os.path.join(parent_dir, result)
            try:
                os.rename(folder_path, new_folder_path)
                print(f"[SUCCESS] Renamed folder to: {new_folder_path}")
                subprocess.run(['explorer', new_folder_path])
            except Exception as e:
                print(f"[ERROR] Failed to rename folder: {e}")
                
    print("\n=== RCVD FPO Process Completed ===")

if __name__ == "__main__":
    main()

import pandas as pd
import json
from pathlib import Path
import sys

# Configure console encoding to avoid errors on Windows terminals
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

excel_path = Path("BAM NPA.xlsx")
json_path = Path("properties.json")

print("[System] กำลังอ่านข้อมูลจากไฟล์ Excel...")

if not excel_path.exists():
    print(f"[-] ไม่พบไฟล์ข้อมูล {excel_path.resolve()}")
    sys.exit(1)

try:
    df = pd.read_excel(excel_path)
    
    # Fill NaN values with safe defaults to prevent JSON validation errors
    # Replace NaN in text fields with empty strings, and numeric fields with None or 0
    df = df.where(pd.notnull(df), None)
    
    # Convert list/dict strings back to list if needed (like campaigns)
    # Convert dataframe to dictionary records
    records = df.to_dict(orient="records")
    
    # Save as JSON file
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        
    print(f"[Success] แปลงข้อมูลสำเร็จ! บันทึกข้อมูล {len(records)} รายการลงไฟล์: {json_path.resolve()}")
except Exception as e:
    print(f"[-] เกิดข้อผิดพลาดในการแปลงข้อมูล: {e}")
    sys.exit(1)

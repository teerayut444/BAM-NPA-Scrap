import re
import time
import argparse
import random
import json
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

EXCEL_FILE = Path("BAM NPA.xlsx")

URL_TEMPLATE = "https://www.bam.co.th/th/npa/property/search?types=บ้านเดี่ยว,ทาวน์เฮ้าส์,คอนโดมิเนียม,อาคารพาณิชย์,ที่ดินเปล่า,โรงงาน,ที่เกษตร,อพาร์ทเม้นท์,อาคารสำนักงาน,พื้นที่สำนักงาน,โรงแรมและรีสอร์ท,Public+Service,สังหาริมทรัพย์,อื่นๆ&page={page_num}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def clean_whitespace(val: str) -> str:
    if not val:
        return ""
    return re.sub(r"\s+", " ", str(val)).strip()

def get_clean_area(area_dict, key):
    if not area_dict or not isinstance(area_dict, dict):
        return ""
    val = area_dict.get(key)
    if val is None or str(val).lower() == "undefined":
        return ""
    return val

def extract_properties_json(html: str) -> list[dict]:
    # Find where properties list starts
    start_idx = html.find('\\"properties\\":')
    if start_idx == -1:
        start_idx = html.find('"properties":')
    if start_idx == -1:
        return []
        
    # Find the first '[' after the key
    bracket_start = html.find('[', start_idx)
    if bracket_start == -1:
        return []
        
    # Find the matching closing bracket
    balance = 0
    bracket_end = -1
    for i in range(bracket_start, len(html)):
        char = html[i]
        if char == '[':
            balance += 1
        elif char == ']':
            balance -= 1
            if balance == 0:
                bracket_end = i
                break
                
    if bracket_end == -1:
        return []
        
    json_str = html[bracket_start:bracket_end+1]
    
    # Unescape the JSON string (replace \" with ")
    json_str = json_str.replace('\\"', '"').replace('\\/', '/')
    
    try:
        return json.loads(json_str)
    except Exception as e:
        print("เกิดข้อผิดพลาดในการแปลงข้อมูล JSON ของทรัพย์สิน:", e)
        return []

def extract_pagination_info(html: str) -> tuple[int, int]:
    total_pages = 1
    total_count = 0
    
    tp_match = re.search(r'\\?"totalPages\\?":\s*(\d+)', html)
    if tp_match:
        total_pages = int(tp_match.group(1))
        
    tc_match = re.search(r'\\?"totalCount\\?":\s*(\d+)', html)
    if tc_match:
        total_count = int(tc_match.group(1))
        
    return total_pages, total_count

def get_detail_data(detail_url: str) -> tuple[float | None, float | None]:
    max_retries = 2
    backoff = 6
    
    for attempt in range(max_retries):
        try:
            r = SESSION.get(detail_url, timeout=8)
            if r.status_code == 200:
                html = r.text
                
                lat, lng = None, None
                # Match latitude and longitude from JSON in script
                match = re.search(r'\\?"latitude\\?":\s*(-?\d+\.\d+)\s*,\s*\\?"longitude\\?":\s*(-?\d+\.\d+)', html)
                if match:
                    lat, lng = float(match.group(1)), float(match.group(2))
                else:
                    # Fallback to Google Maps link
                    match = re.search(r'maps\.google\.com/\?q=(-?\d+\.\d+),(-?\d+\.\d+)', html)
                    if match:
                        lat, lng = float(match.group(1)), float(match.group(2))
                        
                return lat, lng
                
            elif r.status_code == 429:
                print(f"  [429] โดนจำกัดคำขอชั่วคราวขณะดึงหน้ารายละเอียด รอ {backoff} วินาที... (พยายามครั้งที่ {attempt+1}/{max_retries})")
                time.sleep(backoff)
                backoff *= 2
            else:
                break
        except Exception:
            time.sleep(1)
            
    return None, None

def fetch_and_update_detail(idx: int, total: int, item: dict):
    link = item["ลิงก์"]
    if not link:
        return
    # Add a tiny randomized delay to space out thread start times
    time.sleep(random.uniform(0.3, 0.8))
    print(f"  -> [{idx+1}/{total}] ดึงข้อมูลจากหน้ารายละเอียด...")
    lat, lng = get_detail_data(link)
    item["ละติจูด"] = lat
    item["ลองจิจูด"] = lng

def scrape_page(page_num: int) -> tuple[list[dict], int, int]:
    url = URL_TEMPLATE.format(page_num=page_num)
    print(f"กำลังดึงข้อมูลหน้า {page_num}... ({url})")
    
    max_retries = 3
    backoff = 8
    html = ""
    
    for attempt in range(max_retries):
        try:
            r = SESSION.get(url, timeout=20)
            if r.status_code == 200:
                html = r.text
                break
            elif r.status_code == 429:
                print(f"[429] โดนจำกัดคำขอชั่วคราวขณะดึงข้อมูลหน้า {page_num} รอ {backoff} วินาที... (พยายามครั้งที่ {attempt+1}/{max_retries})")
                time.sleep(backoff)
                backoff *= 2
            else:
                print(f"เกิดข้อผิดพลาดในการดึงข้อมูลหน้า {page_num}: Status Code {r.status_code}")
                return [], 1, 0
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการดึงข้อมูลหน้า {page_num}: {e}")
            time.sleep(2)
            
    if not html:
        print(f"ไม่สามารถดึงข้อมูลหน้า {page_num} ได้สำเร็จ ข้ามไปหน้าถัดไป")
        return [], 1, 0

    # Extract JSON list of properties
    properties = extract_properties_json(html)
    total_pages, total_count = extract_pagination_info(html)
    
    print(f"พบประกาศทั้งหมด {len(properties)} รายการในหน้า {page_num} (ยอดรวมทรัพย์ทั้งหมด: {total_count} รายการ, {total_pages} หน้า)")
    
    page_listings = []
    for prop in properties:
        listing_id = prop.get("id", "")
        title = prop.get("title", "")
        location = prop.get("location", "")
        province = prop.get("province", "")
        district = prop.get("district", "")
        prop_type = prop.get("propertyType", "")
        
        # Land area handling
        land_area_dict = prop.get("landArea")
        rai = get_clean_area(land_area_dict, "rai")
        ngan = get_clean_area(land_area_dict, "ngan")
        sqWa = get_clean_area(land_area_dict, "sqWa")
        
        building_area = prop.get("buildingArea")
        building_area = "" if building_area is None or str(building_area).lower() == "undefined" else building_area
        
        bedrooms = prop.get("bedrooms")
        bedrooms = "" if bedrooms is None or str(bedrooms).lower() == "undefined" else bedrooms
        
        bathrooms = prop.get("bathrooms")
        bathrooms = "" if bathrooms is None or str(bathrooms).lower() == "undefined" else bathrooms
        
        parking = prop.get("parking")
        parking = "" if parking is None or str(parking).lower() == "undefined" else parking
        
        prop_code = prop.get("propertyCode", "")
        price = prop.get("price")
        original_price = prop.get("originalPrice")
        valid_to_date = prop.get("validToDate", "")
        image_url = prop.get("imageUrl", "")
        
        campaigns = prop.get("campaignNames", [])
        campaign_str = ", ".join(campaigns) if campaigns else ""
        
        href = prop.get("href", "")
        link = "https://www.bam.co.th" + href if href else ""
        
        listing_data = {
            "ID": listing_id,
            "ชื่อประกาศ": clean_whitespace(title),
            "รหัสทรัพย์": clean_whitespace(prop_code),
            "ประเภททรัพย์": clean_whitespace(prop_type),
            "ราคา": price,
            "ราคาตั้งต้น": original_price,
            "ทำเล/ที่ตั้ง": clean_whitespace(location),
            "ตำบล": clean_whitespace(district),
            "อำเภอ": clean_whitespace(district),
            "จังหวัด": clean_whitespace(province),
            "ละติจูด": None,
            "ลองจิจูด": None,
            "พื้นที่ดิน (ไร่)": rai,
            "พื้นที่ดิน (งาน)": ngan,
            "พื้นที่ดิน (ตร.ว.)": sqWa,
            "พื้นที่ใช้สอย (ตร.ม.)": building_area,
            "ห้องนอน": bedrooms,
            "ห้องน้ำ": bathrooms,
            "ที่จอดรถ": parking,
            "วันที่ลดราคาพิเศษถึง": clean_whitespace(valid_to_date),
            "รูปภาพ": image_url,
            "แคมเปญ": clean_whitespace(campaign_str),
            "ลิงก์": link
        }
        page_listings.append(listing_data)
        
    # Fetch detail pages concurrently (Parallel execution)
    total_listings = len(page_listings)
    if total_listings > 0:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(fetch_and_update_detail, idx, total_listings, item)
                for idx, item in enumerate(page_listings)
            ]
            for fut in futures:
                fut.result()
                
    return page_listings, total_pages, total_count

def save_data(existing_listings, new_listings):
    all_listings = existing_listings + new_listings
    if not all_listings:
        print("ไม่มีข้อมูลที่จะบันทึก")
        return
        
    df = pd.DataFrame(all_listings)
    
    # Reorder columns to ensure exact consistency
    cols_order = [
        "ID", "ชื่อประกาศ", "รหัสทรัพย์", "ประเภททรัพย์", "ราคา", "ราคาตั้งต้น",
        "ทำเล/ที่ตั้ง", "ตำบล", "อำเภอ", "จังหวัด", "ละติจูด", "ลองจิจูด",
        "พื้นที่ดิน (ไร่)", "พื้นที่ดิน (งาน)", "พื้นที่ดิน (ตร.ว.)", "พื้นที่ใช้สอย (ตร.ม.)",
        "ห้องนอน", "ห้องน้ำ", "ที่จอดรถ", "วันที่ลดราคาพิเศษถึง", "รูปภาพ", "แคมเปญ", "ลิงก์"
    ]
    
    # Fill missing columns with None to prevent errors
    for col in cols_order:
        if col not in df.columns:
            df[col] = None
            
    df = df[cols_order]
    
    try:
        df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
        print(f"\n  [Save] บันทึกข้อมูลสำเร็จ! รวมทั้งสิ้น {len(df)} รายการ (เป็นรายการใหม่ {len(new_listings)} รายการ)")
    except Exception as e:
        print(f"\n  [Save] เกิดข้อผิดพลาดในการบันทึกข้อมูลลง Excel: {e}")

def save_metadata(total_count):
    try:
        import datetime
        meta_file = Path("metadata.json")
        meta_data = {
            "total_count": total_count,
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2, ensure_ascii=False)
        print(f"[*] บันทึก metadata.json เรียบร้อยแล้ว (จำนวนทั้งหมดในเว็บ: {total_count} รายการ)")
    except Exception as e:
        print(f"[-] ไม่สามารถบันทึก metadata.json: {e}")

def main():
    parser = argparse.ArgumentParser(description="BAM NPA Property Listings Scraper")
    parser.add_argument(
        "--pages",
        type=str,
        default="5",
        help="Number of pages to scrape (e.g. 5, 10, or 'all')"
    )
    parser.add_argument(
        "--start-page",
        type=str,
        default="auto",
        help="Starting page number. 'auto' resumes from where it left off based on Excel row count."
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start scraping from page 1 and overwrite existing Excel file (no resume)."
    )
    args = parser.parse_args()
    
    # Check if Excel file is locked before starting
    if EXCEL_FILE.exists():
        while True:
            try:
                with open(EXCEL_FILE, "r+"):
                    pass
                break
            except PermissionError:
                print(f"\n[Warning] คำเตือน: ไฟล์ '{EXCEL_FILE.name}' กำลังถูกเปิดใช้งานอยู่ในโปรแกรมอื่น (เช่น Microsoft Excel)")
                print("กรุณาปิดไฟล์ Excel นั้นก่อน เพื่อให้ระบบสามารถเริ่มและบันทึกข้อมูลได้")
                input("\nเมื่อปิดไฟล์เสร็จแล้ว กรุณากด Enter เพื่อลองใหม่อีกครั้ง...")
            except Exception:
                break

    # Load existing listings if not fresh run
    existing_listings = []
    existing_ids = set()
    if not args.fresh and EXCEL_FILE.exists():
        try:
            existing_df = pd.read_excel(EXCEL_FILE)
            existing_listings = existing_df.to_dict(orient="records")
            # Clean NaN in dict values to None
            for item in existing_listings:
                for k, v in item.items():
                    if pd.isna(v):
                        item[k] = None
            if "ID" in existing_df.columns:
                existing_ids = {str(val) for val in existing_df["ID"].dropna().tolist()}
            print(f"[*] พบไฟล์ข้อมูลเดิม มีประกาศทั้งหมด {len(existing_listings)} รายการ (รหัสไม่ซ้ำ: {len(existing_ids)} รายการ)")
        except Exception as e:
            print(f"[-] เกิดข้อผิดพลาดในการโหลดไฟล์ข้อมูลเดิม จะขูดใหม่ทั้งหมด: {e}")
            existing_listings = []
            existing_ids = set()

    # Determine starting page
    start_page = 1
    if args.start_page.lower() == "auto":
        if existing_listings:
            # BAM page sizes are 12 items.
            start_page = (len(existing_listings) // 12) + 1
            print(f"[*] ตรวจพบการขูดข้อมูลเดิม: เริ่มต้นหน้า {start_page} อัตโนมัติ")
        else:
            start_page = 1
    else:
        try:
            start_page = int(args.start_page)
        except ValueError:
            print("ค่า --start-page ไม่ถูกต้อง ให้ใช้ตัวเลขหรือ 'auto'. ใช้ค่าเริ่มต้น 1")
            start_page = 1

    new_listings = []
    
    # Fetch starting page to discover total pages dynamically
    first_listings, total_pages, total_count = scrape_page(start_page)
    if first_listings:
        # Save metadata containing total count of properties on web
        save_metadata(total_count)
        
        for item in first_listings:
            if str(item["ID"]) not in existing_ids:
                new_listings.append(item)
                existing_ids.add(str(item["ID"]))
        
        # Determine page limit
        if args.pages.lower() == "all":
            print(f"เริ่มสแกนหน้าทั้งหมดที่เหลือ (ตั้งแต่หน้า {start_page} ถึง {total_pages})...")
            max_pages = total_pages
        else:
            try:
                max_pages = start_page + int(args.pages) - 1
                max_pages = min(max_pages, total_pages)
            except ValueError:
                print("ค่า --pages ไม่ถูกต้อง ให้ใช้ตัวเลขหรือ 'all'. ใช้ค่าเริ่มต้น 5 หน้า")
                max_pages = min(start_page + 4, total_pages)
                
        # Crawl remaining pages
        try:
            for page in range(start_page + 1, max_pages + 1):
                # Respectful delay between search result pages to avoid triggering blocks
                delay = random.uniform(1.5, 3.0)
                time.sleep(delay)
                
                listings, _, _ = scrape_page(page)
                if not listings:
                    print("ไม่พบประกาศหรือเกิดข้อผิดพลาดในการดึงหน้าถัดไป ยุติการทำงาน")
                    break
                    
                for item in listings:
                    if str(item["ID"]) not in existing_ids:
                        new_listings.append(item)
                        existing_ids.add(str(item["ID"]))
                
                # Auto-save every 5 pages
                if (page - start_page) % 5 == 0:
                    save_data(existing_listings, new_listings)
                    
        except KeyboardInterrupt:
            print("\n[Interrupt] ได้รับการแจ้งเตือนให้หยุดทำงาน กำลังบันทึกข้อมูลที่ดึงได้ทั้งหมดลงไฟล์ Excel...")
            
    if new_listings:
        save_data(existing_listings, new_listings)
    else:
        print("ไม่มีข้อมูลใหม่ที่จะบันทึก")

    input("\nกด Enter เพื่อปิดหน้าต่างนี้...")

if __name__ == "__main__":
    main()

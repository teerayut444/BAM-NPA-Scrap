import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Path to the git executable on this machine (same as Baania project)
GIT_PATH = r"C:\Users\Teerayut.N\AppData\Local\Programs\Git\cmd\git.exe"

# Configure console encoding to avoid errors on Windows terminals
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def run_git_command(args):
    command = [GIT_PATH] + args
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[-] เกิดข้อผิดพลาดขณะรันคำสั่ง git {' '.join(args)}")
        print(f"รายละเอียดข้อผิดพลาด:\n{e.stderr.strip() if e.stderr else 'ไม่มีรายละเอียด'}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"[-] ไม่พบโปรแกรม Git ที่พาธ: {GIT_PATH}")
        sys.exit(1)

def main():
    print("[System] เริ่มต้นระบบอัปโหลดไฟล์ขึ้น GitHub (เหมือนโครงการ Baania)...")
    
    # 1. Initialize git if not already done
    if not Path(".git").exists():
        print("[Git] ไม่พบโฟลเดอร์ .git กำลังเริ่มต้นระบบ Git Local...")
        run_git_command(["init"])
        run_git_command(["branch", "-M", "main"])
        
        repo_url = "https://github.com/Teerayut.N/BAM-NPA-Scrap.git"
        print(f"[Git] กำลังกำหนดค่า Remote ไปยัง: {repo_url}")
        run_git_command(["remote", "add", "origin", repo_url])
    
    # 2. Check status
    print("[Check] ตรวจสอบการเปลี่ยนแปลงไฟล์...")
    status = run_git_command(["status", "--porcelain"])
    
    if not status:
        print("[Success] ไม่มีไฟล์ที่มีการเปลี่ยนแปลง ไม่จำเป็นต้องอัปโหลด")
        return
        
    print("[Modified] ไฟล์ที่มีการเปลี่ยนแปลง:")
    for line in status.splitlines():
        print(f"  - {line}")
    
    # 3. git add .
    print("\n[Git] กำลังสเตจไฟล์ (git add .)...")
    run_git_command(["add", "."])
    
    # 4. git commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Auto-update: {timestamp}"
    print(f"[Git] กำลังบันทึกประวัติการแก้ไข (git commit -m \"{commit_msg}\")...")
    commit_out = run_git_command(["commit", "-m", commit_msg])
    print(commit_out)
    
    # 5. git push origin main
    print("\n[Git] กำลังส่งข้อมูลขึ้น GitHub (git push origin main)...")
    print("โปรดรอสักครู่...")
    run_git_command(["push", "origin", "main"])
    print("[Success] อัปโหลดไฟล์และอัปเดตข้อมูลขึ้น GitHub สำเร็จเรียบร้อยแล้ว!")

if __name__ == "__main__":
    main()

# Camfrog AutoDJ — Windows Setup & Troubleshooting

คู่มือการติดตั้งและแก้ปัญหาสำหรับ Windows โดยเฉพาะ

## 1. ติดตั้งด้วยตัวติดตั้งอัตโนมัติ (แนะนำ)

ดาวน์โหลด `Camfrog-AutoDJ-Setup-x.y.z.exe` จาก [GitHub Releases](https://github.com/cvsz/autodj/releases) แล้วรันเป็นผู้ดูแลระบบ (Run as Administrator)

ตัวติดตั้งจะ:

1. ติดตั้ง `AutoDJ.exe` ไปที่ `C:\Program Files\Camfrog AutoDJ\`
2. สร้าง shortcut ใน Start Menu และ Desktop
3. ลงทะเบียนใน Add/Remove Programs
4. สร้าง `uninstall.exe` สำหรับถอนการติดตั้ง

หลังติดตั้ง ให้รัน `AutoDJ.exe --check` เพื่อตรวจสอบว่าทุกอย่างพร้อมหรือไม่

---

## 2. ติดตั้งด้วยตนเอง (Manual Setup)

ถ้าไม่ใช้ตัวติดตั้ง ให้ทำตามขั้นตอนนี้:

### ขั้นตอนที่ 1: ติดตั้งโปรแกรมที่จำเป็น

| โปรแกรม | วิธีติดตั้ง |
|----------|-------------|
| Python 3.11+ | ดาวน์โหลดจาก [python.org](https://python.org) หรือติดตั้งผ่าน winget: `winget install Python.Python.3.11` |
| mpv | ดาวน์โหลดจาก [mpv.io](https://mpv.io) หรือติดตั้งผ่าน winget: `winget install mpv` |
| yt-dlp | ดาวน์โหลดจาก [github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp/releases) หรือติดตั้งผ่าน winget: `winget install yt-dlp` |

### ขั้นตอนที่ 2: ติดตั้ง AutoDJ

```cmd
:: คลอนโปรเจกต์
git clone https://github.com/cvsz/autodj.git
cd autodj

:: ติดตั้งแพ็กเกจ Python
pip install -e .

:: สร้าง AutoDJ.exe (ตัวเลือก ถ้าต้องการสร้าง exe เอง)
pip install pyinstaller
.\build.ps1
```

### ขั้นตอนที่ 3: สร้าง config.toml

```cmd
copy config.example.toml config.toml
```

แก้ไข `config.toml` ให้ตรงกับสภาพแวดล้อมของคุณ:

```toml
bot_nick = "AutoDJ"
admins = ["YourNick"]
prefix = "!"
lang = "th"

mpv_path = "C:/mpv/mpv.exe"           # แก้เป็น path จริงบนเครื่องคุณ
ytdlp_path = ""                        # ว่างได้ ถ้า yt-dlp อยู่ใน PATH หรืออยู่ถัดจาก mpv.exe

music_dirs = ["D:/Music"]              # โฟลเดอร์เพลงของคุณ
autoplay_sources = []                  # ปล่อยว่างได้ ถ้าไม่ต้องการเพลงอัตโนมัติ
```

### ขั้นตอนที่ 4: ตรวจสอบการตั้งค่า

```cmd
AutoDJ.exe --check
```

จะแสดงสถานะของแต่ละส่วน: mpv, yt-dlp, โฟลเดอร์เพลง, แอดมิน, ห้อง Camfrog ฯลฯ

### ขั้นตอนที่ 5: ค้นหาห้อง Camfrog อัตโนมัติ

เปิดหน้าต่างห้องแชทใน Camfrog แล้วรัน:

```cmd
AutoDJ.exe --discover
```

จะค้นหาหน้าต่างห้องและปุ่มแชทโดยอัตโนมัติ แล้วบันทึกลง `config.toml`

หรือรัน `--windows` เพื่อดูรายการหน้าต่างทั้งหมดที่เปิดอยู่:

```cmd
AutoDJ.exe --windows
```

### ขั้นตอนที่ 6: รัน AutoDJ

```cmd
# โหมดเดสก์ท็อป (มี GUI)
AutoDJ.exe --gui

# โหมดบรรทัดคำสั่ง (ไม่มี GUI)
AutoDJ.exe --console

# โหมดเงียบ (ไม่มี GUI เลย)
AutoDJ.exe
```

---

## 3. การแก้ปัญหา (Troubleshooting)

### ปัญหาที่พบบ่อย

| อาการ | สาเหตุที่เป็นไปได้ | วิธีแก้ไข |
|--------|-------------------|------------|
| `mpv not found` | ไม่ได้ติดตั้ง mpv หรือ path ไม่ถูกต้อง | ติดตั้ง mpv แก้ไข `mpv_path` ใน `config.toml` ให้ชี้ไปที่ไฟล์ `mpv.exe` จริง |
| `yt-dlp not found` | ไม่มี yt-dlp.exe หรือไม่ได้อยู่ใน PATH | โหลด `yt-dlp.exe` มาไว้ถัดจาก `mpv.exe` หรือตั้ง `ytdlp_path` ใน `config.toml` |
| `Cannot start: TOML syntax error` | config.toml มีข้อผิดพลาดด้านไวยากรณ์ | ดูบรรทัดที่มีเครื่องหมาย `^` แล้วแก้ไข หรือคัดลอก `config.example.toml` มาทับ |
| `No module named 'yt_dlp'` | Python module yt-dlp ไม่ได้ติดตั้ง | รัน `pip install yt-dlp` หรือสร้าง AutoDJ.exe ใหม่ด้วย `build.ps1` |
| `YouTube lookup is unavailable` | yt-dlp เวอร์ชันเก่า หรือไม่มี JavaScript runtime | รัน `yt-dlp -U` เพื่ออัปเดต หรือติดตั้ง deno: `winget install deno` |
| `Nothing playing` | ไม่มีเพลงในคิว หรือยังไม่ได้เริ่มเล่น | ใช้ `!play <ชื่อเพลง>` หรือ `!เล่น <ชื่อเพลง>` เพื่อเพิ่มเพลง |
| `คิวเต็มแล้ว` | คำขอในคิวเต็มแล้ว | รอให้เพลงในคิวเล่นจบ หรือใช้ `!ล้างคิว` (แอดมินเท่านั้น) |
| `ข้ามได้เฉพาะคนขอเพลงหรือแอดมิน` | คุณไม่ใช่คนขอเพลงนั้น และไม่ใช่แอดมิน | ใช้ `!โหวตข้าม` แทน หรือขอให้แอดมินข้ามให้ |
| `เล่นไม่ได้: {ชื่อเพลง}` | mpv เล่นเพลงนั้นไม่ได้ | ตรวจสอบว่าไฟล์มีอยู่จริง หรือลิงก์ YouTube ยังใช้งานได้ |
| `ตอนนี้ค้นหาเพลงจาก YouTube ไม่ได้` | yt-dlp ไม่ทำงาน หรือไม่มี JavaScript runtime | อัปเดต yt-dlp: `yt-dlp -U` ติดตั้ง deno: `winget install deno` |
| `ไม่พบหน้าต่างที่ตรงกับ ...` | ยังไม่ได้เปิดหน้าต่างห้อง Camfrog หรือ `window_title_re` ไม่ตรง | เปิดหน้าต่างห้องแชทใน Camfrog ก่อน หรือรัน `AutoDJ.exe --discover` |
| `บล็อกแอดมินไม่ได้` | พยายามบล็อกนICK ที่เป็นแอดมิน | ไม่สามารถบล็อกแอดมินได้ โดยตั้งใจ |

### ข้อผิดพลาดที่พบบ่อยใน `AutoDJ.exe --check`

| ระดับ | ข้อความ | ความหมาย |
|-------|---------|-----------|
| `FAIL` | mpv not found | ติดตั้ง mpv และตั้ง `mpv_path` ใน config.toml |
| `WARN` | no yt-dlp executable | โหลด yt-dlp.exe มาไว้ถัดจาก mpv.exe หรือตั้ง `ytdlp_path` |
| `WARN` | no yt_dlp Python module either | รัน `pip install yt-dlp` |
| `WARN` | music_dirs: folder not found | โฟลเดอร์เพลงที่ระบุใน config.toml ไม่มีอยู่จริง |
| `WARN` | admins is empty | ไม่มีใครถูกตั้งเป็นแอดมิน เพิ่ม `admins = ["YourNick"]` ใน config.toml |
| `WARN` | no JavaScript runtime | ติดตั้ง deno: `winget install deno` |

---

## 4. คำสั่งที่ใช้บ่อย

| คำสั่ง | ความหมาย | ใครใช้ได้ |
|--------|-----------|-----------|
| `!เล่น <ชื่อเพลง>` | ขอเพลงจากชื่อหรือลิงก์ YouTube | ทุกคน |
| `!เพลงนี้` | ดูเพลงที่กำลังเล่นอยู่ | ทุกคน |
| `!ถัดไป` | ดูเพลงถัดไปในคิว | ทุกคน |
| `!คิว` | ดูรายการเพลงในคิว | ทุกคน |
| `!ประวัติ` | ดูประวัติเพลงที่เล่นไป | ทุกคน |
| `!โหวตข้าม` | โหวตข้ามเพลงปัจจุบัน | ทุกคน |
| `!ลบ <เลข>` | ลบเพลงออกจากคิว | คนขอ หรือแอดมิน |
| `!ข้าม` | ข้ามเพลงปัจจุบัน | คนขอ หรือแอดมิน |
| `!หยุดชั่วคราว` | หยุดเพลงชั่วคราว | แอดมินเท่านั้น |
| `!เล่นต่อ` | เล่นเพลงต่อ | แอดมินเท่านั้น |
| `!เสียง <0-100>` | ปรับระดับเสียง | แอดมินเท่านั้น |
| `!สุ่ม on\|off` | เปิด/ปิดสุ่มเพลง | แอดมินเท่านั้น |
| `!วนซ้ำ off\|one` | เปิด/ปิดวนซ้ำเพลงเดียว | แอดมินเท่านั้น |
| `!ล้างคิว` | ล้างคำขอในคิวทั้งหมด | แอดมินเท่านั้น |
| `!โหลด <แหล่ง>` | โหลดเพลงจากแหล่งต่าง ๆ | แอดมินเท่านั้น |
| `!บล็อก <ชื่อ>` | บล็อกไม่ให้ผู้ใช้นั้นใช้คำสั่ง | แอดมินเท่านั้น |
| `!เลิกบล็อก <ชื่อ>` | ยกเลิกการบล็อกผู้ใช้ | แอดมินเท่านั้น |

---

## 5. การลบการติดตั้ง (Uninstall)

ใช้ตัวติดตั้งถอนการติดตั้งผ่าน **Start Menu → Camfrog AutoDJ → Uninstall** หรือไปที่ **หน้าต่างการตั้งค่า → แอป → Camfrog AutoDJ → ถอนการติดตั้ง**

หรือรัน `uninstall.exe` ในโฟลเดอร์ติดตั้งโดยตรง

---

## 6. รายละเอียดไฟล์ที่ติดตั้ง

หลังติดตั้ง โฟลดร์ `C:\Program Files\Camfrog AutoDJ\` จะมี:

| ไฟล์/โฟลเดอร์ | ความหมาย |
|---------------|-----------|
| `AutoDJ.exe` | โปรแกรมหลัก |
| `app.ico` | ไอคอนโปรแกรม |
| `README.md` | คำอธิบายโดยสังเขป |
| `CHANGELOG.md` | บันทึกการเปลี่ยนแปลง |
| `LICENSE` | ใบอนุญาต (MIT) |
| `config.example.toml` | ตัวอย่างไฟล์กำหนดค่า |
| `run_autodj.py` | สคริปต์รันโปรแกรม |
| `config.toml` | ไฟล์กำหนดค่าของคุณ (สร้างเมื่อรันครั้งแรก) |
| `playlist.json` | รายชื่อเพลงที่ขอไว้ (สร้างเมื่อมีคนขอเพลง) |
| `autodj.log` | ไฟล์บันทึกเหตุการณ์ (ถ้าเปิดใช้ `log_file`) |
| `docs/` | เอกสารประกอบ |
| `src/` | โค้ดต้นฉบับ Python |
| `tools/` | เครื่องมือช่วยเหลือ |
| `tests/` | ชุดทดสอบ |

---

## 7. การสร้าง AutoDJ.exe เอง (สำหรับนักพัฒนา)

ถ้าต้องการสร้าง `AutoDJ.exe` เองแทนที่จะใช้ไฟล์ที่แจกจ่าย:

```powershell
# ติดตั้งเครื่องมือสร้าง
pip install -e . pyinstaller

# สร้าง exe (จะลงนามด้วยตัวเองโดยอัตโนมัติ)
.\build.ps1

# หรือสร้างโดยไม่ลงนาม
.\build.ps1 -NoSign

# หรือใช้ Makefile (ถ้ามี make ติดตั้ง)
make build
```

ไฟล์ `.exe` จะถูกสร้างในโฟล더 `dist\`

---

## 8. การขอความช่วยเหลือ

ถ้ายังแก้ปัญหาไม่ได้:

1. รัน `AutoDJ.exe --check` และแนบผลลัพธ์มาด้วย
2. เปิดไฟล์ `autodj.log` และค้นหาข้อผิดพลาด
3. แจ้งปัญหาผ่าน [GitHub Issues](https://github.com/cvsz/autodj/issues) (อย่าลืมลบข้อมูลส่วนตัวออกจาก log ก่อนแนบ)

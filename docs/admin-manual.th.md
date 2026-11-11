# คู่มือแอดมิน AutoDJ — ภาษาไทย

**เวอร์ชัน:** 0.3.0  
**กลุ่มเป้าหมาย:** ผู้ดูแลห้องและผู้ปฏิบัติงานบอท  
**ภาษา:** ไทย

---

## ภาพรวม

คู่มือนี้ครอบคลุมคุณสมบัติการบริหาร การตั้งค่า และขั้นตอนการดำเนินงานสำหรับ AutoDJ ผู้ใช้ทั่วไปควรอ้างอิง [คู่มือผู้ใช้](user-manual.th.md)

---

## คำสั่งแอดมิน

### ควบคุมการเล่น

| คำสั่ง | อัลลิแอส | คำอธิบาย | ตัวอย่าง |
|---------|----------|------------|---------|
| `pause` | `หยุดชั่วคราว` | หยุดการเล่นชั่วคราว | `!หยุดชั่วคราว` |
| `resume` | `unpause`, `เล่นต่อ` | เล่นต่อจากที่หยุด | `!เล่นต่อ` |
| `skip` | `ข้าม` | ข้ามเพลงปัจจุบัน (เพลงใดก็ได้) | `!ข้าม` |
| `vol` | `volume`, `เสียง` | ตั้งระดับเสียง 0-100 หรือดูค่าปัจจุบัน | `!เสียง 80` / `!เสียง` |

### จัดการคิว

| คำสั่ง | อัลลิแอส | คำอธิบาย | ตัวอย่าง |
|---------|----------|------------|---------|
| `clear` | `ล้างคิว` | ล้างคำขอทั้งหมดออกจากคิว | `!ล้างคิว` |
| `shuffle` | `สุ่ม` | เปิด/ปิดโหมดสุ่ม | `!สุ่ม on` / `!สุ่ม off` |
| `repeat` | `วนซ้ำ` | ตั้งโหมดวนซ้ำ | `!วนซ้ำ one` / `!วนซ้ำ off` |
| `remove` | `rm`, `ลบ` | ลบคำขอใดๆ ตามเลขลำดับ | `!ลบ 3` |

### จัดการประวัติ

| คำสั่ง | อัลลิแอส | คำอธิบาย | ตัวอย่าง |
|---------|----------|------------|---------|
| `history` | `recent`, `ประวัติ` | แสดงเพลงที่เล่นไปแล้ว | `!ประวัติ` |
| `clearhistory` | `ล้างประวัติ` | ล้างประวัติทั้งหมด | `!ล้างประวัติ` |
| `deletehistory` | `delhistory`, `ลบประวัติ` | ลบ N รายการสุดท้าย หรือทั้งหมด | `!ลบประวัติ 10` / `!ลบประวัติ all` |
| `last` | `requested`, `ขอล่าสุด` | แสดง 5 เพลงที่ผู้ใช้ขอล่าสุด | `!ขอล่าสุด` |

### โหลดเพลง

| คำสั่ง | อัลลิแอส | คำอธิบาย | ตัวอย่าง |
|---------|----------|------------|---------|
| `load` | `โหลด` | โหลดเพลย์ลิสต์/โฟลเดอร์/ไฟล์ เข้าสู่ระบบเล่นอัตโนมัติ | `!โหลด <แหล่ง>` |

**แหล่งที่โหลดได้:**
- URL เพลย์ลิสต์ YouTube: `!โหลด https://youtube.com/playlist?list=PL...`
- โฟลเดอร์ในเครื่อง: `!โหลด D:\Music\Pop`
- ไฟล์ในเครื่อง: `!โหลด song.mp3`
- ค้นหา YouTube (สำหรับเล่นอัตโนมัติ): `!โหลด ytsearch20:thai pop`

### การสื่อสาร

| คำสั่ง | อัลลิแอส | คำอธิบาย | ตัวอย่าง |
|---------|----------|------------|---------|
| `say` | `พูด` | ส่งข้อความไปยังแชทห้อง | `!พูด สวัสดีทุกคน!` |
| `speak` | `tts`, `ออกเสียง` | ออกเสียงผ่าน TTS (เพลงลดเสียง) | `!ออกเสียง ยินดีต้อนรับ!` |

### จัดการผู้ใช้

| คำสั่ง | อัลลิแอส | คำอธิบาย | ตัวอย่าง |
|---------|----------|------------|---------|
| `block` | `บล็อก` | บล็อกผู้ใช้ไม่ให้ใช้คำสั่ง | `!บล็อก spammer` |
| `unblock` | `เลิกบล็อก` | ยกเลิกการบล็อก | `!เลิกบล็อก spammer` |

### ข้อมูล

| คำสั่ง | อัลลิแอส | คำอธิบาย | ตัวอย่าง |
|---------|----------|------------|---------|
| `help` | `commands`, `ช่วยเหลือ` | แสดงคำสั่งทั้งหมด (รวมแอดมิน) | `!ช่วยเหลือ` |
| `np` | `nowplaying`, `เพลงนี้` | ข้อมูลเพลงปัจจุบัน | `!เพลงนี้` |
| `next` | `upnext`, `ถัดไป` | เพลงถัดไป | `!ถัดไป` |
| `queue` | `q`, `คิว` | คิวทั้งหมด | `!คิว` |
| `voteskip` | `vs`, `โหวตข้าม` | โหวตข้าม (แอดมินใช้ได้) | `!โหวตข้าม` |

---

## การตั้งค่า (config.toml)

### ตั้งค่าแอดมิน (บังคับ)

```toml
# === การตั้งค่าแอดมิน ===
# ใส่นามเดิม Camfrog ของคุณที่นี่ (ไม่สนใจตัวพิมพ์เล็ก/ใหญ่)
admins = ["YourNick", "BackupAdmin"]

# ชื่อของบอทในห้อง (สำหรับตรวจจับข้อความตัวเอง)
bot_nick = "AutoDJ"

# คำนำหน้าคำสั่ง
prefix = "!"
```

### ห้องและการเชื่อมต่อ

```toml
# การตรวจจับหน้าต่างห้อง Camfrog
window_title_re = ".*"          # Regex ชื่อหน้าต่างห้อง
process_re = "(?i)camfrog"      # กรองชื่อโปรเซส
auto_discover = true            # ตรวจจับห้องอัตโนมัติตอนเริ่มต้น

# แอดอัปเตอร์แชท: "uia" (Windows UI Automation) | "logtail" | "console"
chat_reader = "uia"
chat_sender = "uia"

# เฉพาะ UIA (เติมอัตโนมัติโดย --discover)
view_kind = "auto"
view_type = "Document"
view_index = 0
input_type = "Edit"
input_index = -1
line_regex = '^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<user>[^:\s][^:]{0,30}):\s(?P<text>.+)$'
```

### การตั้งค่าเสียง

```toml
# เส้นทาง mpv player (จำเป็น)
mpv_path = "mpv"                    # หรือพาธเต็ม: "C:/mpv/mpv.exe"

# เส้นทาง yt-dlp (ตรวจจับอัตโนมัติถ้าว่าง)
ytdlp_path = ""                     # หรือ "C:/mpv/yt-dlp.exe"

# อุปกรณ์เอาท์พุตเสียง (จาก: mpv --audio-device=help)
audio_device = ""                   # เช่น "wasapi/{guid}" สำหรับ virtual cable

# ระดับเสียงเริ่มต้น (0-100)
volume = 70
```

### คลังเพลง

```toml
# โฟลเดอร์เพลงในเครื่อง (ผู้ใช้ขอได้โดยชื่อ)
music_dirs = ["D:/Music", "E:/Music2"]

# แหล่งเล่นอัตโนมัติเพิ่มเติม (เพลย์ลิสต์ YouTube, โฟลเดอร์, ไฟล์)
autoplay_sources = [
    "https://www.youtube.com/playlist?list=PL...",
    "D:/Music/Autoplay"
]

# สุ่มสระเพลงอัตโนมัติ
shuffle = true
```

### ขีดจำกัดและการป้องกัน

```toml
# โดเมน YouTube ที่อนุญาตให้ขอ
allowed_hosts = ["youtube.com", "youtu.be", "music.youtube.com"]

# ขีดจำกัดต่อผู้ใช้
max_requests_per_user = 3      # สูงสุดคำขอพร้อมกันในคิว
user_request_limit = 5         # สูงสุดคำขอต่อ sliding window
rate_limit_window = 300.0      # sliding window (วินาที)

# ขีดจำกัดคิว
max_queue = 50                 # ขนาดคิวทั้งหมด
max_duration = 900             # ความยาวเพลงสูงสุด (วินาที) สำหรับผู้ใช้ทั่วไป

# โหวตข้าม
voteskip_threshold = 3         # คะแนนที่ต้องการเพื่อข้าม
voteskip_dynamic = false       # เกณฑ์ไดนามิกตามจำนวนคนในห้อง
voteskip_dynamic_pct = 30      # เปอร์เซ็นต์สำหรับโหมดไดนามิก

# คูลดาวน์และป้องกันน้ำท่วม
cooldown = 3.0                 # วินาทีระหว่างคำสั่งต่อผู้ใช้
send_interval = 1.5            # วินาทีระหว่างข้อความแชท
max_msg_len = 180              # ความยาวข้อความสูงสุด
```

### การเล่นอัตโนมัติและพฤติกรรมเวลาว่าง (ใหม่ใน 0.2.8)

```toml
# วินาทีที่ไม่มีคำขอจากผู้ใช้ ก่อนสลับไปเล่นอัตโนมัติ
autoplay_idle_timeout = 30.0   # ขั้นต่ำ 60 วินาที ถ้า auto_reply_enabled

# ความคงที่ของเพลย์ลิสต์
playlist_file = "playlist.json"    # บันทึกคำขอผู้ใช้ที่นี่
playlist_dir = ""                  # โฟลเดอร์ไฟล์ .json เพลย์ลิสต์
search_limit = 1                   # ผลลัพธ์ค้นหา YouTube ต่อคำขอ

# หมดเวลา mpv (0 = ไม่มี timeout)
mpv_timeout = 30
```

### ทักทายแอดมิน (ใหม่ใน 0.2.8)

```toml
# ทักทายแอดมินเมื่อส่งข้อความครั้งแรกในเซสชัน
admin_greeting_enabled = false
admin_greeting_message = "สวัสดีครับแอดมิน {admin} ยินดีต้อนรับกลับมา!"
admin_greeting_cooldown = 3600.0   # วินาทีระหว่างการทักทายต่อแอดมิน
```

### ความปลอดภัย IM (ใหม่ใน 0.2.8)

```toml
# กำหนดให้ผู้ใช้ต้องอยู่ในห้อง (ปรากฏในแชท) จึงจะใช้คำสั่ง IM ได้
im_require_room_presence = true
```

### ตอบกลับอัตโนมัติ (ข้อความตามกำหนด)

```toml
auto_reply_enabled = false
auto_reply_interval = 300.0      # ขั้นต่ำ 60 วินาที
auto_reply_file = "ads-list.json"  # ไฟล์ JSON เก็บข้อความ
```

### TTS (Text-to-Speech)

```toml
tts_voice = ""                   # ส่วนหนึ่งของชื่อเสียงที่ติดตั้ง
tts_rate = 170                   # อัตราการพูด
tts_duck = 25                    # ระดับเสียงเพลงระหว่าง TTS (0-100)
```

### สไตล์ข้อความ (เฉพาะแสดงตัวอย่างใน GUI)

> **หมายเหตุ:** ไคลเอนต์ Camfrog เดสก์ท็อป **ไม่รองรับ rich text** ในข้อความที่ส่งออก การตั้งค่านี้ใช้ **เฉพาะ** สำหรับแผงแสดงตัวอย่าง FontEditor ใน GUI เท่านั้น ข้อความที่ส่งจริงจะเป็น plain text ทุกครั้งผ่าน UIA

```toml
message_style = { 
    font_family = "Consolas", 
    font_size = 14, 
    font_color = "#FF0000", 
    bold = false, 
    italic = false, 
    underline = false 
}
```

### การบันทึก Log

```toml
log_file = ""                    # เช่น "autodj.log" (หมุน 1MB x3)
log_path = ""                    # ไดเรกทอรี log แบบกำหนดเอง
log_encoding = "utf-8"
```

### เปิดอัตโนมัติ (Windows เท่านั้น)

```toml
auto_launch = false              # เปิด Camfrog และเข้าห้องอัตโนมัติ
camfrog_exe = ""                 # เส้นทางไฟล์ Camfrog executable
client_title_re = ".*"           # Regex ชื่อหน้าต่างไคลเอนต์หลัก
room = ""                        # ชื่อห้องที่จะเข้าร่วม
join_uri_template = ""           # URI template พร้อม placeholder {room}
launch_timeout = 60              # วินาทีรอหน้าต่างห้อง
```

### ผู้ใช้ที่ถูกบล็อก

```toml
blocked_users = []               # นามเดิมที่คำสั่งจะถูกเพิกเฉย
```

---

## คุณสมบัติ GUI สำหรับแอดมิน

### ปุ่มบนแถบหัว

- **EN/TH** — สลับภาษาแบบเรียลไทม์
- **⚙️ Settings** — เปิดกล่องโต้ตอบตั้งค่า (แก้ไข config ทั้งหมดได้)
- **🔍 Discover room** — รัน auto-discovery จาก GUI
- **✓ Check setup** — รันการวินิจฉัยจาก GUI

### การ์ดเพลงปัจจุบัน

- **แผ่นหมุน** — ตัวบ่งชี้การเล่นแบบภาพ
- **อีควอลไอเซอร์เคลื่อนไหว** — ตกแต่ง (ไม่ได้วิเคราะห์เสียงจริง)
- **แถบความคืบหน้า** — คลิกเพื่อ seek
- **แถบปรับเสียง** — ลากเพื่อเปลี่ยนระดับเสียง
- **ไฟ ON AIR** — สีแดงตอนเล่น
- **Pause/Skip** — ปุ่มกลม
- **ความคืบหน้าโหวตข้าม** — แสดงคะแนนปัจจุบัน/ที่ต้องการ

### แท็บ

1. **Queue** — รายการคำขอพร้อมปุ่ม Remove/Clear
2. **History** — เพลงที่เล่นไปแล้ว
3. **Chat** — บันทึกแชทห้อง พร้อมช่อง Say/Speak

### กล่องโต้ตอบตั้งค่า

เข้าถึงผ่านปุ่ม **⚙️ Settings** ทุกการตั้งค่าใน config.toml แก้ไขได้ พร้อม:
- ตรวจสอบค่าที่ป้อน (ช่วงค่า, regex, ตัวเลือก)
- บันทึกแบบ atomic พร้อม backup `.bak`
- ย้ายไป `%APPDATA%\CamfrogAutoDJ\` อัตโนมัติถ้าโฟลเดอร์ติดตั้งเขียนไม่ได้
- สลับภาษา label แบบเรียลไทม์

---

## การวินิจฉัยและบำรุงรักษา

### เครื่องมือบรรทัดคำสั่ง

```bash
# ตรวจสอบระบบเต็มรูปแบบ
AutoDJ.exe --check
# หรือ
camfrog-autodj --check

# ตรวจจับหน้าต่างห้องอัตโนมัติ
AutoDJ.exe --discover

# แสดงหน้าต่างทั้งหมด (หา Camfrog)
AutoDJ.exe --windows

# ดับ tree ควบคุมหน้าต่าง
AutoDJ.exe --dump "Camfrog"

# ส่งข้อความทดสอบไปห้อง
AutoDJ.exe --say "test message"

# รันพร้อม GUI
AutoDJ.exe --gui

# รันแบบ headless
AutoDJ.exe

# โหมดคอนโซล (พิมพ์คำสั่งตรงๆ)
AutoDJ.exe --console --lang th
```

### ผลลัพธ์ Health Check

`--check` ตรวจสอบ:
- ✅ พบ mpv executable
- ✅ yt-dlp พร้อมใช้ (exe หรือ Python module)
- ✅ JavaScript runtime (สำหรับ yt-dlp)
- ✅ โฟลเดอร์เพลงเข้าถึงได้
- ✅ รายการแอดมินไม่ว่าง
- ✅ ไวยากรณ์ config ถูกต้อง
- ✅ ตรวจจับหน้าต่าง Camfrog ได้
- ✅ Python packages ติดตั้งครบ

### ไฟล์ Log

- **ค่าเริ่มต้น:** แสดงผลบนคอนโซล (stdout/stderr)
- **ไฟล์:** ตั้ง `log_file = "autodj.log"` ใน config
- **หมุนเวียน:** 1 MB × 3 ไฟล์
- **ตำแหน่ง:** พาธสัมพัทธ์ resolve ไป `%APPDATA%\CamfrogAutoDJ\`

### ปัญหาที่พบบ่อยและวิธีแก้

| ปัญหา | สาเหตุ | วิธีแก้ |
|--------|--------|---------|
| "mpv not found" | mpv_path ผิด หรือ mpv ไม่ได้ติดตั้ง | ติดตั้ง mpv, ตั้ง path ให้ถูกต้อง |
| "yt-dlp not found" | ไม่มี yt-dlp | วาง yt-dlp.exe ใกล้ mpv.exe หรือ `pip install yt-dlp` |
| "ค้นหา YouTube ไม่ได้" | yt-dlp เก่า หรือขาด JS runtime | `yt-dlp -U`, ติดตั้ง deno/node |
| "Config syntax error" | TOML ผิด | ดูบรรทัดที่มี `^` แก้หรือคัดลอกตัวอย่าง |
| "เล่นไม่ได้" | mpv error | ดู log สำหรับ error ของ mpv |
| "GUI เปิดไม่ได้" | Auto-discovery crash | ใช้ NullAdapter fallback; รัน `--check`/`--discover` จาก GUI |
| "Permission denied" config | ติดตั้งใน Program Files | ย้ายไป APPDATA อัตโนมัติ |

---

## การสร้าง AutoDJ.exe (Windows)

### ข้อกำหนดเบื้องต้น

- Windows 10/11
- Python 3.11+
- mpv ติดตั้งแล้ว
- yt-dlp.exe ใกล้ mpv.exe
- Visual Studio Build Tools (สำหรับ PyInstaller)

### ขั้นตอนสร้าง

```powershell
# 1. ติดตั้ง dependencies
python -m pip install -e . pyinstaller

# 2. Build (สร้าง self-signed cert อัตโนมัติ)
.\build.ps1

# 3. หรือใช้ certificate ของตัวเอง
.\build.ps1 -Pfx cert.pfx -Password "secret"

# 4. ตรวจสอบ
dist\AutoDJ.exe --version
dist\AutoDJ.exe --check
```

### ตัวเลือก Build

| ตัวเลือก | คำอธิบาย |
|---------|-----------|
| `-Clean` | ล้าง build artifacts ก่อน |
| `-NoSign` | ข้ามการ sign code |
| `-Pfx` | พาธไฟล์ .pfx certificate |
| `-Password` | รหัสผ่าน certificate |
| `-Thumbprint` | thumbprint cert ใน user store |
| `-Subject` | subject สำหรับ self-signed cert |

---

## ตัวติดตั้ง NSIS (Windows)

### สร้าง Installer

```powershell
# ต้องการ NSIS 3.0+ พร้อม MUI2
makensis installer.nsi
```

### คุณสมบัติ Installer

- ติดตั้งต่อผู้ใช้ไป `%APPDATA%\CamfrogAutoDJ` (ไม่ต้อง admin)
- ติดตั้ง Python, mpv, yt-dlp, VB-Cable ผ่าน winget
- สร้าง Shortcut บน Desktop/Start Menu
- สร้าง config.toml แบบโต้ตอบ
- ตัวเลือก auto-start ตอน login
- รัน `AutoDJ.exe --check` ยืนยัน
- มี Uninstaller รวมอยู่

---

## ข้อควรพิจารณาด้านความปลอดภัย

### การยืนยันตัวตนด้วยชื่อเล่น

> ⚠️ **คำเตือน:** การให้สิทธิ์แอดมินใช้ชื่อเล่น Camfrog ซึ่ง **ปลอมได้** ผู้ใช้คนไหนก็สามารถเปลี่ยนชื่อเล่นให้ตรงกับแอดมินและได้สิทธิ์แอดมิน

**การลดความเสี่ยง:**
- ใช้ชื่อแอดมินที่ซับซ้อน ยากเดา
- เก็บรายการ `admins` ให้น้อยที่สุด
- ตรวจสอบ log สำหรับกิจกรรมแอดมินที่น่าสงสัย
- เปิด `im_require_room_presence = true` (ค่าเริ่มต้น)

### พฤติกรรม Fail-Closed

- รายการ `admins` ว่าง = **ไม่มีสิทธิ์แอดมิน** ผ่านชื่อเล่น
- คอนโซลท้องถิ่น (`--console`) มีสิทธิ์แอดมินเสมอ
- ผู้ใช้ที่ถูกบล็อกจะถูก **เพิกเฉยเงียบๆ** (ไม่มีข้อความ error)

### ความปลอดภัยการตั้งค่า

- เขียนแบบ atomic (temp file + `os.replace`)
- Backup `.bak` ทุกครั้งที่บันทึก
- ตรวจสอบค่าก่อนเขียน (ช่วงค่า, regex, ตัวเลือก)
- ย้ายไฟล์ config อัตโนมัติถ้าเขียนไม่ได้

---

## การอัปเกรด

### จาก 0.2.x

1. **Backup** `config.toml` และ `playlist.json`
2. **Pull** โค้ดล่าสุด
3. **รัน** `python -m pip install -e . --upgrade`
4. **ตรวจสอบ** `AutoDJ.exe --check`
5. **ยืนยัน** การ migrate config (รันอัตโนมัติตอนเริ่มต้น)

### การ Migrate Config

AutoDJ migrate อัตโนมัติ:
- พาธ placeholder (`REPLACE_ME`) → ค่าเริ่มต้น
- Key เก่า → โครงสร้างใหม่
- สร้าง `config.toml.bak` ก่อนเปลี่ยนแปลง

---

## ตำแหน่งไฟล์

| ไฟล์ | ตำแหน่งค่าเริ่มต้น | คำอธิบาย |
|------|------------------|-----------|
| `config.toml` | `%APPDATA%\CamfrogAutoDJ\` | การตั้งค่าหลัก |
| `playlist.json` | เหมือน config | คำขอผู้ใช้ที่คงอยู่ |
| `ads-list.json` | เหมือน config | ข้อความตอบกลับอัตโนมัติ |
| `autodj.log` | เหมือน config | Log ไฟล์หมุนเวียน |
| `config.toml.bak` | เหมือน config | Backup จากการบันทึกล่าสุด |

---

## ฟีเจอร์ขั้นสูง

### การยืนยันตัวตน YouTube

```toml
youtube_cookies_file = ""        # Netscape cookies.txt สำหรับ yt-dlp
youtube_cookies_browser = ""     # เช่น "chrome", "firefox", "edge"
youtube_ca_bundle = ""           # Custom CA bundle สำหรับ verify certificate
```

### วิศวกรรมเสียง

```toml
audio_fade = true                # เปิด fade in/out
audio_fade_in_sec = 1.2          # ระยะเวลา fade in
audio_fade_out_sec = 1.5         # ระยะเวลา fade out
audio_normalize = false          # ปรับระดับเสียงไดนามิก (dynaudnorm)
```

### โหวตข้ามแบบไดนามิก

```toml
voteskip_dynamic = false
voteskip_dynamic_pct = 30        # % ของผู้เข้าร่วมที่ต้องการ
```

### จำกัดอัตราต่อผู้ใช้

```toml
user_request_limit = 5           # สูงสุดคำขอ
rate_limit_window = 300.0        # sliding window (วินาที)
```

---

## รายการตรวจสอบการแก้ปัญหา

- [ ] รัน `AutoDJ.exe --check` — เขียวหมด?
- [ ] `mpv --audio-device=help` — อุปกรณ์ถูกต้องใน config?
- [ ] `yt-dlp -U` — เวอร์ชันล่าสุด?
- [ ] Config TOML ถูกต้อง? (ไม่มี syntax error)
- [ ] ชื่อแอดมินอยู่ใน `admins` (ไม่สนใจตัวพิมพ์)?
- [ ] โฟลเดอร์เพลงมีอยู่และอ่านได้?
- [ ] หน้าต่างห้อง Camfrog เปิดอยู่?
- [ ] VB-Cable ติดตั้งและตั้งเป็นไมค์ใน Camfrog?
- [ ] อุปกรณ์เสียงใน config ตรงกับ cable input?
- [ ] Log file เขียนได้? (ตรวจสอบพาธ `log_file`)

---

## การสนับสนุน

- **Logs:** ดู `autodj.log` หรือ output คอนโซล
- **Debug:** รันกับ flag `-v` สำหรับ verbose logging
- **GUI:** ใช้ปุ่ม **Check setup** สำหรับวินิจฉัยภาพ
- **Config:** ใช้กล่องโต้ตอบ **Settings** แก้ไขอย่างปลอดภัย
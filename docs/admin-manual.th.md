# คู่มือแอดมิน AutoDJ — ภาษาไทย

**เวอร์ชัน:** 0.3.10  
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

### AI และการอัปเดต

| คำสั่ง | อัลลิแอส | คำอธิบาย | ตัวอย่าง |
|---------|----------|------------|---------|
| `ai` | `เอไอ` | `on` / `off` / `status` / `model <id>` / `prompt <ข้อความ>` — มีผลทันที (เฉพาะขณะรัน ถ้าต้องการให้ถาวรให้แก้ config.toml) พิมพ์ `!เอไอ` อย่างเดียวจะแสดงสถานะ; `!เอไอ help` ส่งรายการคำสั่งทั้งหมดให้ทาง IM | `!เอไอ status` / `!เอไอ help` |
| `update` | `อัปเดต` | ตรวจสอบเวอร์ชันที่ใหม่กว่าบน GitHub; `apply` = ดาวน์โหลด (ตรวจ SHA-256) แล้วเตรียม `AutoDJ.next.exe` + `autodj_update.bat` | `!อัปเดต` / `!อัปเดต apply` |

### ข้อมูล

| คำสั่ง | อัลลิแอส | คำอธิบาย | ตัวอย่าง |
|---------|----------|------------|---------|
| `help` | `commands`, `ช่วยเหลือ` | แสดงคำสั่งทั้งหมด (รวมแอดมิน) | `!ช่วยเหลือ` |
| `np` | `nowplaying`, `เพลงนี้` | ข้อมูลเพลงปัจจุบัน พร้อมเวลาที่เล่นไป `(เล่นไป/ความยาว)` | `!เพลงนี้` |
| `next` | `upnext`, `ถัดไป` | เพลงถัดไป | `!ถัดไป` |
| `queue` | `q`, `คิว` | คิวทั้งหมด | `!คิว` |
| `voteskip` | `vs`, `โหวตข้าม` | โหวตข้าม (แอดมินใช้ได้) | `!โหวตข้าม` |
| `aplay` | `addm` | ขอเพลงผ่าน IM (alias ของ play) | `/aplay <เพลงหรือลิงก์ YouTube>` |
| `nowp` | `เพลงนี้` | แสดงเพลงปัจจุบัน (alias ของ np) | `/nowp` |
| `skipp` | `ข้ามเพลง` | ข้ามเพลงปัจจุบัน (alias ของ skip) | `/skipp` |
| `lastp` | `ขอล่าสุด` | แสดงเพลงที่เล่นล่าสุด (alias ของ last) | `/lastp` |
| `hbdp` | `hbdm` | อวยพรวันเกิด + เปิดเพลงวันเกิด | `/hbdp <ชื่อ>` |
| `topp` | `topm` | เพลงขอสูงสุดวันนี้/สัปดาห์นี้ | `/topp` หรือ `/topp week` |
| `favp` | `favm` | บันทึกเพลงที่เล่นอยู่ในเพลงโปรด | `/favp` |
| `myfavp` | `myfavm` | ดูเพลงโปรดของตัวเอง | `/myfavp` |
| `hadj` | `helpm`, `คู่มือ` | คู่มือคำสั่งทั้งหมด (ทั้งสองหน้า) | `/hadj` |

---

## การตั้งค่า (config.toml)

### ตั้งค่าแอดมิน (บังคับ)

```toml
# === การตั้งค่าแอดมิน ===
# ใส่นามเดิม Camfrog ของคุณที่นี่ (ไม่สนใจตัวพิมพ์เล็ก/ใหญ่)
admins = ["YourNick", "BackupAdmin"]

# ชื่อของบอทในห้อง (สำหรับตรวจจับข้อความตัวเอง)
bot_nick = "AutoDJ"            # ค่าเริ่มต้น; ตั้งเป็นชื่อที่บอทใช้แชทจริง

# คำนำหน้าคำสั่ง
prefix = "!"
```

### ห้องและการเชื่อมต่อ

```toml
# การตรวจจับหน้าต่างห้อง Camfrog
window_title_re = ".*"              # Regex ชื่อหน้าต่างห้อง
process_re = "(?i)camfrog"          # กรองชื่อโปรเซส
window_exclude_re = ""              # Drop matching titles when several windows match
window_index = 0                    # Pick the Nth remaining match
auto_discover = true                # ตรวจจับห้องอัตโนมัติตอนเริ่มต้น

# แอดอัปเตอร์แชท: "uia" (Windows UI Automation) | "logtail" | "console"
chat_reader = "uia"
chat_sender = "uia"

# เฉพาะ UIA (เติมอัตโนมัติโดย --discover)
view_kind = "auto"                  # auto | web | text
send_mode = "auto"                  # background | foreground | auto
send_verify = true                  # auto: check the line really appeared in the room
web_strict_body = true              # web view: drop plain text right after message body
web_view_title = "wb-log-room-data" # substring of the chat-history pane title
web_input_title = "wb-edit-data"    # substring of the message-box pane title
view_type = "Document"              # (filled in by auto_discover)
view_index = 0
input_type = "Edit"
input_index = -1
line_regex = '^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<user>[^:\s][^:]{0,30}):\s(?P<text>.+)$'
log_path = ""                       # also write the log to this file (rotating, 1 MB x 3)
log_encoding = "utf-8"              # log file encoding
```

### การตั้งค่าเสียง

```toml
# เส้นทาง mpv player (จำเป็น)
mpv_path = "mpv/mpv.exe"            # หรือพาธเต็ม: "C:/mpv/mpv.exe"

# เส้นทาง yt-dlp (ตรวจจับอัตโนมัติถ้าว่าง)
ytdlp_path = ""                     # "" = หาอัตโนมัติ (ข้าง mpv หรือใน PATH); หรือ "C:/mpv/yt-dlp.exe"

# การยืนยันตัวตน YouTube (ตัวเลือก)
youtube_cookies_file = ""           # path to Netscape cookies.txt for yt-dlp
youtube_cookies_browser = ""        # browser name for --cookies-from-browser (e.g. chrome, edge, firefox)
youtube_ca_bundle = ""              # path to custom CA bundle PEM file for yt-dlp certificate verification

# อุปกรณ์เอาท์พุตเสียง (จาก: mpv --audio-device=help)
audio_device = "auto"               # "auto" = system default; หรือ wasapi/{GUID} สำหรับ virtual cable

# เอฟเฟกต์เสียง
audio_fade = true                   # enable audio volume fade-in and fade-out
audio_fade_in_sec = 1.2             # fade-in duration in seconds
audio_fade_out_sec = 1.5            # fade-out duration on skip/stop in seconds
audio_normalize = false             # enable dynamic audio loudness normalization (dynaudnorm)

# ระดับเสียงเริ่มต้น (0-100)
volume = 100
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

# สุ่มสระเพลงอัตโนมัติ (แบบถุงสุ่ม: ไม่ซ้ำจนกว่าจะเล่นครบทุกเพลง; สระเพลงวนเล่นไม่รู้จบ)
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
voteskip_cooldown = 10.0       # วินาทีระหว่างการโหวตข้ามจากผู้ใช้เดียวกัน

# คูลดาวน์และป้องกันน้ำท่วม
cooldown = 3.0                 # วินาทีระหว่างคำสั่งต่อผู้ใช้
send_interval = 1.5            # วินาทีระหว่างข้อความแชท
max_msg_len = 200              # ความยาวข้อความสูงสุด
```

### การประกาศเพลงและตอบ "เพลงอะไร"

```toml
announce_next = true                # ประกาศเพลงถัดไปในแชท

# ตอบข้อความในห้องเช่น "เพลงอะไร" / "what song" โดยไม่ต้องใช้คำสั่ง (ข้อความเดียวกับ !เพลงนี้)
np_question_reply = true
np_question_keywords = ["เพลงอะไร", "เพลงไร", "เพลงชื่อ", "ชื่อเพลง", "เพลงนี้ชื่อ", "what song", "whats playing", "what's playing", "song name"]
np_question_cooldown = 20.0         # วินาทีระหว่างการตอบแต่ละครั้ง ใช้ร่วมทั้งห้อง (0-3600)

# เทมเพลตข้อความ ("" = ใช้ข้อความในตัวตาม `lang`)
msg_now = ""
msg_next = "เพลงต่อไป อีก {eta} เพลง {title} ขอโดย {requester}"
```

- ฟิลด์ในเทมเพลต: `{title}`, `{duration}`, `{requester}` และใหม่ `{elapsed}` / `{remaining}` (เวลาที่เล่นไป/เหลือของเพลงปัจจุบัน) กับ `{eta}` (ใน `msg_next`: อีกนานเท่าไรเพลงนั้นจะเริ่ม) ค่าที่ไม่ทราบจะแสดงเป็น `?` ถ้าเทมเพลตผิดจะกลับไปใช้ข้อความในตัว
- `!np` / `!nowplaying` / `!เพลงนี้` ตอบเป็นข้อความเพลงที่กำลังเล่นพร้อม `(เล่นไป/ความยาว)` เช่น `กำลังเล่น: X [3:20] - ขอโดย bob (1:05/3:20)`
- คีย์เวิร์ดจับแบบหาคำย่อยในข้อความ ไม่สนตัวพิมพ์เล็ก/ใหญ่ ข้อความที่ขึ้นต้นด้วย prefix คำสั่งจะไม่นับ เปิด/ปิดได้ในหน้าตั้งค่าของ GUI ด้วย

### การเล่นอัตโนมัติและพฤติกรรมเวลาว่าง

```toml
# วินาทีที่ไม่มีคำขอจากผู้ใช้ ก่อนสลับไปเล่นอัตโนมัติ
autoplay_idle_timeout = 30.0       # ขั้นต่ำ 30 วินาที

# ความคงที่ของเพลย์ลิสต์
playlist_file = "playlist.json"    # บันทึกคำขอผู้ใช้ที่นี่ (ลบซ้ำ)
playlist_dir = ""         # โฟลเดอร์ไฟล์ .json เพลย์ลิสต์ (โหลดอัตโนมัติตอนเริ่มต้น); "" = ปิดการใช้งาน
search_limit = 1                   # ผลลัพธ์ค้นหา YouTube ต่อ !play ของ non-admin (1 = ผลลัพธ์แรก; สูงสุด 50)

# หมดเวลา mpv (0 = ไม่มี timeout)
mpv_timeout = 30                   # วินาทีรอหนึ่งเพลง mpv ก่อนถือว่า hang
```

- สระเพลงอัตโนมัติวนเล่นไปเรื่อย ๆ ถ้า `shuffle = true` จะไม่เล่นเพลงซ้ำจนกว่าจะเล่นครบทุกเพลงในสระ
- เพลงที่ประกาศว่า "เพลงถัดไป" คือเพลงที่จะเล่นต่อจริงเสมอ
- ประกาศ "กำลังเล่น" ครั้งเดียวต่อเพลง แม้ใช้ `!วนซ้ำ one`

### ทักทายแอดมิน

```toml
# ทักทายแอดมินเมื่อส่งข้อความครั้งแรกในเซสชัน
admin_greeting_enabled = true      # ทักแอดมินเมื่อเข้าห้อง (แทนข้อความต้อนรับ)
admin_greeting_message = "สวัสดีครับแอดมิน {admin} ยินดีต้อนรับกลับมา!"
admin_greeting_cooldown = 3600.0   # วินาทีระหว่างการทักทายต่อแอดมิน (1 ชั่วโมง)
```

### ความปลอดภัย IM (ใหม่ใน 0.3.0)

```toml
# กำหนดให้ผู้ใช้ต้องอยู่ในห้อง (ปรากฏในแชท) จึงจะใช้คำสั่ง IM ได้
im_require_room_presence = true
```

### ตอบกลับอัตโนมัติ (ข้อความตามกำหนด)

```toml
auto_reply_enabled = true
auto_reply_interval = 60.0        # วินาทีระหว่างข้อความ auto-reply (ขั้นต่ำ 60 วินาที)
auto_reply_file = "ads-list.json"  # ไฟล์ JSON เก็บข้อความสำหรับหมุนเวียน
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
    font_family = "Tahoma", 
    font_size = 14, 
    font_color = "#FF0000", 
    bold = true, 
    italic = false, 
    underline = false 
}
```

### การบันทึก Log

```toml
log_file = ""                    # เช่น "autodj.log" (หมุน 1MB x3)
log_path = ""                    # ไดเรกทอรี log แบบกำหนดเอง
log_encoding = "utf-8"

# JSON structured logging
log_json = false                 # enable JSON structured logging output
log_json_fields = [              # extra fields to include in JSON logs
  "request_id", "delivery_id", "user", "track_id", "generation",
  "attempt_id", "category", "stage", "state"
]
```

### เปิดอัตโนมัติ (Windows เท่านั้น)

```toml
auto_launch = false              # เปิด Camfrog และเข้าห้องอัตโนมัติ
camfrog_exe = "%USERPROFILE%\\AppData\\Local\\Programs\\Camfrog Video Chat\\Camfrog Video Chat.exe"  # เส้นทางไฟล์ Camfrog exe
client_title_re = ".*"           # Regex ชื่อหน้าต่างไคลเอนต์หลัก
room = ""                        # ชื่อห้องที่จะเข้าร่วม
join_uri_template = "camfrog://room/{room}"  # URI template พร้อม placeholder {room} (URL-encoded)
launch_timeout = 60              # วินาทีรอหน้าต่างห้อง
```

### ผู้ใช้ที่ถูกบล็อก

```toml
blocked_users = []               # นามเดิมที่คำสั่งจะถูกเพิกเฉย (แอดมินไม่สามารถถูกบล็อกได้)
```

### IM Auto-Reply & Viewer

```toml
im_auto_reply_enabled = true       # enable auto-reply to private/instant messages
im_auto_reply_message = "Thanks for your message! I'm a bot and will respond when I can. Use !help for commands."
im_auto_reply_cooldown = 60.0      # seconds between auto-replies to the same user (avoid spam)
im_viewer_enabled = true           # show the IM / private message viewer tab in the GUI
im_require_room_presence = true    # รับ IM เฉพาะคนที่เคยพิมพ์ในห้อง; คนอื่นได้รับ IM ส่วนตัว
                                   # im_join_room_message (ค่าเริ่มต้น "กรุณาเข้าห้อง camfrog:join:{room} ก่อนขอเพลงครับ"; ครั้งเดียวต่อ im_auto_reply_cooldown)
allow_play_in_room = true          # requests in room chat and by IM; false = IM only
```

### Camfrog RE Integrations (Gift / Avatar / Status / Alerts)

```toml
# Gift / virtual-gift announcement (detect gift messages in room chat)
gift_announce_enabled = true

# Avatar change announcement (detect avatar changes in room chat)
avatar_change_enabled = true

# Status indicator announcement (detect online/away/busy/invisible/admin/moderator/owner)
status_indicator_enabled = true

# Status alerts (detect upgrade/payment-required status text)
status_alert_enabled = true
```

### Welcome Message

```toml
welcome_message_enabled = true     # ทักทายทุกคนที่เข้าห้อง
welcome_message_message = "ยินดีต้อนรับ {user} เข้าสู่ {room} สถานีเพลง อัตโนมัติ 24/7 ชั่วโมง"   # {user}, {room}
welcome_message_cooldown = 3600.0   # วินาทีระหว่างการทักทายคนเดิม (1 ชั่วโมง)
join_line_regex = '...'             # ข้อความแจ้ง "X เข้าห้อง" ต้องมี (?P<user>...) ; "" = ทักเมื่อพิมพ์ครั้งแรก
```

บอทจับการเข้าห้องจากข้อความแจ้งของห้อง ค่าเริ่มต้นรองรับ `*** bob has joined the room`,
`bob has entered the room` และ `สมชาย เข้าสู่ห้อง` ถ้า Camfrog ของคุณใช้ข้อความอื่น ให้คัดลอก
บรรทัดแจ้งเข้าห้องหนึ่งบรรทัดมาปรับ `join_line_regex` ถ้าไม่เห็นข้อความแจ้งเข้าห้อง บอทจะทักตอนผู้ใช้พิมพ์ครั้งแรกแทน
แต่ละคนถูกทักหนึ่งครั้งต่อช่วงคูลดาวน์: แอดมินได้ `admin_greeting_message` คนอื่นได้ `welcome_message_message`

### ทักทายผู้รับไมค์ (DJ)

```toml
mic_greeting_enabled = true        # ทักทายเมื่อห้องแจ้งว่าผู้ใช้ได้รับไมค์
mic_greeting_message = ""          # {user} = ชื่อเล่น; "" = ข้อความเริ่มต้นตามภาษา ("คุณ {user} รับไมค์เป็น DJ ขณะนี้")
mic_greeting_cooldown = 300.0      # วินาทีระหว่างการทักผู้ใช้คนเดิม (0-86400)
```

นับเฉพาะบรรทัดเต็มในรูปแบบ `<ชื่อ> <วลีรับไมค์>` เช่น `Seaza is now speaking`,
`Seaza has the mic`, `Seaza is the DJ`, `Seaza กำลังรับไมค์`, `Seaza กำลังพูด` และต้องเป็นบรรทัดที่
ผู้ส่งคือชื่อนั้นเอง (หรือไม่มีผู้ส่ง เช่นข้อความระบบ) ข้อความแชทปกติเช่น "who is the dj?" จะไม่ทำให้บอททัก
และผู้ใช้คนหนึ่งไม่สามารถทำให้บอทประกาศว่าคนอื่นเป็น DJ ได้ ผู้ใช้ที่ถูกบล็อกจะถูกข้าม ทั้งสามค่าตั้งได้ใน
หน้าต่าง Settings ด้วย ยังไม่ได้ทดสอบกับห้อง Camfrog จริง: ถ้า Camfrog ของคุณใช้ข้อความแจ้งต่างออกไป บอทจะไม่ทัก

### Admin Command Gating (Config-gated Features)

```toml
# Admin mic mute/unmute
admin_mute_mic = true
admin_unmute_mic = true

# Admin block/unblock user
admin_block_user = false
admin_unblock_user = false

# Admin block/unblock bot
admin_block_bot = true
admin_unblock_bot = true

# Admin kick/ban/unban user
admin_kick_user = true
admin_ban_user = true
admin_unban_user = true

# Admin punish user/bot
admin_punish_user = true
admin_punish_bot = true

# Admin delete message
admin_delete_message_enabled = true

# Mic mute state
mute_enabled = false
```

### JSON Structured Logging

```toml
log_json = false                       # enable JSON structured logging output
log_json_fields = [                    # extra fields to include in JSON logs
  "request_id", "delivery_id", "user", "track_id", "generation",
  "attempt_id", "category", "stage", "state"
]
```

### AI ตอบแชท

```toml
ai_enabled = true                  # เปิดเป็นค่าเริ่มต้น แต่ AI จะไม่ทำงานจนกว่าจะตั้ง ai_api_key
ai_api_key = ""                    # NVIDIA key (nvapi-...) from https://build.nvidia.com/settings
ai_base_url = "https://integrate.api.nvidia.com/v1"   # endpoint ที่รองรับ OpenAI API; ต้องเป็น https (http ใช้ได้เฉพาะ localhost/127.0.0.1/::1)
ai_model = "nvidia/llama-3.3-nemotron-super-49b-v1.5"   # NVIDIA API catalog model id
ai_system_prompt = "..."
ai_max_chars = 200                 # ความยาวคำตอบ AI สูงสุด (ตัวอักษร)
ai_user_cooldown = 30.0            # วินาทีระหว่างคำตอบ AI ถึงผู้ใช้คนเดิม
```

- AI ตอบเฉพาะข้อความในห้องที่ไม่ใช่คำสั่ง และ**ไม่ตอบ IM ส่วนตัวเด็ดขาด** (บอทโพสต์ได้แค่ในห้องสาธารณะ ถ้าตอบจะทำให้ข้อความส่วนตัวหลุดออกไป)
- URL ที่ฝังชื่อผู้ใช้/รหัสผ่านจะถูกปฏิเสธ คูลดาวน์ต่อผู้ใช้บังคับใช้จริง และช่วยจำกัดค่าใช้จ่าย API ด้วย
- `!ai on|off|status|model <id>|prompt <ข้อความ>` (แอดมิน) มีผลทันที ส่วนการแก้ config มีผลเมื่อโหลดใหม่ พิมพ์ `!ai` อย่างเดียวจะแสดงสถานะ และ `!ai help` ส่งรายการคำสั่งทั้งหมดทาง IM
- เมื่อตั้ง `ai_api_key` แล้ว ข้อความแชทในห้องที่ไม่ใช่คำสั่งจะถูกส่งไปยัง AI endpoint ที่ตั้งไว้ (ค่าเริ่มต้นคือ NVIDIA) ถ้าไม่ต้องการให้ตั้ง `ai_enabled = false`

### อัปเดตอัตโนมัติ

```toml
auto_update_enabled = false        # ต้องเปิดเอง; ถ้าปิดจะไม่มีการเชื่อมต่อ GitHub เบื้องหลังเลย
auto_update_repo = "cvsz/autodj"
auto_update_check_interval = 21600.0   # วินาที (ขั้นต่ำ 300)
auto_update_asset = "AutoDJ.exe"
```

- เสนอเฉพาะเวอร์ชันที่ใหม่กว่าจริงเท่านั้น เวอร์ชันที่อ่านไม่ออกจะไม่ถือว่าใหม่กว่า
- `!อัปเดต` (แอดมิน) ตรวจสอบทันที; `!อัปเดต apply` ดาวน์โหลดไฟล์และเก็บไว้เฉพาะเมื่อ SHA-256 ตรงกับ `digest` ของ asset บน GitHub หรือไฟล์ `<asset>.sha256` / `SHA256SUMS` ใน release **ผู้ดูแล release ต้องเผยแพร่ค่านี้** มิฉะนั้นจะปฏิเสธการดาวน์โหลด
- ไฟล์ที่ตรวจแล้วจะวางไว้ข้าง exe พร้อม `autodj_update.bat` ให้รันสคริปต์นี้เพื่อสลับไฟล์และเริ่มโปรแกรมใหม่

### Webhook / API Integration

```toml
webhook_enabled = false                # enable HTTP webhook server for external control
webhook_host = "127.0.0.1"             # host to bind webhook server (use 0.0.0.0 for external access)
webhook_port = 8080                    # port for webhook server
webhook_secret = ""                    # คีย์ HMAC ยาวอย่างน้อย 16 ตัวอักษร; ว่าง/สั้นเกินไป = ทุกคำขอถูกปฏิเสธด้วย 503
webhook_rate_limit_per_ip = 60         # max requests per IP per minute
webhook_cors_origins = ["http://127.0.0.1:8080"]           # CORS allowed origins (e.g. ["https://example.com"]; default ["http://127.0.0.1:8080"])
```

การลงลายเซ็นคำขอ (ทุกคำขอ):

- `X-Timestamp`: เวลา unix (วินาที) ต้องต่างจากนาฬิกาเซิร์ฟเวอร์ไม่เกิน 300 วินาที
- `X-Signature`: ค่า hex ของ `HMAC-SHA256(webhook_secret, f"{timestamp}.{METHOD}.{path}." + raw_body)`
- ลายเซ็นแต่ละอันใช้ได้ครั้งเดียว (ส่งซ้ำได้ 401) ไม่มี/หมดอายุ/ไม่ถูกต้อง = 401; เกิน `webhook_rate_limit_per_ip` = 429

```python
import hashlib, hmac, time
ts = str(int(time.time()))
sig = hmac.new(secret.encode(), f"{ts}.POST./webhook/skip.".encode() + body, hashlib.sha256).hexdigest()
```

> **หมายเหตุ:** มีโค้ดเซิร์ฟเวอร์ webhook แล้ว แต่ engine ยังไม่ได้สั่งเริ่มเซิร์ฟเวอร์ตอนรันจริง ตอนนี้ตั้ง `webhook_enabled = true` จึงยังไม่มีผล

### Config Hot Reload

```toml
config_hot_reload = false              # enable hot reload of config.toml (requires 'watchdog' extra: pip install -e .[hotreload])
```

### Plugin System

```toml
plugins = ["builtin.stats", "builtin.help"]  # list of plugin modules to load (e.g. "builtin.stats", "myplugin")
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
- ตอนบันทึกจะคงค่าที่หน้าตั้งค่าไม่ได้แสดงไว้ (`ai_*`, `auto_update_*`, `webhook_secret`, `voteskip_cooldown`, `log_json*`) ไม่รีเซ็ตเป็นค่าเริ่มต้นแล้ว
- ปุ่มเปิด/ปิดการตอบคำถาม "เพลงอะไร" ในห้อง (`np_question_reply`)
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
make installer        # หรือ: powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1
```

ต้อง build `dist\AutoDJ.exe` ก่อน (`make build` หรือ `make build-all` สำหรับ exe + installer)
`scripts/build_installer.ps1` จะคัดลอก `config.example.toml` ล่าสุดไปเป็น `dist\config.toml`
(พร้อม README, CHANGELOG และ LICENSE) ทุกครั้งที่รัน ใส่เวอร์ชันจาก `pyproject.toml` ลงใน `installer.nsi`
แล้วจึงรัน `makensis` การรัน `makensis installer.nsi` เองจะข้ามขั้นตอนนี้และอาจได้ config เก่าติดไปกับตัวติดตั้ง
ไฟล์ `config.toml` ของนักพัฒนาจะไม่ถูกรวมเข้าไปเด็ดขาด

### คุณสมบัติ Installer

- ติดตั้งต่อผู้ใช้ไป `%APPDATA%\CamfrogAutoDJ` (ไม่ต้อง admin)
- ติดตั้ง `config.toml` จาก `config.example.toml`; ถ้ามี `config.toml` อยู่แล้วจะเก็บไว้ตอนอัปเกรด
- เขียน `mpv_path` / `ytdlp_path` แบบพาธเต็มของ mpv ที่มากับตัวติดตั้งลงใน `config.toml` (`AutoDJ.exe --write-install-paths`)
- ส่วนเสริม: mpv + yt-dlp ติดตั้งใน `%APPDATA%\CamfrogAutoDJ\mpv` (ไม่ใช่ `%APPDATA%\mpv` ซึ่งเป็นโฟลเดอร์ตั้งค่าของ mpv เอง)
- ปิด AutoDJ / mpv ที่รันจากโฟลเดอร์ติดตั้งก่อนอัปเกรดหรือถอนการติดตั้ง
- Shortcut ใน Start Menu (AutoDJ, Edit Config, Uninstall) และบน Desktop
- มี `install.ps1` สำหรับติดตั้ง VB-CABLE และโปรแกรมที่จำเป็นอื่น (ไม่ได้รวม VB-CABLE มาในตัวติดตั้ง)
- Uninstaller เก็บ `config.toml`, เพลย์ลิสต์, log และข้อมูลผู้ใช้ไว้

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
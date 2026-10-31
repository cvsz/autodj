#!/usr/bin/env python3
"""
Camfrog AutoDJ - Launcher

ช่วยเรียกใช้ AutoDJ ได้ง่ายขึ้น โดยไม่ต้องพิมพ์คำสั่งยาว ๆ

ตัวอย่างการใช้งาน:
    python launch_autodj.py --gui          เปิดหน้าต่างเดสก์ท็อป
    python launch_autodj.py --console      โหมดคอนโซล (ภาษาไทย)
    python launch_autodj.py --check        ตรวจสอบการตั้งค่า
    python launch_autodj.py --discover     ค้นหาห้อง Camfrog อัตโนมัติ
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Camfrog AutoDJ Launcher - เรียกใช้ AutoDJ ได้ง่ายขึ้น"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="เปิดหน้าต่างเดสก์ท็อป GUI (ค่าเริ่มต้นถ้าไม่ระบุตัวเลือก)",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="โหมดคอนโซล (พิมพ์คำสั่งผ่านแป้นพิมพ์)",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "th"],
        default="th",
        help="ภาษาของบอท (ค่าเริ่มต้น: th)",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="เส้นทางไปยังไฟล์ config.toml (ค่าเริ่มต้น: config.toml)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="ตรวจสอบการตั้งค่าว่าครบถ้วนหรือไม่ แล้วออก",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="ค้นหาห้อง Camfrog และบันทึกการตั้งค่าลง config.toml แล้วออก",
    )
    parser.add_argument(
        "--say",
        metavar="TEXT",
        help="ส่งข้อความเข้าไปในห้องแชทครั้งเดียวแล้วออก",
    )
    parser.add_argument(
        "--no-discover",
        action="store_true",
        help="ข้ามการค้นหาห้องอัตโนมัติตอนเริ่มต้น",
    )

    args = parser.parse_args()

    # ตรวจสอบว่า config.toml มีอยู่หรือไม่
    config_path = Path(args.config)
    if not config_path.exists():
        example = Path("config.example.toml")
        if example.exists():
            print(
                f"[!] ไม่พบไฟล์ {args.config} พบไฟล์ตัวอย่าง {example} แทน"
            )
            print(f"    แนะนำให้คัดลอก: copy {example} {args.config}")
        else:
            print(f"[!] ไม่พบไฟล์ตั้งค่า {args.config}")
            print("    โปรดสร้างไฟล์ config.toml ก่อนรัน AutoDJ")
        sys.exit(1)

    # สร้างคำสั่งสำหรับเรียก AutoDJ
    cmd = [sys.executable, "-m", "camfrog_autodj", "-c", str(config_path)]

    if args.lang:
        cmd.extend(["--lang", args.lang])

    if args.check:
        cmd.append("--check")
    elif args.discover:
        cmd.append("--discover")
    elif args.say:
        cmd.extend(["--say", args.say])
    elif args.console:
        cmd.append("--console")
    elif args.gui or not any([args.check, args.discover, args.say, args.console]):
        cmd.append("--gui")

    if args.no_discover and not (args.check or args.discover or args.say):
        cmd.append("--no-discover")

    print(f"[AutoDJ] กำลังรัน: {' '.join(cmd)}")
    print("-" * 60)

    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n[AUTO DJ] ผู้ใช้หยุดการทำงาน")
    except Exception as exc:
        print(f"\n[AUTO DJ] เกิดข้อผิดพลาด: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Interface translations. PDF content and settings values retain their original text."""

import re

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
)

THAI = {
    "Home": "หน้าหลัก",
    "Settings": "การตั้งค่า",
    "About": "เกี่ยวกับ",
    "Merge / Append": "รวมไฟล์ PDF",
    "Split PDF": "แยกไฟล์ PDF",
    "Remove / Extract": "ลบหรือดึงหน้า",
    "PDF to JPG / PNG": "แปลง PDF เป็น JPG / PNG",
    "Edit PDF": "แก้ไข PDF",
    "Browse files…": "เลือกไฟล์…",
    "Add PDFs…": "เพิ่มไฟล์ PDF…",
    "Add a page range…": "เพิ่มช่วงหน้า…",
    "Drop PDF, JPG or PNG files here": "วางไฟล์ PDF, JPG หรือ PNG ที่นี่",
    "Select files, or paste copied files with Ctrl+V.": "เลือกไฟล์ หรือวางไฟล์ที่คัดลอกด้วย Ctrl+V",
    "Search tools": "ค้นหาเครื่องมือ",
    "All tools": "เครื่องมือทั้งหมด",
    "Documents are processed locally": "ประมวลผลเอกสารบนเครื่องนี้",
    "Export…": "ส่งออก…",
    "Save": "บันทึก",
    "Save as…": "บันทึกเป็น…",
    "Previous": "ก่อนหน้า",
    "Next": "ถัดไป",
    "Fit page": "พอดีหน้า",
    "Fit width": "พอดีความกว้าง",
    "Pan": "เลื่อนหน้า",
    "Undo": "เลิกทำ",
    "Redo": "ทำซ้ำ",
    "Delete": "ลบ",
    "Remove": "นำออก",
    "Duplicate": "ทำสำเนา",
    "Invert": "สลับการเลือก",
    "Split here": "แยกตรงนี้",
    "Use range": "เลือกช่วงหน้า",
    "Insert image": "แทรกรูปภาพ",
    "Object properties": "คุณสมบัติวัตถุ",
    "Export as ZIP": "ส่งออกเป็น ZIP",
    "Check for updates": "ตรวจสอบการอัปเดต",
    "Language": "ภาษา",
    "Theme": "ธีม",
    "System": "ตามระบบ",
    "Light": "สว่าง",
    "Dark": "มืด",
    "Version {version}": "เวอร์ชัน {version}",
    "About PDF Toolbox": "เกี่ยวกับ PDF Toolbox",
    "Local desktop PDF tools": "เครื่องมือ PDF สำหรับใช้งานบนเครื่อง",
    "Combine documents and arrange pages": "รวมเอกสารและจัดลำดับหน้า",
    "Divide a document into separate files": "แยกเอกสารเป็นหลายไฟล์",
    "Keep, remove or extract selected pages": "เก็บ ลบ หรือดึงหน้าที่เลือก",
    "Export pages at the resolution you choose": "ส่งออกหน้าตามความละเอียดที่เลือก",
    "Add text, pictures and shapes": "เพิ่มข้อความ รูปภาพ และรูปร่าง",
    "Drop PDFs, arrange the pages, then export the combined document.": "วางไฟล์ PDF จัดลำดับหน้า แล้วส่งออกเอกสารที่รวมแล้ว",
    "Drop a PDF and choose how to divide it into separate files.": "วางไฟล์ PDF แล้วเลือกวิธีแยกเป็นหลายไฟล์",
    "Select pages to remove or extract. Drag pages to change their order.": "เลือกหน้าที่ต้องการลบหรือดึง ลากหน้าเพื่อเปลี่ยนลำดับ",
    "Drop PDFs, select pages, and choose an image format and resolution.": "วางไฟล์ PDF เลือกหน้า รูปแบบภาพ และความละเอียด",
    "Individual pages": "แยกทีละหน้า",
    "Every N pages": "แบ่งทุก N หน้า",
    "Custom ranges": "กำหนดช่วงหน้า",
    "Boundaries": "กำหนดจุดแยก",
    "Filename prefix or {n} pattern": "คำนำหน้าชื่อไฟล์หรือรูปแบบ {n}",
    "Custom": "กำหนดเอง",
    "JPG quality ": "คุณภาพ JPG ",
    "JPG quality": "คุณภาพ JPG",
    "Transparent PNG": "PNG พื้นหลังโปร่งใส",
    "Save page order": "บันทึกลำดับหน้า",
    "Remove selected": "ลบหน้าที่เลือก",
    "Extract selected": "ดึงหน้าที่เลือกเป็นไฟล์เดียว",
    "Extract selected separately": "ดึงหน้าที่เลือกเป็นไฟล์แยก",
    "Append at end": "ต่อท้าย",
    "Insert before current page": "แทรกก่อนหน้าปัจจุบัน",
    "size unavailable": "ไม่ทราบขนาดไฟล์",
    "Double-click to jump to its first page.": "ดับเบิลคลิกเพื่อไปหน้าแรกของไฟล์",
    "Pages per file": "จำนวนหน้าต่อไฟล์",
    "Groups such as 1-3;4-6;7": "กลุ่มหน้า เช่น 1-3;4-6;7",
    "Split after pages such as 2,4": "แยกหลังหน้าที่ระบุ เช่น 2,4",
    "All pages": "ทุกหน้า",
    "Page range, e.g. 1–3,5": "ช่วงหน้า เช่น 1-3,5",
    "Page range, e.g. 1-3,5": "ช่วงหน้า เช่น 1-3,5",
    "{documents} PDF(s) · {pages} pages · {selection} selected": "PDF {documents} ไฟล์ · {pages} หน้า · เลือก {selection} หน้า",
    "{pages} pages · {size}": "{pages} หน้า · {size}",
    "{count} remaining": "เหลือ {count} หน้า",
    "{count} output files": "ไฟล์ที่จะส่งออก {count} ไฟล์",
    "▼ Split after": "▼ แยกหลังหน้านี้",
    "Preview ≈ {width} × {height} px": "ขนาดภาพโดยประมาณ {width} × {height} พิกเซล",
    "Select": "เลือก",
    "Text": "ข้อความ",
    "Font": "แบบอักษร",
    "Align": "การจัดแนว",
    "Left": "ซ้าย",
    "Center": "กึ่งกลาง",
    "Right": "ขวา",
    "Font size": "ขนาดตัวอักษร",
    "Width": "ความกว้าง",
    "Height": "ความสูง",
    "Rotation": "มุมหมุน",
    "Opacity %": "ความทึบ %",
    "Border width": "ความหนาเส้นขอบ",
    "Bold": "ตัวหนา",
    "Italic": "ตัวเอียง",
    "Underline": "ขีดเส้นใต้",
    "Lock aspect ratio": "คงอัตราส่วน",
    "Text / border color": "สีข้อความหรือเส้นขอบ",
    "Fill color": "สีพื้น",
    "Choose color": "เลือกสี",
    "Rectangle": "สี่เหลี่ยม",
    "Rounded rectangle": "สี่เหลี่ยมมุมมน",
    "Ellipse": "วงรี",
    "Circle": "วงกลม",
    "Line": "เส้นตรง",
    "Arrow": "ลูกศร",
    "Freehand": "วาดอิสระ",
    "Highlight": "ไฮไลต์",
    "Filled rectangle": "สี่เหลี่ยมทึบ",
    "Copy": "คัดลอก",
    "Cut": "ตัด",
    "Bring forward": "เลื่อนขึ้นหนึ่งชั้น",
    "Send backward": "เลื่อนลงหนึ่งชั้น",
    "Bring to front": "นำขึ้นหน้าสุด",
    "Send to back": "ส่งไปหลังสุด",
    "Page {page}": "หน้า {page}",
    "Page {page} of {total}": "หน้า {page} จาก {total}",
    "No page selected": "ยังไม่ได้เลือกหน้า",
    "Rendering page…": "กำลังแสดงตัวอย่างหน้า…",
    "This page could not be rendered.": "แสดงตัวอย่างหน้านี้ไม่ได้",
    "Default output folder": "โฟลเดอร์ส่งออกเริ่มต้น",
    "Choose folder…": "เลือกโฟลเดอร์…",
    "Default image DPI": "ความละเอียดภาพเริ่มต้น (DPI)",
    "Check GitHub for updates in the background": "ตรวจสอบอัปเดตจาก GitHub ในเบื้องหลัง",
    "Software updates": "การอัปเดตซอฟต์แวร์",
    "Check interval (hours)": "ตรวจสอบทุก (ชั่วโมง)",
    "Last check": "ตรวจสอบล่าสุด",
    "No update checks yet": "ยังไม่ได้ตรวจสอบการอัปเดต",
    "Manage GitHub credential…": "จัดการโทเค็น GitHub…",
    "Clear preview cache": "ล้างแคชตัวอย่าง",
    "Reset preferences": "คืนค่าการตั้งค่าเริ่มต้น",
    "Enable update checks?": "เปิดการตรวจสอบอัปเดตหรือไม่",
    "PDF Toolbox will contact the configured GitHub repository to check for new installers. It sends no document or clipboard information.": "PDF Toolbox จะติดต่อคลัง GitHub ที่ตั้งค่าไว้เพื่อตรวจสอบตัวติดตั้งใหม่ โดยไม่ส่งข้อมูลเอกสารหรือคลิปบอร์ด",
    "GitHub update credential": "โทเค็น GitHub สำหรับอัปเดต",
    "Paste a read-only token for the update repository. Leave blank to remove it.": "วางโทเค็นแบบอ่านอย่างเดียวสำหรับคลังอัปเดต เว้นว่างเพื่อลบโทเค็น",
    "GitHub update credential preference saved.": "บันทึกการตั้งค่าโทเค็น GitHub แล้ว",
    "Reset preferences?": "คืนค่าการตั้งค่าเริ่มต้นหรือไม่",
    "This restores the default app preferences.": "การตั้งค่าแอปจะกลับเป็นค่าเริ่มต้น",
    "Wait for the current PDF operation to finish.": "โปรดรอให้การประมวลผล PDF เสร็จสิ้น",
    "Choose files": "เลือกไฟล์",
    "PDF and images (*.pdf *.jpg *.jpeg *.png)": "PDF และรูปภาพ (*.pdf *.jpg *.jpeg *.png)",
    "PDF files (*.pdf)": "ไฟล์ PDF (*.pdf)",
    "Images (*.png *.jpg *.jpeg)": "รูปภาพ (*.png *.jpg *.jpeg)",
    "Choose a PDF for page insertion": "เลือก PDF ที่จะนำหน้ามาแทรก",
    "Choose a local PDF file.": "เลือกไฟล์ PDF บนเครื่องนี้",
    "Choose one PDF for this tool.": "เลือก PDF หนึ่งไฟล์สำหรับเครื่องมือนี้",
    "Open a PDF for image insertion": "เปิด PDF ที่จะแทรกรูปภาพ",
    "Choose files on this computer.": "เลือกไฟล์บนเครื่องนี้",
    "Password protected PDF": "PDF ที่ป้องกันด้วยรหัสผ่าน",
    "Password for {name}": "รหัสผ่านสำหรับ {name}",
    "Insert a page range": "แทรกช่วงหน้า",
    "{name} has {total} pages. Enter a range such as 1-3,5.": "{name} มี {total} หน้า ระบุช่วงหน้า เช่น 1-3,5",
    "Opening PDF…": "กำลังเปิด PDF…",
    "Unsaved changes": "มีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก",
    "Choose output folder": "เลือกโฟลเดอร์ส่งออก",
    "Save as PDF": "บันทึกเป็น PDF",
    "Choose an output location on this computer.": "เลือกตำแหน่งส่งออกบนเครื่องนี้",
    "Exporting PDF pages…": "กำลังส่งออกหน้า PDF…",
    "Saving edited PDF…": "กำลังบันทึก PDF ที่แก้ไข…",
    "Save changes?": "บันทึกการเปลี่ยนแปลงหรือไม่",
    "The PDF has unsaved edits.": "PDF นี้มีการแก้ไขที่ยังไม่ได้บันทึก",
    "Cancelling…": "กำลังยกเลิก…",
    "Export complete": "ส่งออกเสร็จแล้ว",
    "Saved {count} file(s).": "บันทึกแล้ว {count} ไฟล์",
    "Open folder": "เปิดโฟลเดอร์",
    "Open file": "เปิดไฟล์",
    "Preview cache cleared.": "ล้างแคชตัวอย่างแล้ว",
    "Licenses": "สัญญาอนุญาต",
    "User guide": "คู่มือการใช้งาน",
    "OK": "ตกลง",
    "Cancel": "ยกเลิก",
    "Close": "ปิด",
    "Discard": "ละทิ้ง",
    "Yes": "ใช่",
    "No": "ไม่",
    "Update available": "มีอัปเดต",
    "Updates are unavailable for this build.": "บิลด์นี้ไม่รองรับการอัปเดตอัตโนมัติ",
    "Update check could not finish.": "ตรวจสอบการอัปเดตไม่สำเร็จ",
    "This version is current.": "เวอร์ชันนี้เป็นเวอร์ชันล่าสุดแล้ว",
    "The available version was skipped.": "ข้ามเวอร์ชันที่มีให้อัปเดตแล้ว",
    "Version {version} is available.": "มีเวอร์ชัน {version} ให้อัปเดต",
    "Installed {installed} • Available {latest}": "ติดตั้งอยู่ {installed} • มีเวอร์ชัน {latest}",
    "Show Details…": "แสดงรายละเอียด…",
    "Hide Details…": "ซ่อนรายละเอียด…",
    "Update now": "อัปเดตตอนนี้",
    "Later": "ภายหลัง",
    "Skip this version": "ข้ามเวอร์ชันนี้",
    "Downloading verified update…": "กำลังดาวน์โหลดอัปเดต…",
    "Downloaded {current:.1f} of {total:.1f} MB": "ดาวน์โหลดแล้ว {current:.1f} จาก {total:.1f} MB",
    "Update download ended before installation.": "การดาวน์โหลดอัปเดตสิ้นสุดก่อนติดตั้ง",
    "Ready to install": "พร้อมติดตั้ง",
    "Update verified. Select Ready to install when you’re ready.": "ตรวจสอบอัปเดตแล้ว เลือก «พร้อมติดตั้ง» เมื่อต้องการติดตั้ง",
    "Install update?": "ติดตั้งอัปเดตหรือไม่",
    "PDF Toolbox will close and start the verified installer.": "PDF Toolbox จะปิดแล้วเปิดตัวติดตั้งที่ตรวจสอบแล้ว",
    "The installer could not start. Try again.": "เปิดตัวติดตั้งไม่ได้ โปรดลองอีกครั้ง",
    "The downloaded installer could not be verified. Download it again.": "ตรวจสอบตัวติดตั้งที่ดาวน์โหลดไม่ได้ โปรดดาวน์โหลดอีกครั้ง",
    "Updated to {version}.": "อัปเดตเป็นเวอร์ชัน {version} แล้ว",
    "The update did not complete. You can continue using this version.": "อัปเดตไม่สำเร็จ คุณยังใช้เวอร์ชันนี้ต่อได้",
    "Wait for the current PDF operation to finish or cancel it first.": "โปรดรอให้การประมวลผล PDF เสร็จ หรือยกเลิกก่อน",
    "Wait for the update task to finish before closing.": "โปรดรอให้งานอัปเดตเสร็จก่อนปิดแอป",
    "Split handles one PDF at a time. Remove the current pages first.": "เครื่องมือแยกไฟล์รองรับ PDF ทีละไฟล์ โปรดนำหน้าปัจจุบันออกก่อน",
    "Select a page before the last page to place a split after it.": "เลือกหน้าก่อนหน้าสุดท้ายเพื่อแยกหลังหน้านั้น",
    "Add a PDF first.": "เพิ่ม PDF ก่อน",
    "Select one or more pages.": "เลือกอย่างน้อยหนึ่งหน้า",
    "The output must contain at least one page.": "ไฟล์ผลลัพธ์ต้องมีอย่างน้อยหนึ่งหน้า",
    "Choose a PDF, JPG or PNG file.": "เลือกไฟล์ PDF, JPG หรือ PNG",
    "This image could not be opened.": "เปิดรูปภาพนี้ไม่ได้",
    "Open a PDF before inserting an image.": "เปิด PDF ก่อนแทรกรูปภาพ",
    "This image is too large. Resize it before inserting.": "รูปภาพใหญ่เกินไป โปรดย่อขนาดก่อนแทรก",
    "Cancelled. No output files were saved.": "ยกเลิกแล้ว ไม่มีการบันทึกไฟล์ผลลัพธ์",
    "Access was denied. Choose a folder you can write to.": "ไม่มีสิทธิ์เข้าถึง เลือกโฟลเดอร์ที่คุณเขียนไฟล์ได้",
    "The file could not be read or saved. Check access and available disk space.": "อ่านหรือบันทึกไฟล์ไม่ได้ ตรวจสอบสิทธิ์เข้าถึงและพื้นที่ดิสก์",
    "The PDF could not be processed. Check that the file opens in a PDF reader.": "ประมวลผล PDF ไม่ได้ ลองเปิดไฟล์ด้วยโปรแกรมอ่าน PDF",
    "Enter page numbers or ranges such as 1-3,5.": "ระบุหมายเลขหน้าหรือช่วงหน้า เช่น 1-3,5",
    "Each range must be in ascending order within pages 1–{count}.": "แต่ละช่วงต้องเรียงจากน้อยไปมากและอยู่ภายในหน้า 1–{count}",
    "Page ranges must not overlap or repeat a page.": "ช่วงหน้าต้องไม่ซ้อนกันหรือมีหน้าซ้ำ",
    "Add a PDF before splitting.": "เพิ่ม PDF ก่อนแยกไฟล์",
    "Split groups must not overlap.": "กลุ่มหน้าที่แยกต้องไม่ซ้อนกัน",
    "Enter a positive number of pages per file.": "ระบุจำนวนหน้าต่อไฟล์ที่มากกว่าศูนย์",
    "Enter the password for this PDF.": "ระบุรหัสผ่านสำหรับ PDF นี้",
    "This PDF has no pages.": "PDF นี้ไม่มีหน้าเอกสาร",
    "This page has invalid dimensions.": "ขนาดของหน้านี้ไม่ถูกต้อง",
    "The output image is too large. Choose a lower DPI.": "ภาพผลลัพธ์ใหญ่เกินไป เลือกค่า DPI ที่ต่ำลง",
    "Choose a supported output format, DPI and quality.": "เลือกชนิดไฟล์ ค่า DPI และคุณภาพที่รองรับ",
    "An output PDF needs at least one page.": "PDF ผลลัพธ์ต้องมีอย่างน้อยหนึ่งหน้า",
    "Choose a valid Windows output filename.": "เลือกชื่อไฟล์ผลลัพธ์ที่ใช้ได้บน Windows",
    "Choose a filename pattern that produces unique names.": "เลือกรูปแบบชื่อไฟล์ที่ให้ชื่อไม่ซ้ำกัน",
    "An output file already exists. Choose a new name or folder.": "มีไฟล์ผลลัพธ์ชื่อนี้แล้ว เลือกชื่อหรือโฟลเดอร์ใหม่",
    "The release does not have a valid stable version.": "รุ่นเผยแพร่ไม่มีหมายเลขเวอร์ชันเสถียรที่ถูกต้อง",
    "The update repository is not configured.": "ยังไม่ได้ตั้งค่าคลังสำหรับอัปเดต",
    "The update verification key is not configured.": "ยังไม่ได้ตั้งค่าคีย์ตรวจสอบอัปเดต",
    "The Windows publisher policy is invalid.": "การตั้งค่านโยบายผู้เผยแพร่บน Windows ไม่ถูกต้อง",
    "The release information could not be verified.": "ตรวจสอบความถูกต้องของข้อมูลรุ่นเผยแพร่ไม่ได้",
    "The installer size does not match the signed release.": "ขนาดตัวติดตั้งไม่ตรงกับข้อมูลรุ่นที่ลงลายเซ็น",
    "The installer checksum does not match the signed release.": "ค่าแฮชของตัวติดตั้งไม่ตรงกับข้อมูลรุ่นที่ลงลายเซ็น",
    "Windows publisher trust verification requires Windows.": "การตรวจสอบผู้เผยแพร่ต้องทำบน Windows",
    "Windows could not verify the installer publisher.": "Windows ตรวจสอบผู้เผยแพร่ตัวติดตั้งไม่ได้",
    "GitHub returned an unexpected download redirect.": "GitHub เปลี่ยนเส้นทางดาวน์โหลดไปยังปลายทางที่ไม่คาดไว้",
    "Private updates need a GitHub credential in Settings.": "อัปเดตจากคลังส่วนตัวต้องใช้โทเค็น GitHub ในการตั้งค่า",
    "GitHub’s update check limit was reached. Try again later.": "ตรวจสอบอัปเดตถึงขีดจำกัดของ GitHub แล้ว ลองใหม่ภายหลัง",
    "The release is unavailable. Check the repository and credential.": "เข้าถึงรุ่นเผยแพร่ไม่ได้ ตรวจสอบคลังและโทเค็น",
    "GitHub could not serve this update. Try again later.": "GitHub ไม่สามารถส่งอัปเดตนี้ได้ ลองใหม่ภายหลัง",
    "GitHub could not be reached. Try again when online.": "ติดต่อ GitHub ไม่ได้ ลองใหม่เมื่อเชื่อมต่ออินเทอร์เน็ต",
    "GitHub returned unexpectedly large release information.": "ข้อมูลรุ่นเผยแพร่จาก GitHub มีขนาดใหญ่เกินคาด",
    "The GitHub release metadata or required assets are invalid.": "ข้อมูลรุ่นหรือไฟล์ที่จำเป็นใน GitHub ไม่ถูกต้อง",
    "GitHub lists a different installer size than the signed release.": "ขนาดตัวติดตั้งใน GitHub ไม่ตรงกับข้อมูลรุ่นที่ลงลายเซ็น",
    "Free some disk space before downloading the installer.": "เพิ่มพื้นที่ว่างบนดิสก์ก่อนดาวน์โหลดตัวติดตั้ง",
    "The installer is larger than the signed release.": "ตัวติดตั้งใหญ่กว่าที่ระบุในข้อมูลรุ่นที่ลงลายเซ็น",
    "Windows Credential Manager could not read the update token.": "ตัวจัดการข้อมูลประจำตัวของ Windows อ่านโทเค็นอัปเดตไม่ได้",
    "Windows Credential Manager could not save the change.": "ตัวจัดการข้อมูลประจำตัวของ Windows บันทึกการเปลี่ยนแปลงไม่ได้",
}


def thai_enabled(widget):
    prefs = getattr(widget.window(), "prefs", None)
    return prefs is not None and prefs.value("language", "English") == "ไทย"


def translate_text(source, thai):
    if not thai:
        return source
    if source in THAI:
        return THAI[source]
    if "\n" in source:
        return "\n".join(THAI.get(line, line) for line in source.split("\n"))
    # The range error and saved status from older builds arrive already formatted.
    for pattern, template in (
        (
            r"Each range must be in ascending order within pages 1–(\d+)\.",
            "Each range must be in ascending order within pages 1–{count}.",
        ),
        (r"Version ([0-9.]+) is available\.", "Version {version} is available."),
    ):
        match = re.fullmatch(pattern, source)
        if match:
            return THAI[template].format(count=match[1], version=match[1])
    return source


def tr(widget, source, **values):
    text = translate_text(source, thai_enabled(widget))
    return text.format(**values) if values else text


class Choice(QComboBox):
    """Keep canonical option values stable as the visible captions change."""

    def addItems(self, texts):
        for text in texts:
            self.addItem(text, text)

    def setCurrentText(self, text):
        index = self.findData(text)
        if index >= 0:
            self.setCurrentIndex(index)
        else:
            super().setCurrentText(text)

    def retranslate(self):
        with QSignalBlocker(self):
            for index in range(self.count()):
                self.setItemText(index, tr(self, self.itemData(index)))


def retranslate_controls(window):
    thai = thai_enabled(window)

    def refresh(widget, read, write, key):
        current = read()
        source = widget.property(key)
        if source is None or current not in (source, translate_text(source, True)):
            source = current
        translated = translate_text(source, thai)
        if translated != current:
            widget.setProperty(key, source)
            write(translated)

    for widget in window.findChildren(QLabel) + window.findChildren(QAbstractButton):
        refresh(widget, widget.text, widget.setText, "translation_source")
        refresh(widget, widget.toolTip, widget.setToolTip, "translation_tooltip")
    for widget in window.findChildren(QLineEdit):
        refresh(widget, widget.placeholderText, widget.setPlaceholderText, "translation_hint")
    for widget in window.findChildren(QSpinBox):
        refresh(widget, widget.prefix, widget.setPrefix, "translation_prefix")
    for widget in window.findChildren(Choice):
        widget.retranslate()


def localize_buttons(box, *buttons):
    captions = {
        QMessageBox.StandardButton.Ok: "OK",
        QMessageBox.StandardButton.Save: "Save",
        QMessageBox.StandardButton.Discard: "Discard",
        QMessageBox.StandardButton.Cancel: "Cancel",
        QMessageBox.StandardButton.Close: "Close",
        QMessageBox.StandardButton.Yes: "Yes",
        QMessageBox.StandardButton.No: "No",
    }
    for button in buttons:
        box.button(button).setText(tr(box.parentWidget(), captions[button]))


def ask_text(parent, title, label, echo=QLineEdit.EchoMode.Normal):
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(tr(parent, title))
    dialog.setLabelText(tr(parent, label))
    dialog.setTextEchoMode(echo)
    dialog.setOkButtonText(tr(parent, "OK"))
    dialog.setCancelButtonText(tr(parent, "Cancel"))
    accepted = dialog.exec() == dialog.DialogCode.Accepted
    return dialog.textValue() if accepted else "", accepted

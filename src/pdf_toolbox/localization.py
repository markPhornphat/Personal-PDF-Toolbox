"""Interface translations. PDF content and settings values retain their original text."""

import re

from PySide6.QtCore import QSignalBlocker, Qt
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
    "Drop a file to\nget started": "วางไฟล์\nเพื่อเริ่มต้น",
    "PDF, JPG or PNG. Paste files with Ctrl+V.": "PDF, JPG หรือ PNG วางไฟล์ที่คัดลอกด้วย Ctrl+V",
    "Dog with an ice cream cone": "น้องหมากับไอศกรีมโคน",
    "PDF tools": "เครื่องมือ PDF",
    "No tools match your search.": "ไม่พบเครื่องมือที่ตรงกับการค้นหา",
    "Preferences": "ค่ากำหนด",
    "Documents": "เอกสาร",
    "Pages": "หน้าเอกสาร",
    "Move up": "เลื่อนขึ้น",
    "Move down": "เลื่อนลง",
    "Home": "หน้าหลัก",
    "Settings": "การตั้งค่า",
    "About": "เกี่ยวกับ",
    "A new version is ready": "มีเวอร์ชันใหม่พร้อมอัปเดต",
    "Update now to install and reopen PDF Toolbox automatically.": "อัปเดตตอนนี้เพื่อติดตั้งและเปิด PDF Toolbox อีกครั้งโดยอัตโนมัติ",
    "Remind me later": "เตือนฉันภายหลัง",
    "Checking for updates…": "กำลังตรวจสอบการอัปเดต…",
    "Downloading and verifying update…": "กำลังดาวน์โหลดและตรวจสอบการอัปเดต…",
    "Check on the first launch each day and after Windows restarts.": "ตรวจสอบเมื่อเปิดแอปครั้งแรกของวันและหลังรีสตาร์ต Windows",
    "Update cancelled.": "ยกเลิกการอัปเดตแล้ว",
    "The verified update is ready. Automatic installation requires the installed app.": "ตรวจสอบอัปเดตแล้ว การติดตั้งอัตโนมัติต้องทำผ่านแอปที่ติดตั้งไว้",
    "Merge / Append": "รวมไฟล์ PDF",
    "Split PDF": "แยกไฟล์ PDF",
    "Remove / Extract": "ลบหรือดึงหน้า",
    "PDF to JPG / PNG": "PDF เป็น JPG / PNG",
    "Edit PDF": "แก้ไข PDF",
    "Organize PDF": "จัดระเบียบ PDF",
    "Reorder, rotate and insert pages": "จัดลำดับ หมุน และแทรกหน้า",
    "Drag to reorder pages, rotate selections, or insert a blank page.": "ลากเพื่อจัดลำดับหน้า หมุนหน้าที่เลือก หรือแทรกหน้าว่าง",
    "Rotate left": "หมุนซ้าย",
    "Rotate right": "หมุนขวา",
    "Blank page": "หน้าว่าง",
    "Reverse order": "กลับลำดับหน้า",
    "Browse files…": "เลือกไฟล์…",
    "Add PDFs…": "เพิ่มไฟล์ PDF…",
    "Add a page range…": "เพิ่มช่วงหน้า…",
    "Drop PDF, JPG or PNG files here": "วางไฟล์ PDF, JPG หรือ PNG ที่นี่",
    "Drop a PDF here": "วางไฟล์ PDF หนึ่งไฟล์ที่นี่",
    "Drop one or more PDFs here": "วางไฟล์ PDF หนึ่งไฟล์ขึ้นไปที่นี่",
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
    "Split after": "แยกหลังหน้านี้",
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
    "No public update release was found.": "ไม่พบอัปเดตที่เผยแพร่สาธารณะ",
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

BUTTON_HELP = {
    "Home": ("Open the PDF tools dashboard.", "เปิดหน้ารวมเครื่องมือ PDF"),
    "Settings": ("Open app preferences and update settings.", "เปิดค่ากำหนดและการตั้งค่าการอัปเดต"),
    "About": ("View the app version, guide, and licenses.", "ดูเวอร์ชัน คู่มือ และสัญญาอนุญาต"),
    "Theme": ("Choose the app appearance.", "เลือกรูปแบบสีของแอป"),
    "System": ("Match the Windows appearance.", "ใช้รูปแบบสีตาม Windows"),
    "Light": ("Use the light theme.", "ใช้ธีมสว่าง"),
    "Dark": ("Use the dark theme.", "ใช้ธีมมืด"),
    "Merge / Append": ("Combine PDFs and arrange their pages.", "รวมไฟล์ PDF และจัดลำดับหน้า"),
    "Split PDF": ("Divide one PDF into separate files.", "แยก PDF หนึ่งไฟล์ออกเป็นหลายไฟล์"),
    "Remove / Extract": ("Remove, keep, or export selected pages.", "ลบ เก็บ หรือส่งออกหน้าที่เลือก"),
    "PDF to JPG / PNG": (
        "Convert PDF pages to JPG or PNG images.",
        "แปลงหน้า PDF เป็นรูปภาพ JPG หรือ PNG",
    ),
    "Edit PDF": ("Add text, pictures, or shapes to a PDF.", "เพิ่มข้อความ รูปภาพ หรือรูปร่างใน PDF"),
    "Organize PDF": ("Arrange, rotate, and insert PDF pages.", "จัดลำดับ หมุน และแทรกหน้า PDF"),
    "Rotate left": (
        "Rotate selected pages 90° counterclockwise.",
        "หมุนหน้าที่เลือกทวนเข็มนาฬิกา 90 องศา",
    ),
    "Rotate right": ("Rotate selected pages 90° clockwise.", "หมุนหน้าที่เลือกตามเข็มนาฬิกา 90 องศา"),
    "Blank page": ("Insert a blank A4 page after the current page.", "แทรกหน้าว่าง A4 หลังหน้าปัจจุบัน"),
    "Reverse order": ("Reverse the order of all pages.", "กลับลำดับหน้าทั้งหมด"),
    "Browse files…": ("Choose files from your computer.", "เลือกไฟล์จากคอมพิวเตอร์"),
    "Add PDFs…": ("Add PDFs to this workspace.", "เพิ่มไฟล์ PDF ในเครื่องมือนี้"),
    "Add a page range…": ("Insert selected pages from another PDF.", "แทรกหน้าที่เลือกจาก PDF อีกไฟล์"),
    "Export…": ("Choose where to save the result.", "เลือกตำแหน่งบันทึกผลลัพธ์"),
    "Export as ZIP": ("Pack the output files into one ZIP archive.", "รวมไฟล์ผลลัพธ์ไว้ในไฟล์ ZIP เดียว"),
    "Transparent PNG": ("Keep transparent areas in PNG output.", "คงพื้นที่โปร่งใสในไฟล์ PNG"),
    "Move up": ("Move the selected pages earlier in the document.", "เลื่อนหน้าที่เลือกให้มาก่อน"),
    "Move down": ("Move the selected pages later in the document.", "เลื่อนหน้าที่เลือกไปด้านหลัง"),
    "Duplicate": ("Make a copy of the selection.", "ทำสำเนาสิ่งที่เลือก"),
    "Remove": ("Remove selected pages from this workspace.", "นำหน้าที่เลือกออกจากเครื่องมือนี้"),
    "Invert": ("Select the pages that are currently unselected.", "สลับให้เลือกหน้าที่ยังไม่ได้เลือก"),
    "Undo": ("Reverse the last change.", "ย้อนการเปลี่ยนแปลงล่าสุด"),
    "Redo": ("Restore the last change you undid.", "ทำการเปลี่ยนแปลงที่เพิ่งย้อนกลับอีกครั้ง"),
    "Split here": ("Start a new output file after the current page.", "เริ่มไฟล์ผลลัพธ์ใหม่หลังหน้าปัจจุบัน"),
    "Use range": ("Select pages using the entered page range.", "เลือกหน้าตามช่วงที่ระบุ"),
    "Previous": ("Show the previous page.", "แสดงหน้าก่อนหน้า"),
    "Next": ("Show the next page.", "แสดงหน้าถัดไป"),
    "−": ("Zoom out on the page preview.", "ย่อมุมมองหน้า"),
    "+": ("Zoom in on the page preview.", "ขยายมุมมองหน้า"),
    "Fit page": ("Show the whole page in the preview.", "แสดงทั้งหน้าในพื้นที่แสดงตัวอย่าง"),
    "Fit width": (
        "Fit the page to the width of the preview.",
        "ปรับหน้าให้พอดีกับความกว้างของพื้นที่แสดงตัวอย่าง",
    ),
    "Pan": ("Toggle dragging to move around the preview.", "เปิดหรือปิดการลากเพื่อเลื่อนมุมมอง"),
    "Insert image": ("Choose an image to place on the current page.", "เลือกรูปภาพเพื่อวางบนหน้าปัจจุบัน"),
    "Delete": ("Delete the selected objects.", "ลบวัตถุที่เลือก"),
    "Save": ("Save the edited PDF.", "บันทึก PDF ที่แก้ไขแล้ว"),
    "Save as…": ("Choose a filename for the edited PDF.", "ตั้งชื่อไฟล์ PDF ที่แก้ไขแล้ว"),
    "Bold": ("Toggle bold for the selected text.", "เปิดหรือปิดตัวหนาสำหรับข้อความที่เลือก"),
    "Italic": ("Toggle italics for the selected text.", "เปิดหรือปิดตัวเอียงสำหรับข้อความที่เลือก"),
    "Underline": ("Underline the selected text.", "ขีดเส้นใต้ข้อความที่เลือก"),
    "Lock aspect ratio": (
        "Keep the object's proportions when resizing.",
        "คงสัดส่วนของวัตถุเมื่อปรับขนาด",
    ),
    "Text / border color": ("Choose a text or outline color.", "เลือกสีข้อความหรือเส้นขอบ"),
    "Fill color": ("Choose a color for the inside of the shape.", "เลือกสีภายในรูปร่าง"),
    "Choose folder…": ("Set the default folder for exports.", "ตั้งค่าโฟลเดอร์เริ่มต้นสำหรับส่งออก"),
    "Clear preview cache": ("Clear cached page thumbnails.", "ล้างภาพขนาดย่อของหน้าที่เก็บไว้"),
    "Reset preferences": ("Restore the default app preferences.", "คืนค่ากำหนดเริ่มต้นของแอป"),
    "Check GitHub for updates in the background": (
        "Let the app check for updates automatically.",
        "ให้แอปตรวจสอบอัปเดตโดยอัตโนมัติ",
    ),
    "Check for updates": (
        "Look for a newer signed release on GitHub.",
        "ค้นหารุ่นใหม่ที่ลงลายเซ็นบน GitHub",
    ),
    "Manage GitHub credential…": (
        "Save or remove the token for private updates.",
        "บันทึกหรือลบโทเค็นสำหรับอัปเดตแบบส่วนตัว",
    ),
    "Update available": ("View details for the available update.", "ดูรายละเอียดการอัปเดตที่พร้อมใช้งาน"),
    "Ready to install": ("Install the verified update.", "ติดตั้งอัปเดตที่ตรวจสอบแล้ว"),
    "Update now": (
        "Download, verify, install, and reopen PDF Toolbox.",
        "ดาวน์โหลด ตรวจสอบ ติดตั้ง และเปิด PDF Toolbox อีกครั้ง",
    ),
    "Remind me later": (
        "Dismiss until the next startup check.",
        "ปิดจนกว่าจะตรวจสอบเมื่อเปิดแอปครั้งถัดไป",
    ),
    "Later": ("Dismiss this update for now.", "ปิดการแจ้งอัปเดตนี้ไว้ก่อน"),
    "Skip this version": ("Skip update reminders for this version.", "ข้ามการแจ้งเตือนอัปเดตสำหรับรุ่นนี้"),
    "Open folder": ("Show the exported files in File Explorer.", "แสดงไฟล์ที่ส่งออกใน File Explorer"),
    "Open file": ("Open the exported file.", "เปิดไฟล์ที่ส่งออก"),
    "Licenses": ("Read the bundled software licenses.", "อ่านสัญญาอนุญาตของซอฟต์แวร์ที่รวมมาด้วย"),
    "User guide": ("Open the PDF Toolbox user guide.", "เปิดคู่มือการใช้ PDF Toolbox"),
    "Cancel": ("Stop this action.", "หยุดการดำเนินการนี้"),
    "OK": ("Confirm and continue.", "ยืนยันและดำเนินการต่อ"),
    "Close": ("Close this dialog.", "ปิดหน้าต่างนี้"),
    "Discard": ("Continue without saving the pending changes.", "ดำเนินการต่อโดยไม่บันทึกการเปลี่ยนแปลง"),
    "Yes": ("Confirm this action.", "ยืนยันการดำเนินการนี้"),
    "No": ("Decline this action.", "ปฏิเสธการดำเนินการนี้"),
    "Copy": ("Copy the selected objects to the clipboard.", "คัดลอกวัตถุที่เลือกไปยังคลิปบอร์ด"),
    "Cut": ("Move selected objects to the clipboard.", "ย้ายวัตถุที่เลือกไปยังคลิปบอร์ด"),
    "Bring forward": ("Raise the selected objects one layer.", "เลื่อนวัตถุที่เลือกขึ้นหนึ่งชั้น"),
    "Send backward": ("Lower the selected objects one layer.", "เลื่อนวัตถุที่เลือกลงหนึ่งชั้น"),
    "Bring to front": ("Place the selection above all other objects.", "นำสิ่งที่เลือกไว้หน้าวัตถุอื่นทั้งหมด"),
    "Send to back": ("Place the selection behind all other objects.", "นำสิ่งที่เลือกไว้หลังวัตถุอื่นทั้งหมด"),
}
BUTTON_LABELS = {THAI.get(label, label): label for label in BUTTON_HELP}


def describe_button(button, context, label=None):
    if isinstance(button, QAbstractButton):
        button.setCursor(Qt.CursorShape.PointingHandCursor)
    label = label or button.text() or button.accessibleName()
    help_text = BUTTON_HELP.get(label) or BUTTON_HELP.get(BUTTON_LABELS.get(label, ""))
    if help_text:
        button.setToolTip(help_text[1 if thai_enabled(context) else 0])


def describe_buttons(panel, context):
    for button in panel.findChildren(QAbstractButton):
        describe_button(button, context)


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
        refresh(
            widget, widget.accessibleName, widget.setAccessibleName, "translation_accessibility"
        )
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
    describe_buttons(box, box.parentWidget())


def ask_text(parent, title, label, echo=QLineEdit.EchoMode.Normal):
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(tr(parent, title))
    dialog.setLabelText(tr(parent, label))
    dialog.setTextEchoMode(echo)
    dialog.setOkButtonText(tr(parent, "OK"))
    dialog.setCancelButtonText(tr(parent, "Cancel"))
    describe_buttons(dialog, parent)
    accepted = dialog.exec() == dialog.DialogCode.Accepted
    return dialog.textValue() if accepted else "", accepted

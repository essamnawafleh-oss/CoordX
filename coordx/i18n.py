"""Arabic / English interface strings."""
from __future__ import annotations

_lang = "ar"

S = {
    "app_name": ("كورد اكس", "CoordX"),
    "app_tagline": ("تحويل جداول الإحداثيات من الصور وملفات PDF والإكسل\nإلى نقاط على الأوتوكاد (DXF)",
                    "Turn coordinate tables from images, PDFs and Excel\ninto AutoCAD points (DXF)"),
    "dev_label": ("تطوير", "Developed by"),
    "dev_name": ("عصام النوافلة - Essam Nawafleh", "Essam Nawafleh - عصام النوافلة"),
    "free_line": ("🤲  هذا البرنامج مجاني لوجه الله تعالى", "🤲  This program is free, for the sake of Allah"),
    "dua_line": ("إذا سهّل عليك شغلك، لا تنسَ المطوّر من دعوة بظهر الغيب بالتوفيق والسداد",
                 "If it made your work easier, please remember the developer in your prayers"),
    "dua_text": ("«اللهم وفّقه ويسّر أمره وارزقه من حيث لا يحتسب»",
                 "«O Allah, grant him success, ease his affairs and provide for him from where he does not expect»"),
    "app_title": ("كورد اكس  ·  CoordX", "CoordX  ·  كورد اكس"),
    "start": ("ابدأ  ←", "Start  →"),
    "version": ("الإصدار", "Version"),

    "open": ("فتح ملفات", "Open files"),
    "open_tip": ("صور، PDF، إكسل أو CSV. ممكن تختار أكثر من ملف", "Images, PDF, Excel or CSV. You can pick several files"),
    "new_parcel": ("قطعة جديدة", "New parcel"),
    "remove_parcel": ("حذف القطعة", "Remove parcel"),
    "export_dxf": ("تصدير DXF", "Export DXF"),
    "export_excel": ("تصدير Excel", "Export Excel"),
    "export_csv": ("تصدير CSV (Civil 3D)", "Export CSV (Civil 3D)"),
    "language": ("English", "عربي"),
    "about": ("حول البرنامج", "About"),
    "file_filter": ("كل الملفات المدعومة", "All supported files"),

    "parcels": ("القطع", "Parcels"),
    "drop_hint": ("اسحب الصور أو ملفات PDF أو الإكسل لهون\nأو اكبس «فتح ملفات»",
                  "Drag images, PDFs or Excel files here\nor press “Open files”"),
    "name": ("اسم القطعة", "Parcel name"),
    "stated_area": ("المساحة بالمخطط (م²)", "Area on plan (m²)"),
    "stated_area_ph": ("اختياري، للمقارنة", "optional, for checking"),
    "col_no": ("رقم", "No."),
    "col_x": ("X (شرقي)", "X (East)"),
    "col_y": ("Y (شمالي)", "Y (North)"),
    "col_z": ("Z (منسوب)", "Z (Elev.)"),
    "add_row": ("إضافة نقطة", "Add point"),
    "insert_row": ("إدراج فوق", "Insert above"),
    "del_row": ("حذف", "Delete"),
    "up": ("▲", "▲"),
    "down": ("▼", "▼"),
    "swap_xy": ("تبديل X ↔ Y", "Swap X ↔ Y"),
    "renumber": ("إعادة الترقيم", "Renumber"),
    "checks": ("التحقق", "Checks"),
    "side": ("الضلع", "Side"),
    "length": ("الطول المحسوب", "Computed length"),
    "on_plan": ("بالمخطط", "On plan"),
    "status": ("الحالة", "Status"),
    "area": ("المساحة", "Area"),
    "perimeter": ("المحيط", "Perimeter"),
    "points_n": ("عدد النقاط", "Points"),
    "method_ocr": ("قراءة الصورة (OCR)", "Image reading (OCR)"),
    "method_pdf-text": ("نص PDF مباشر", "PDF text"),
    "method_excel": ("ملف إكسل/CSV", "Excel/CSV file"),
    "method_manual": ("إدخال يدوي", "Manual entry"),
    "source": ("المصدر", "Source"),
    "fit": ("ملاءمة", "Fit"),
    "no_image": ("لا توجد صورة لهذا المصدر", "No image for this source"),

    "st_ok": ("✓ مطابق", "✓ matches"),
    "st_warn": ("⚠ مشكوك", "⚠ suspicious"),
    "st_none": ("—", "—"),
    "area_ok": ("✓ مطابقة للمخطط", "✓ matches the plan"),
    "area_warn": ("⚠ فرق {d:+.2f} م² ({p:+.1f}%) عن المخطط. إذا في ضلع منحني (قوس) هذا طبيعي",
                  "⚠ differs by {d:+.2f} m² ({p:+.1f}%) from the plan. Normal if a side is curved (arc)"),
    "summary_ok": ("✓ كل الفحوصات سليمة", "✓ All checks passed"),
    "summary_issues": ("⚠ في {n} ملاحظة، راجع الخلايا الملونة", "⚠ {n} issue(s), review the coloured cells"),
    "sides_matched": ("{m} من {n} أضلاع مطابقة لأطوال المخطط", "{m} of {n} sides match lengths on the plan"),

    "flag_missing": ("القيمة ناقصة", "Value missing"),
    "flag_low_conf": ("القراءة غير أكيدة ({c}%)، تأكد منها", "Uncertain reading ({c}%), please verify"),
    "flag_split": ("انفصل رقم النقطة عن الإحداثي تلقائياً، تأكد", "Point number was split off the coordinate, please verify"),
    "flag_digits": ("عدد الخانات مختلف عن باقي النقاط", "Different number of digits than the other points"),
    "flag_far": ("النقطة بعيدة جداً عن باقي النقاط", "Point is very far from the others"),
    "flag_duplicate": ("نقطة مكررة (نفس السابقة)", "Duplicate of the previous point"),
    "msg_self_cross": ("الضلع {a} بيقطع الضلع {b}، يمكن ترتيب النقاط غلط", "Side {a} crosses side {b}, the point order may be wrong"),

    "reading": ("جاري القراءة…", "Reading…"),
    "reading_file": ("جاري قراءة {f}", "Reading {f}"),
    "loaded": ("تمت قراءة {n} قطعة", "{n} parcel(s) read"),
    "nothing_found": ("ما لقيت جدول إحداثيات في: {f}\nجرّب صورة أوضح، أو جهّز إكسل من الصورة وافتحه هون.",
                      "No coordinate table found in: {f}\nTry a clearer image, or make an Excel file from it and open that."),
    "read_error": ("صار خطأ بقراءة {f}:\n{e}", "Error reading {f}:\n{e}"),
    "no_parcels": ("ما في قطع للتصدير", "No parcels to export"),
    "saved": ("تم الحفظ: {f}", "Saved: {f}"),
    "save_error": ("ما قدرت أحفظ الملف:\n{e}", "Could not save the file:\n{e}"),
    "open_folder": ("فتح المجلد", "Open folder"),
    "confirm_remove": ("حذف القطعة «{n}»؟", "Remove parcel “{n}”?"),
    "export_issues": ("في {n} ملاحظة ما انحلت. بدك تكمل التصدير؟", "There are {n} unresolved issue(s). Export anyway?"),

    "dxf_title": ("خيارات DXF", "DXF options"),
    "dxf_points": ("النقاط (POINT)", "Points (POINT)"),
    "dxf_numbers": ("أرقام النقاط", "Point numbers"),
    "dxf_boundary": ("حدود القطعة (Polyline)", "Parcel boundary (Polyline)"),
    "dxf_lengths": ("أطوال الأضلاع", "Side lengths"),
    "dxf_table": ("جدول الإحداثيات", "Coordinate table"),
    "dxf_area": ("اسم القطعة والمساحة", "Parcel name and area"),
    "dxf_height": ("ارتفاع النص", "Text height"),
    "dxf_auto": ("تلقائي", "Automatic"),
    "dxf_which": ("القطع", "Parcels"),
    "dxf_current": ("القطعة الحالية بس", "Current parcel only"),
    "dxf_all_one": ("كل القطع بملف واحد", "All parcels in one file"),
    "dxf_all_sep": ("كل قطعة بملف لحالها", "Each parcel in its own file"),
    "choose_folder": ("اختر مجلد الحفظ", "Choose output folder"),
    "ok": ("موافق", "OK"),
    "cancel": ("إلغاء", "Cancel"),
    "close": ("إغلاق", "Close"),
}


def set_lang(lang: str):
    global _lang
    _lang = "en" if lang == "en" else "ar"


def lang() -> str:
    return _lang


def tr(key: str, **kw) -> str:
    pair = S.get(key)
    if pair is None:
        return key
    text = pair[0] if _lang == "ar" else pair[1]
    return text.format(**kw) if kw else text

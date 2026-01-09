from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepInFrame, KeepTogether, PageBreak, Flowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from datetime import date
import re
import os
import json

# --- Шрифты ---
pdfmetrics.registerFont(TTFont("Roboto", "fonts/Roboto-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Roboto-Bold", "fonts/Roboto-Bold.ttf"))
BASE_FONT = "Roboto"
BOLD_FONT = "Roboto-Bold"

# --- Стили ---
styles = getSampleStyleSheet()
BASE_FONT_SIZE = 11
HEADING_FONT_SIZE = 14
TITLE_FONT_SIZE = 24

for key in ["Normal", "Title", "Heading2", "Heading3"]:
    styles[key].fontName = BASE_FONT

styles["Normal"].fontSize = BASE_FONT_SIZE
styles["Normal"].leading = BASE_FONT_SIZE + 2

styles["Title"].fontName = BOLD_FONT
styles["Title"].fontSize = TITLE_FONT_SIZE
styles["Title"].leading = TITLE_FONT_SIZE + 2
styles["Title"].spaceAfter = 8

styles["Heading2"].fontName = BOLD_FONT
styles["Heading2"].fontSize = HEADING_FONT_SIZE
styles["Heading2"].leading = HEADING_FONT_SIZE + 2
styles["Heading2"].spaceAfter = 6

styles["Heading3"].fontName = BOLD_FONT
styles["Heading3"].fontSize = HEADING_FONT_SIZE
styles["Heading3"].leading = HEADING_FONT_SIZE + 1
styles["Heading3"].spaceAfter = 4

FIRM_COLOR = colors.HexColor("#2196F3")
HEADER_GRADIENT_START = colors.HexColor("#d9effb")
HEADER_GRADIENT_END = colors.HexColor("#90cff4")

# --- Project Styles ---
project_card_title_style = ParagraphStyle(
    "ProjectCardTitle",
    parent=styles["Heading3"],
    fontName=BOLD_FONT,
    fontSize=16,
    leading=20,
    textColor=colors.HexColor("#222e3a"),
    spaceAfter=4,
)
project_card_role_style = ParagraphStyle(
    "ProjectCardRole",
    parent=styles["Normal"],
    fontSize=11,
    textColor=colors.HexColor("#888888"),
    leftIndent=2,
)
project_card_desc_style = ParagraphStyle(
    "ProjectCardDesc",
    parent=styles["Normal"],
    fontSize=11,
    textColor=colors.HexColor("#6c7a89"),
    spaceAfter=4,
)
project_card_stack_style = ParagraphStyle(
    "ProjectCardStack",
    parent=styles["Normal"],
    fontSize=10,
    textColor=FIRM_COLOR,
    italic=True,
    spaceAfter=2,
)

# ============================================================
#  HEADER / FOOTER
# ============================================================
def resolve_logo_path():
    """Находит логотип в папке data_input"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "data_input", "logo.jpg")  # или logo.jpg
    if os.path.exists(logo_path):
        return logo_path
    else:
        return None


def add_inpro_header_footer(canvas, doc):
    """Фирменный хедер + футер Inpro Analytics с логотипом"""
    width, height = A4
    canvas.saveState()

    # Logo
    logo_path = resolve_logo_path()
    page_width, page_height = A4
    logo_height = 58  # фиксированная высота логотипа (можно регулировать)

    if logo_path:
        try:
            canvas.drawImage(
                logo_path,
                0, page_height - logo_height,     # X=0, чтобы начать с самого левого края
                width=page_width, height=logo_height,  # растягиваем на всю ширину страницы
                preserveAspectRatio=False,        # ⚠️ отключаем сохранение пропорций
                mask="auto"
            )
        except Exception as e:
            print(f"⚠️ Ошибка при вставке логотипа: {e}")


 
    # Footer
    footer_lines = ["Austria, Graz", "recruiting@inpro-analytics.at", "www.inpro-analytics.at"]
    canvas.setFont("Roboto", 8)
    canvas.setFillColor(colors.HexColor("#A9A8A8"))
    y = 20
    for line in footer_lines:
        canvas.drawString(25, y, line)
        y += 10

    canvas.restoreState()


# --- Утилиты ---
def sanitize_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip()) or "Unknown"

def p(text, style):
    return Paragraph(text.replace("\n", "<br/>"), style)

def format_category_name(key: str) -> str:
    return {
        "cloud_platforms": "Cloud Platforms",
        "devops_iac": "DevOps & IaC",
        "monitoring_security": "Monitoring & Security",
        "programming_languages": "Programming Languages",
        "containers_orchestration": "Containers & Orchestration",
        "ci_cd_tools": "CI/CD Tools",
        "databases": "Databases",
        "backend": "Backend",
        "frontend": "Frontend",
        "security": "Security",
        "ai_ml_tools": "AI & ML Tools",
        "infrastructure_os": "Infrastructure & OS",
        "other_tools": "Other Tools"
    }.get(key, key.replace("_", " ").title())

# --- Блоки ---
def make_left_box(data, styles):
    items = []
    header_style = ParagraphStyle("LeftHeader", parent=styles["Heading3"], fontName=BOLD_FONT, spaceAfter=6)

    edu = data.get("education", "")
    if edu:
        items += [p("<b>Education:</b>", header_style), p(edu, styles["Normal"]), Spacer(0, 6)]

    langs = data.get("languages", [])
    if langs:
        items.append(p("<b>Languages:</b>", header_style))
        for lang in langs:
            lang_name = lang.get("language", "")
            lvl = lang.get("level", "")
            if lang_name and lvl:
                items.append(Paragraph(f"{lang_name} &mdash; {lvl}", styles["Normal"]))
            elif lang_name:
                items.append(p(f"• {lang_name}", styles["Normal"]))
        items.append(Spacer(0, 6))

    dom = data.get("domains", [])
    if dom:
        items.append(p("<b>Domains:</b>", header_style))
        items.append(p("<br/>".join(dom), styles["Normal"]))

    return KeepInFrame(0, 0, items, mode="shrink")

def make_right_box(data, styles):
    text = data.get("profile_summary", "") or ""
    body = [p(text, ParagraphStyle("Summary", parent=styles["Normal"], leading=16))]
    return KeepInFrame(0, 0, body, mode="shrink")

def make_overview_box(data, styles):
    """
    Формирует блок 'OVERVIEW – Hard Skills' с ограничением по длине.
    Каждая категория занимает максимум две строки (~5–6 инструментов).
    """
    hard_skills = data.get("hard_skills", {})
    if not hard_skills:
        return None

    # Заголовок
    title_style = ParagraphStyle(
        "OverviewTitle",
        parent=styles["Heading2"],
        fontName=BOLD_FONT,
        fontSize=18,
        leading=22,
        textColor=FIRM_COLOR,
        spaceBefore=6,
        spaceAfter=6,
    )

    rows = [[Paragraph("OVERVIEW – Hard Skills", title_style), ""]]
    rows.append(["", ""])

    # порядок вывода
    desired_order = [
        "programming_languages", "backend", "frontend", "databases",
        "cloud_platforms", "devops_iac", "ci_cd_tools",
        "containers_orchestration", "monitoring_security",
        "infrastructure_os", "security",
        "data_engineering", "etl_tools",
        "bi_tools", "analytics", "ai_ml_tools",
        "other_tools"
    ]
    # ✅ Покажем и те категории, которых нет в desired_order, но пришли в JSON
    rest = [k for k in hard_skills.keys() if k not in desired_order]
    order = desired_order + rest

    for key in order:
        tools = hard_skills.get(key, [])
        if not tools:
            continue

        # нормализация списка
        tool_names = []
        for t in tools:
            if isinstance(t, dict):
                name = (t.get("name") or "").strip()
                if name:
                    tool_names.append(name)
            elif isinstance(t, str):
                s = t.strip()
                if s:
                    tool_names.append(s)

        if not tool_names:
            continue

    # ограничитель по количеству элементов в строке
    MAX_ITEMS = 12

    for key in desired_order:
        tools = hard_skills.get(key, [])
        if not tools:
            continue

        # нормализуем список
        tool_names = []
        for t in tools:
            if isinstance(t, dict):
                name = t.get("name", "").strip()
                if name:
                    tool_names.append(name)
            elif isinstance(t, str):
                tool_names.append(t.strip())

        if not tool_names:
            continue

        # сортировка и уникальность
        tool_names = sorted(set(tool_names))

        # ограничиваем количество
        if len(tool_names) > MAX_ITEMS:
            tool_names = tool_names[:MAX_ITEMS]

        tools_str = ", ".join(tool_names)

        # визуальное сокращение, чтобы строка не занимала более двух линий
        if len(tools_str) > 120:
            tools_str = tools_str[:117].rsplit(",", 1)[0]

        left = Paragraph(f"<b>{format_category_name(key)}:</b>",
                         ParagraphStyle("Left", parent=styles["Normal"],
                                        fontName=BOLD_FONT, fontSize=11))
        right = Paragraph(tools_str,
                          ParagraphStyle("Right", parent=styles["Normal"],
                                         fontSize=11, leading=13,
                                         wordWrap='CJK',  # аккуратный перенос
                                         textColor=colors.HexColor("#222e3a")))
        rows.append([left, right])

    table = Table(rows, colWidths=[55*mm, 120*mm], hAlign="LEFT")
    style = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (0, 0), (-1, 0), BOLD_FONT),
        ("FONTSIZE", (0, 0), (-1, 0), 14),
        ("SPAN", (0, 0), (-1, 0)),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
    ])

    for i in range(2, len(rows)):
        bg = colors.whitesmoke if i % 2 == 0 else colors.white
        style.add("BACKGROUND", (0, i), (-1, i), bg)

    table.setStyle(style)
    return table


def make_first_page_section(data, styles):
    """
    Первая страница — имя, должность, контакты, Education, Languages, Domains и Summary.
    """
    elements = []

    full_name = data.get("full_name", "")
    position = data.get("title", "")
    location = data.get("location", "")
    email = data.get("email", "")
    phone = data.get("phone", "")

    # --- Левая колонка (Education, Languages, Domains) ---
    left_box = make_left_box(data, styles)

    # --- Правая колонка (Profile Summary) ---
    right_box = make_right_box(data, styles)

    # --- Таблица с двумя колонками ---
    left_w = 70 * mm
    right_w = 90 * mm
    table = Table([[left_box, right_box]], colWidths=[left_w, right_w], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # --- Заголовок (имя и должность) ---
    header = f'<b>{full_name}</b>'
    if position:
        header += f'<br/><font size="20" color="#888888">{position}</font>'
    header_p = Paragraph(header, ParagraphStyle(
        "CardTitleBig",
        parent=styles["Title"],
        fontName=BOLD_FONT,
        fontSize=28,
        leading=32,
        spaceAfter=10,
        textColor=FIRM_COLOR,
    ))

    # --- Контактная информация ---
    contact_lines = []
    if location:
        contact_lines.append(f'<font color="#888888">{location}</font>')
    if email:
        contact_lines.append(f'<font color="#888888">{email}</font>')
    if phone:
        contact_lines.append(f'<font color="#888888">{phone}</font>')

    if contact_lines:
        contact_p = Paragraph("<br/>".join(contact_lines), ParagraphStyle(
            "ContactInfoBig",
            parent=styles["Normal"],
            fontSize=13,
            leading=18,
            spaceAfter=12,
            textColor=colors.HexColor("#888888"),
        ))
        elements.append(contact_p)

    # --- Добавляем всё в блок ---
    elements.append(header_p)
    elements.append(Spacer(1, 10))
    elements.append(table)
    elements.append(Spacer(1, 20))

    return elements


# --- Проекты ---
class RoundedCard(Flowable):
    def __init__(self, content, width, padding=20, radius=6,
                 strokeColor=colors.HexColor("#2196F3"),
                 strokeWidth=1.2, shadow=True):
        super().__init__()
        self.content = content
        self.width = width
        self.padding = padding
        self.radius = radius
        self.strokeColor = strokeColor
        self.strokeWidth = strokeWidth
        self.shadow = shadow
        self._inner = None
        self._height = None

    def wrap(self, availW, availH):
        innerW = min(self.width, availW) - 2 * self.padding
        kif = KeepInFrame(innerW, 10_000, self.content, mode="shrink")
        w, h = kif.wrapOn(self.canv, innerW, availH)
        self._inner = kif
        self._height = h + 2 * self.padding
        return min(self.width, availW), self._height

    def draw(self):
        c = self.canv
        w, h = self.width, self._height
        if self.shadow:
            c.setFillColor(colors.HexColor("#cce8ff"))
            c.roundRect(4, -4, w, h, self.radius, stroke=0, fill=1)
        c.setStrokeColor(self.strokeColor)
        c.setLineWidth(self.strokeWidth)
        c.setFillColor(colors.white)
        c.roundRect(0, 0, w, h, self.radius, stroke=1, fill=1)
        self._inner.drawOn(c, self.padding, self.padding)

def make_projects_section(projects, styles):
    if not projects:
        return []

    elements = []
    FIRM_COLOR = colors.HexColor("#2196F3")

    # --- Заголовок секции ---
    section_title = Paragraph(
        '<font color="#2196F3"><b>PROJECTS & EXPERIENCE</b></font>',
        ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontSize=18,
            leading=22,
            spaceAfter=10,
            textColor=FIRM_COLOR,
        )
    )

    cards_on_page = 0
    first_card_done = False

    for idx, project in enumerate(projects, 1):
        title = project.get("project_title", "")
        role = project.get("role", "")
        overview = project.get("overview", "")
        duration = project.get("duration", "")
        tech_stack = project.get("tech_stack", [])
        responsibilities = project.get("responsibilities", [])

        pdfmetrics.registerFont(TTFont("Roboto-Italic", "fonts/Roboto-Italic.ttf"))

        # --- Заголовок карточки ---
        header = f"<b>Project {idx}. {title}</b>"
        if role:
            header += f'<br/><font size="11" color="#888888">{role}</font>'
        if duration:
            header += f'<br/><font name="Roboto-Italic" size="10" color="#2196F3">{duration}</font>'
        header_p = Paragraph(header, project_card_title_style)

        # --- Описание проекта ---
        desc_p = Paragraph(overview, project_card_desc_style) if overview else None

        # --- Responsibilities ---
        resp_items = []
        if responsibilities:
            resp_items.append(Paragraph(
                "Responsibilities:",
                ParagraphStyle(
                    "CardRespTitle",
                    parent=styles["Normal"],
                    fontSize=10,
                    leading=12,
                    spaceAfter=6,
                    textColor=FIRM_COLOR,
                ),
            ))
            for r in responsibilities:
                resp_items.append(
                    Paragraph(
                        f"• {r}",
                        ParagraphStyle(
                            "CardRespItem",
                            parent=styles["Normal"],
                            fontSize=10,
                            leading=12,
                            leftIndent=20,
                            firstLineIndent=-10,
                            textColor=colors.HexColor("#222e3a"),
                        ),
                    )
                )

        # --- Tech stack (выровнено строго под остальным текстом) ---
        stack_p = None
        if tech_stack:
            stack = " · ".join(tech_stack)
            stack_p = Paragraph(
                f'<b><font color="#2196F3">Tech stack:</font></b> {stack}',
                ParagraphStyle(
                    "CardStackFixed",
                    parent=styles["Normal"],
                    fontSize=10,
                    leading=13,
                    leftIndent=55,
                    firstLineIndent=-55,
                    spaceBefore=4,
                    spaceAfter=8,
                    textColor=FIRM_COLOR,
                ),
            )

        # --- Сборка содержимого карточки ---
        card_content = [header_p]
        if desc_p:
            card_content.append(desc_p)
        if resp_items:
            card_content.extend(resp_items)
        if stack_p:
            card_content.append(stack_p)

        # --- Создание округлённой карточки ---
        card = RoundedCard(
            content=card_content,
            width=170 * mm,
            padding=20,
            radius=6,
            strokeColor=FIRM_COLOR,
            strokeWidth=1.2,
            shadow=True,
        )

        # --- Добавление карточек в поток ---
        if not first_card_done:
            elements.append(KeepTogether([section_title, Spacer(1, 10), card, Spacer(1, 20)]))
            first_card_done = True
            cards_on_page = 1
        else:
            elements.append(KeepTogether([card, Spacer(1, 20)]))
            cards_on_page += 1

        # --- Две карточки на страницу ---
        if cards_on_page == 2:
            elements.append(PageBreak())
            cards_on_page = 0

    return elements


def make_skills_overview_box(data, styles):
    skills_overview = data.get("skills_overview", [])
    if not skills_overview:
        return None

    title = Paragraph(
        '<font color="#2196F3"><b>SKILLS OVERVIEW</b></font>',
        ParagraphStyle(
            "SkillsOverviewTitle",
            parent=styles["Heading2"],
            fontSize=18,
            leading=22,
            spaceAfter=12,
            textColor=colors.HexColor("#2196F3"),
        )
    )

    grouped = {}
    for item in skills_overview:
        cat = (item.get("category") or "").strip()
        tools_list = item.get("tools", [])  # ✅ правильный ключ
        yoe_raw = (str(item.get("years_of_experience", "")).strip())  # для вывода как есть

        # берём максимальное число из строки (поддержит "4.8", "4–5", "5+")
        nums = re.findall(r"\d+(?:\.\d+)?", yoe_raw)
        yoe_num = float(nums[-1]) if nums else 0.0

        if not cat:
            continue
        if cat not in grouped:
            grouped[cat] = {"tools": [], "max_years_num": 0.0, "yoe_display": "-"}

        # тулсы
        if isinstance(tools_list, list):
            grouped[cat]["tools"].extend([str(t).strip() for t in tools_list if str(t).strip()])
        elif isinstance(tools_list, str) and tools_list.strip():
            grouped[cat]["tools"].append(tools_list.strip())

        # обновляем максимум и строку для отображения
        if yoe_num >= grouped[cat]["max_years_num"]:
            grouped[cat]["max_years_num"] = yoe_num
            grouped[cat]["yoe_display"] = (yoe_raw or "-")

    # --- стили
    header_left = ParagraphStyle("HeaderLeft", parent=styles["Normal"],
                                 fontName=BOLD_FONT, fontSize=11,
                                 alignment=TA_LEFT, textColor=colors.HexColor("#222e3a"))
    header_center = ParagraphStyle("HeaderCenter", parent=styles["Normal"],
                                   fontName=BOLD_FONT, fontSize=11,
                                   alignment=TA_CENTER, textColor=colors.HexColor("#222e3a"))
    cell_left = ParagraphStyle("CellLeft", parent=styles["Normal"],
                               fontSize=11, alignment=TA_LEFT,
                               textColor=colors.HexColor("#222e3a"))
    cell_center = ParagraphStyle("CellCenter", parent=styles["Normal"],
                                 fontSize=11, alignment=TA_CENTER,
                                 textColor=colors.HexColor("#222e3a"))
    cell_tools = ParagraphStyle("CellTools", parent=styles["Normal"],
                                fontSize=11, leading=13, alignment=TA_LEFT,
                                wordWrap='CJK', textColor=colors.HexColor("#222e3a"))

    # --- таблица ---
    rows = [[
        Paragraph("Category", header_left),
        Paragraph("Tools", header_left),
        Paragraph("YoE", header_center),
    ]]

    for cat, values in grouped.items():
        # 1) Tools → строка
        tools_list = values.get("tools", [])
        tools_str = ", ".join(sorted(set([str(t).strip() for t in tools_list if str(t).strip()]))) or "-"

        # 2) YoE → берём исходную строку, извлекаем число и округляем, оставляем только цифру
        yoe_raw = str(values.get("yoe_display", "")).strip()
        nums = re.findall(r"\d+(?:\.\d+)?", yoe_raw)
        if nums:
            yoe_num = round(float(nums[-1]))   # last number (поддержит "4–5", "4.8", "5+")
            yoe_str = str(int(yoe_num))
        else:
            yoe_str = "0"

        rows.append([
            Paragraph(format_category_name(cat), cell_left),
            Paragraph(tools_str, cell_tools),   # обязательно стиль с wordWrap='CJK'
            Paragraph(yoe_str, cell_center),
        ])




    table = Table(rows, colWidths=[55 * mm, 95 * mm, 25 * mm], hAlign="LEFT")

    style = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
    ])

    # Чередование строк (серо-белые)
    for i in range(1, len(rows)):
        style.add("BACKGROUND", (0, i), (-1, i),
                  colors.whitesmoke if i % 2 == 1 else colors.white)
        
    # 🔹 Принудительно включаем перенос текста во втором столбце (Tools)
    style.add("WORDWRAP", (1, 1), (1, -1), None)

    # 🔹 Немного увеличим высоту строк
    style.add("LEADING", (1, 1), (1, -1), 13)
        
    table.setStyle(style)

    return [title, Spacer(1, 8), table, Spacer(1, 12)]


# --- Главная сборка ---
def create_pretty_first_section(json_data, output_dir=".", prefix="CV"):
    full_name = json_data.get("full_name", "Unknown")
    safe = sanitize_filename(full_name)
    fname = f"{prefix}_{safe}_{date.today().isoformat()}.pdf"
    out_path = os.path.join(output_dir, fname)

    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=25*mm, bottomMargin=18*mm)

    elements = []
    elements += make_first_page_section(json_data, styles)
    overview_box = make_overview_box(json_data, styles)
    if overview_box:
        elements.append(overview_box)
    projects_section = make_projects_section(json_data.get("projects_experience", []), styles)
    elements += projects_section
    skills_overview_box = make_skills_overview_box(json_data, styles)
    if skills_overview_box:
        elements.extend([Spacer(1, 6), *skills_overview_box])


    
    # Построение PDF с фирменным хедером и футером
    doc.build(elements, onFirstPage=add_inpro_header_footer, onLaterPages=add_inpro_header_footer)

    return out_path

# ============================================================
#  Обёртка для Streamlit — возвращает PDF как байты
# ============================================================
import io, os, glob

def generate_report_pdf_bytes(filled_json):
    """
    Генерирует PDF через create_pretty_first_section()
    и возвращает байты для скачивания в Streamlit.
    """
    output_dir = "data_output"
    os.makedirs(output_dir, exist_ok=True)

    # создаём PDF
    create_pretty_first_section(filled_json, output_dir=output_dir, prefix="CV_Streamlit")

    # ищем последний созданный файл
    pdf_files = sorted(
        glob.glob(os.path.join(output_dir, "CV_Streamlit*.pdf")),
        key=os.path.getmtime,
        reverse=True
    )
    if not pdf_files:
        raise FileNotFoundError("Не найден созданный PDF-файл после генерации.")

    latest_pdf = pdf_files[0]
    with open(latest_pdf, "rb") as f:
        pdf_bytes = f.read()

    return pdf_bytes

# --- Запуск ---
if __name__ == "__main__":
    with open("data_output/result_Manuel.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    pdf_path = create_pretty_first_section(data)
    print(f"✅ PDF создан: {pdf_path}")
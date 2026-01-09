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
from typing import Dict
import re
import os
import json
import ast

# --- Fonts ---
pdfmetrics.registerFont(TTFont("Roboto", "fonts/Roboto-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Roboto-Bold", "fonts/Roboto-Bold.ttf"))
BASE_FONT = "Roboto"
BOLD_FONT = "Roboto-Bold"

# --- Styles ---
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
    """Finds a logo in the data_input folder."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "data_input", "logo.jpg")  # or logo.jpg
    if os.path.exists(logo_path):
        return logo_path
    else:
        return None


def add_inpro_header_footer(canvas, doc):
    """Branded header + footer for Inpro Analytics, including the logo."""
    width, height = A4
    canvas.saveState()

    # Logo
    logo_path = resolve_logo_path()
    page_width, page_height = A4
    logo_height = 58  # fixed logo height (can be adjusted)

    if logo_path:
        try:
            canvas.drawImage(
                logo_path,
                0, page_height - logo_height,     # X=0 to start from the very left edge
                width=page_width, height=logo_height,  # stretch to full page width
                preserveAspectRatio=False,        # ⚠️ disable aspect ratio preservation
                mask="auto"
            )
        except Exception as e:
            print(f"⚠️ Error inserting logo: {e}")


 
    # Footer
    footer_lines = ["Austria, Graz", "recruiting@inpro-analytics.at", "www.inpro-analytics.at"]
    canvas.setFont("Roboto", 8)
    canvas.setFillColor(colors.HexColor("#A9A8A8"))
    y = 20
    for line in footer_lines:
        canvas.drawString(25, y, line)
        y += 10

    canvas.restoreState()


# --- Utilities ---
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

# --- Sections ---
def make_left_box(data, styles):
    items = []
    header_style = ParagraphStyle("LeftHeader", parent=styles["Heading3"], fontName=BOLD_FONT, spaceAfter=6)

    edu = data.get("education", "")
    # Support both formats: new (degree/institution/year) and legacy (Institution/Abschluss/Jahr)
    if isinstance(edu, list):
        def edu_row_to_str(row):
            if not isinstance(row, dict):
                return ""
            if any(k in row for k in ("degree", "institution", "year")):
                return " | ".join(str(v) for v in [row.get("degree"), row.get("institution"), row.get("year")] if v)
            return " | ".join(str(v) for v in [row.get("Institution"), row.get("Abschluss"), row.get("Jahr")] if v)
        edu = "<br/>".join([
            edu_row_to_str(row) for row in edu if isinstance(row, dict) and any(row.values())
        ])
    if edu:
        items += [p("<b>Education:</b>", header_style), p(edu, styles["Normal"]), Spacer(0, 6)]

    langs = data.get("languages", [])
    # Do not render the block if there are no non-empty languages
    if langs and isinstance(langs, list):
        nonempty_langs = [lang for lang in langs if (lang.get("language") or lang.get("Sprache"))]
        if nonempty_langs:
            items.append(p("<b>Languages:</b>", header_style))
            for lang in nonempty_langs:
                lang_name = lang.get("language") or lang.get("Sprache", "")
                lvl = lang.get("level") or lang.get("Niveau", "")
                if lang_name and lvl:
                    items.append(Paragraph(f"{lang_name} &mdash; {lvl}", styles["Normal"]))
                elif lang_name:
                    items.append(p(f"• {lang_name}", styles["Normal"]))
            items.append(Spacer(0, 6))

    dom = data.get("domains", [])
    if dom:
        items.append(p("<b>Domains:</b>", header_style))
        items.append(p("<br/>".join(dom), styles["Normal"]))
        items.append(Spacer(0, 6))

    companies = data.get("companies", [])
    if companies:
        items.append(p("<b>Companies:</b>", header_style))
        items.append(p("<br/>".join(companies), styles["Normal"]))
        items.append(Spacer(0, 6))

    return KeepInFrame(0, 0, items, mode="shrink")

def make_right_box(data, styles):
    text = data.get("profile_summary", "") or ""
    body = [p(text, ParagraphStyle("Summary", parent=styles["Normal"], leading=16))]
    return KeepInFrame(0, 0, body, mode="shrink")

def make_overview_box(data, styles):
    """
    Builds the 'OVERVIEW – Hard Skills' block with a length constraint.
    Each category takes at most two lines (~5–6 tools).
    """
    hard_skills = data.get("hard_skills", {})
    if not hard_skills:
        return None

    # Title
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

    # Display order
    desired_order = [
        "programming_languages", "backend", "frontend", "databases",
        "cloud_platforms", "devops_iac", "ci_cd_tools",
        "containers_orchestration", "monitoring_security",
        "infrastructure_os", "security",
        "data_engineering", "etl_tools",
        "bi_tools", "analytics", "ai_ml_tools",
        "other_tools" 
    ]
    # ✅ Also show categories not in desired_order but present in JSON
    rest = [k for k in hard_skills.keys() if k not in desired_order]
    order = desired_order + rest

    for key in order:
        tools = hard_skills.get(key, [])
        if not tools:
            continue

        # Normalize list
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

    # Max number of items per line
    MAX_ITEMS = 12

    for key in desired_order:
        tools = hard_skills.get(key, [])
        if not tools:
            continue

        # Normalize list
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

        # Sort + unique
        tool_names = sorted(set(tool_names))

        # Limit count
        if len(tool_names) > MAX_ITEMS:
            tool_names = tool_names[:MAX_ITEMS]

        tools_str = ", ".join(tool_names)

        # Trim to keep the row within ~2 lines
        if len(tools_str) > 120:
            tools_str = tools_str[:117].rsplit(",", 1)[0]

        left = Paragraph(f"<b>{format_category_name(key)}:</b>",
                         ParagraphStyle("Left", parent=styles["Normal"],
                                        fontName=BOLD_FONT, fontSize=11))
        right = Paragraph(tools_str,
                          ParagraphStyle("Right", parent=styles["Normal"],
                                         fontSize=11, leading=13,
                                         wordWrap='CJK',  # nicer line wrapping
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
    First page: name, title, contacts, Education, Languages, Domains, and Summary.
    """
    elements = []

    full_name = data.get("full_name", "")
    position = data.get("title", "")
    location = data.get("location", "")
    email = data.get("email", "")
    phone = data.get("phone", "")

    # --- Left column (Education, Languages, Domains) ---
    left_box = make_left_box(data, styles)

    # --- Right column (Profile Summary) ---
    right_box = make_right_box(data, styles)

    # --- Two-column table ---
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

    # --- Header (name and title) ---
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

    # --- Contact info ---
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

    # --- Assemble block ---
    elements.append(header_p)
    elements.append(Spacer(1, 10))
    elements.append(table)
    elements.append(Spacer(1, 20))

    return elements



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
        self._height = 0
        self._outerW = width  # actual width used in draw()

    def wrap(self, availW, availH):
        # Small epsilon to ensure we never exceed the frame width
        EPS = 1.0
        border = self.strokeWidth * 2

        # ⬅️ KEY: the card must NOT be wider than the frame (otherwise LayoutError)
        self._outerW = max(1, availW - border - EPS)

        innerW = self._outerW - 2 * self.padding
        innerW = max(1, innerW)

        innerH = max(1, availH - 2 * self.padding)

        kif = KeepInFrame(innerW, innerH, self.content, mode="shrink")
        w, h = kif.wrapOn(self.canv, innerW, innerH)

        # KeepInFrame may return 0 height for empty content, which breaks layout
        h = max(1, h)

        self._inner = kif
        self._height = max(1, h + 2 * self.padding + border)

        # ⬅️ Return the actual width we will draw
        return self._outerW + border, self._height

    def draw(self):
        c = self.canv

        # Draw exactly what we computed in wrap()
        w = self._outerW
        h = self._height

        if self.shadow:
            c.setFillColor(colors.HexColor("#cce8ff"))
            c.roundRect(4, -4, w, h, self.radius, stroke=0, fill=1)

        c.setStrokeColor(self.strokeColor)
        c.setLineWidth(self.strokeWidth)
        c.setFillColor(colors.white)
        c.roundRect(0, 0, w, h, self.radius, stroke=1, fill=1)

        if self._inner:
            self._inner.drawOn(c, self.padding, self.padding)

def make_projects_section(projects, styles):
    if not projects:
        return []

    elements = []
    FIRM_COLOR = colors.HexColor("#2196F3")

    # --- Section title ---
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
        # Normalize (editors often return None)
        title = (project.get("project_title") or "").strip()
        role = (project.get("role") or "").strip()
        overview = (project.get("overview") or "").strip()
        duration = (project.get("duration") or "").strip()
        tech_stack = project.get("tech_stack") or []
        responsibilities = project.get("responsibilities") or []

        # Skip empty projects (otherwise the card may become degenerate)
        has_any = bool(title or role or overview or duration)
        if not has_any:
            if isinstance(tech_stack, list) and any(str(x).strip() for x in tech_stack):
                has_any = True
            if isinstance(responsibilities, list) and any(str(x).strip() for x in responsibilities):
                has_any = True
        if not has_any:
            continue

        pdfmetrics.registerFont(TTFont("Roboto-Italic", "fonts/Roboto-Italic.ttf"))

        # --- Card header ---
        header = f"<b>Project {idx}. {title}</b>"
        if role:
            header += f'<br/><font size="11" color="#888888">{role}</font>'
        if duration:
            header += f'<br/><font name="Roboto-Italic" size="10" color="#2196F3">{duration}</font>'
        header_p = Paragraph(header, project_card_title_style)

        # --- Project description ---
        desc_p = Paragraph(overview, project_card_desc_style) if overview else None

        # --- Responsibilities ---
        resp_items = []

        # Normalize responsibilities into list[str]
        if isinstance(responsibilities, list):
            responsibilities = [str(r).strip() for r in responsibilities if str(r).strip()]
        elif isinstance(responsibilities, str) and responsibilities.strip():
            s = responsibilities.strip()
            # Handle stringified list, e.g. "['a', 'b']" or "[\"a\", \"b\"]"
            if s.startswith("[") and s.endswith("]"):
                parsed = None
                try:
                    parsed = ast.literal_eval(s)
                except Exception:
                    try:
                        parsed = json.loads(s)
                    except Exception:
                        parsed = None
                if isinstance(parsed, list):
                    responsibilities = [str(r).strip() for r in parsed if str(r).strip()]
                else:
                    responsibilities = [s]
            else:
                # Split multiline/bulleted text into separate items
                lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
                if len(lines) > 1:
                    responsibilities = [ln.lstrip("•*-·–— ").strip() for ln in lines if ln.strip()]
                else:
                    responsibilities = [s]
        else:
            responsibilities = []

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

        # --- Tech stack (aligned with the rest of the text) ---
        stack_p = None
        if isinstance(tech_stack, list):
            tech_stack = [str(t).strip() for t in tech_stack if str(t).strip()]
        elif isinstance(tech_stack, str) and tech_stack.strip():
            tech_stack = [tech_stack.strip()]
        else:
            tech_stack = []

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

        # --- Assemble card content ---
        card_content = [header_p]
        if desc_p:
            card_content.append(desc_p)
        if resp_items:
            card_content.extend(resp_items)
        if stack_p:
            card_content.append(stack_p)

        # --- Create rounded card ---
        card = RoundedCard(
            content=card_content,
            width=None,
            padding=20,
            radius=6,
            strokeColor=FIRM_COLOR,
            strokeWidth=1.2,
            shadow=True,
        )

        # --- Add cards to the flow ---
        if not first_card_done:
            elements.append(KeepTogether([section_title, Spacer(1, 10), card, Spacer(1, 20)]))
            first_card_done = True
            cards_on_page = 1
        else:
            elements.append(KeepTogether([card, Spacer(1, 20)]))
            cards_on_page += 1

        # --- Two cards per page ---
        if cards_on_page == 2:
            elements.append(PageBreak())
            cards_on_page = 0

    return elements


def make_skills_overview_box(data, styles):
    skills_overview = data.get("skills_overview", [])
    if not skills_overview:
        return None

    # Normalize and drop only truly empty rows (no category or no tools).
    normalized = []
    for item in skills_overview:
        if not isinstance(item, dict):
            continue
        # Support both formats:
        # - English: category/tools/years_of_experience
        # - Legacy German: Kategorie/Werkzeuge/Jahre Erfahrung
        cat = (item.get("category") or item.get("Kategorie") or "").strip()

        tools_list = item.get("tools")
        if tools_list is None:
            tools_list = item.get("Werkzeuge", [])

        yoe_value = item.get("years_of_experience")
        if yoe_value is None:
            yoe_value = item.get("Jahre Erfahrung")

        if isinstance(tools_list, str):
            tools_list = [t.strip() for t in re.split(r"[,/;]", tools_list) if t.strip()]
        elif isinstance(tools_list, list):
            tools_list = [str(t).strip() for t in tools_list if str(t).strip()]
        else:
            tools_list = []
        if not cat or not tools_list:
            continue
        normalized.append({
            "category": cat,
            "tools": tools_list,
            "years_of_experience": yoe_value if yoe_value is not None else "",
        })
    skills_overview = normalized
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
        tools_list = item.get("tools", [])  # ✅ correct key
        yoe_raw = (str(item.get("years_of_experience", "")))  # keep for display as-is

        # take the max number from the string (supports "4.8", "4–5", "5+")
        nums = re.findall(r"\d+(?:\.\d+)?", yoe_raw)
        yoe_num = float(nums[-1]) if nums else 0.0

        if not cat:
            continue
        if cat not in grouped:
            grouped[cat] = {"tools": [], "max_years_num": 0.0, "yoe_display": "-"}

        # tools
        if isinstance(tools_list, list):
            grouped[cat]["tools"].extend([str(t).strip() for t in tools_list if str(t).strip()])
        elif isinstance(tools_list, str) and tools_list.strip():
            grouped[cat]["tools"].append(tools_list.strip())

        # update max + display string
        if yoe_num >= grouped[cat]["max_years_num"]:
            grouped[cat]["max_years_num"] = yoe_num
            grouped[cat]["yoe_display"] = (yoe_raw or "-")

    # --- Styles
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

    # --- Table ---
    rows = [[
        Paragraph("Category", header_left),
        Paragraph("Tools", header_left),
        Paragraph("YoE", header_center),
    ]]

    for cat, values in grouped.items():
        # 1) Tools → string
        tools_list = values.get("tools", [])
        tools_str = ", ".join(sorted(set([str(t).strip() for t in tools_list if str(t).strip()]))) or "-"

        # 2) YoE → use original string, extract number, round, keep digits only
        yoe_raw = str(values.get("yoe_display", "")).strip()
        nums = re.findall(r"\d+(?:\.\d+)?", yoe_raw)
        if nums:
            yoe_num = round(float(nums[-1]))   # last number (supports "4–5", "4.8", "5+")
            yoe_str = str(int(yoe_num))
        else:
            yoe_str = "0"

        rows.append([
            Paragraph(format_category_name(cat), cell_left),
            Paragraph(tools_str, cell_tools),   # requires wordWrap='CJK'
            Paragraph(yoe_str, cell_center),
        ])




    table = Table(rows, colWidths=[55 * mm, 95 * mm, 25 * mm], hAlign="LEFT")

    style = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
    ])

    # Alternating row colors (grey/white)
    for i in range(1, len(rows)):
        style.add("BACKGROUND", (0, i), (-1, i),
                  colors.whitesmoke if i % 2 == 1 else colors.white)
        
    # 🔹 Force word wrapping in the second column (Tools)
    style.add("WORDWRAP", (1, 1), (1, -1), None)

    # 🔹 Slightly increase row height
    style.add("LEADING", (1, 1), (1, -1), 13)
        
    table.setStyle(style)

    return [title, Spacer(1, 8), table, Spacer(1, 12)]


# --- Main PDF build ---
def create_pretty_first_section(json_data, output_dir=".", prefix="CV Inpro"):
    """Creates a PDF named 'CV Inpro <FirstName> <Position>.pdf' in a Windows-safe way."""
    full_name = json_data.get("full_name", "Unknown").strip()
    title = json_data.get("title", "").strip()

    # Combine name and title into one string and sanitize immediately
    raw_filename = f"{prefix} {full_name} {title}".strip()
    safe_filename = sanitize_filename(raw_filename)

    # Add extension
    fname = f"{safe_filename}.pdf"
    out_path = os.path.join(output_dir, fname)

    # Create PDF
    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=25 * mm,
        bottomMargin=18 * mm,
    )

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

    # Build PDF with branded header and footer
    doc.build(elements, onFirstPage=add_inpro_header_footer, onLaterPages=add_inpro_header_footer)

    return out_path

# Streamlit-dependent comparison utilities were moved to similarity_view.py to decouple this module.


# --- Run ---
if __name__ == "__main__":
    with open("debug/filled_cv_from_gpt.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    pdf_path = create_pretty_first_section(data)
    print(f"✅ PDF created: {pdf_path}")
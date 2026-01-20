# PDF Layout Notes - Buyside Memo Engine v0.1.0

## Overview

This document specifies how to render the Buyside Memo Engine manual to PDF for print-friendly distribution.

---

## Page Setup

| Setting | Value |
|---------|-------|
| Page size | US Letter (8.5" × 11") |
| Margins | 1" all sides |
| Orientation | Portrait |
| Color mode | Color (for tables/emphasis) |

---

## Typography

### Headings
| Level | Font | Size | Weight | Spacing |
|-------|------|------|--------|---------|
| H1 | Sans-serif | 18pt | Bold | 24pt before, 12pt after |
| H2 | Sans-serif | 14pt | Bold | 18pt before, 8pt after |
| H3 | Sans-serif | 12pt | Bold | 12pt before, 6pt after |
| H4 | Sans-serif | 11pt | Bold | 8pt before, 4pt after |

### Body Text
| Element | Font | Size | Line Height |
|---------|------|------|-------------|
| Paragraphs | Serif | 11pt | 1.4 |
| Lists | Serif | 11pt | 1.3 |
| Tables | Sans-serif | 10pt | 1.2 |
| Code | Monospace | 10pt | 1.2 |
| Captions | Sans-serif | 9pt | 1.2 |

### Font Recommendations
- Headings: Helvetica, Arial, or Open Sans
- Body: Georgia, Times New Roman, or Crimson Text
- Code: Courier, Consolas, or Source Code Pro

---

## Page Elements

### Header
- Content: "Buyside Memo Engine v0.1.0"
- Position: Top right
- Size: 9pt
- Style: Italic

### Footer
- Content: Page number
- Position: Center bottom
- Size: 10pt
- Format: "Page X of Y"

### Page Breaks

Insert page break **before**:
- Section A (Run Metadata)
- Section B (Diff vs Latest)
- Section C (10 Findings)
- Section D (Deliverables)
- Section E (Latent Quality Module)
- Section F (Pitfalls & Compliance)
- Supporting Files list

---

## Tables

### Styling
- Header row: Bold, light gray background (#f0f0f0)
- Borders: 0.5pt gray lines
- Cell padding: 4pt
- Alternate row shading: Optional (#fafafa)

### Width
- Full page width for main tables
- Auto-fit columns to content
- Wrap text in narrow columns

---

## Code Blocks

### Styling
- Background: Light gray (#f5f5f5)
- Border: 0.5pt gray, rounded corners (2pt)
- Padding: 8pt
- Overflow: Wrap or reduce font size

### JSON/Python Blocks
- Syntax highlighting if available
- Line numbers for blocks >10 lines

---

## Lists

### Bulleted Lists
- Marker: Circle or disc
- Indent: 0.25" per level
- Max depth: 3 levels

### Numbered Lists
- Format: 1. 2. 3. (not 1) 2) 3))
- Indent: 0.25" per level

### Checklists
- Use ☐ for unchecked
- Use ☑ for checked
- Or use [ ] and [x] if Unicode not supported

---

## Special Elements

### Callout Boxes
For important warnings or tips:
- Background: Light yellow (#fffde7) for warnings, light blue (#e3f2fd) for tips
- Border: 2pt left border in darker shade
- Padding: 8pt

### Score Anchors Table
The rubric score anchor tables should use:
- Fixed column widths
- Consistent row heights
- Clear separation between score levels

---

## Document Structure

### Table of Contents
Generate TOC with:
- H1 and H2 entries
- Page numbers
- Dot leaders
- Hyperlinks in digital PDF

### Cross-References
When referencing other sections:
- Use "See Section X" format
- Include page number in print version
- Use hyperlinks in digital version

---

## Export Settings

### PDF Export from Markdown
Recommended tools:
- Pandoc with LaTeX backend
- VS Code with Markdown PDF extension
- Typora export

### Pandoc Command
```bash
pandoc buyside_memo_engine_v0.1.0.md \
  -o buyside_memo_engine_v0.1.0.pdf \
  --pdf-engine=xelatex \
  --toc \
  --toc-depth=2 \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V mainfont="Georgia" \
  -V sansfont="Helvetica" \
  -V monofont="Courier"
```

### Print Considerations
- Ensure adequate contrast for B&W printing
- Test that tables fit page width
- Verify code blocks don't overflow

---

## Quality Checklist

Before distributing PDF:
- [ ] TOC generated and accurate
- [ ] Page numbers continuous
- [ ] No orphan headings (heading at bottom of page without content)
- [ ] Tables fit within margins
- [ ] Code blocks readable (not truncated)
- [ ] Links functional (in digital version)
- [ ] Header/footer on all pages
- [ ] Section breaks correct

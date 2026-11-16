"""
Boarding pass + e-ticket generator for the airline demo.
Usage (in cmd):   python make_boarding_pass.py <laptop-ip> <flight>
Example:          python make_boarding_pass.py 192.168.43.7 AI101
Reads  C:\\n8n-files\\flights.json and C:\\n8n-files\\passengers.csv
Writes PDFs to C:\\n8n-files\\output
"""
import os, sys, csv, json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

if len(sys.argv) < 2:
    sys.exit("Usage: python make_boarding_pass.py <laptop-ip> [flight, default AI101]")
host = sys.argv[1].replace("http://", "").replace("https://", "").rstrip("/")
if ":" not in host:
    host += ":5678"
FLIGHT = (sys.argv[2] if len(sys.argv) > 2 else "AI101").upper()
FOLDER = os.environ.get("N8N_FILES", r"C:\n8n-files")
OUT = os.path.join(FOLDER, "output")
os.makedirs(OUT, exist_ok=True)

flights = {f["flight_no"]: f for f in json.load(open(os.path.join(FOLDER, "flights.json"), encoding="utf-8"))}
if FLIGHT not in flights:
    sys.exit(f"Flight {FLIGHT} not found in flights.json")
with open(os.path.join(FOLDER, "passengers.csv"), newline="", encoding="utf-8") as fh:
    pax = [p for p in csv.DictReader(fh) if p["flight_no"] == FLIGHT]
pax.sort(key=lambda p: int(p["boarding_seq"]))
fl = flights[FLIGHT]
URL = f"http://{host}/webhook/flight-status?flight={FLIGHT}"
NAVY = colors.HexColor("#0b1f3a"); BLUE = colors.HexColor("#12305a"); GREY = colors.HexColor("#6b7a90")
DATE_STR = datetime.strptime(fl["date"], "%Y-%m-%d").strftime("%d %b %Y").upper()


def draw_qr(c, data, x, y, size):
    w = qr.QrCodeWidget(data); b = w.getBounds()
    d = Drawing(size, size, transform=[size / (b[2] - b[0]), 0, 0, size / (b[3] - b[1]), 0, 0])
    d.add(w); renderPDF.draw(d, c, x, y)


def field(c, label, value, x, y, size=11, align="left"):
    c.setFillColor(GREY); c.setFont("Helvetica", 6.5)
    (c.drawString if align == "left" else c.drawRightString)(x, y + size + 2, label)
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", size)
    (c.drawString if align == "left" else c.drawRightString)(x, y, str(value))


# ---- boarding passes ----
W, H = 210 * mm, 90 * mm
bp_path = os.path.join(OUT, f"boarding_passes_{FLIGHT}.pdf")
c = canvas.Canvas(bp_path, pagesize=(W, H))
STUB = 62 * mm; MAIN = W - STUB
for p in pax:
    c.setFillColor(NAVY); c.rect(0, H - 16 * mm, W, 16 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 15)
    c.drawString(10 * mm, H - 10.5 * mm, fl["airline"].upper())
    c.setFont("Helvetica-Bold", 11); c.drawRightString(MAIN - 8 * mm, H - 10 * mm, "BOARDING PASS")
    c.setFont("Helvetica", 8); c.drawRightString(W - 6 * mm, H - 10 * mm, "LIVE STATUS QR")
    name = f"{p['last_name']}/{p['first_name']} {p['title']}".upper()
    field(c, "PASSENGER NAME", name, 10 * mm, H - 28 * mm, 13)
    field(c, "FLIGHT", FLIGHT, MAIN - 8 * mm, H - 28 * mm, 13, "right")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 30)
    c.drawString(10 * mm, H - 46 * mm, fl["from_iata"]); c.drawString(62 * mm, H - 46 * mm, fl["to_iata"])
    c.setStrokeColor(GREY); c.setLineWidth(1.2)
    c.line(38 * mm, H - 42 * mm, 56 * mm, H - 42 * mm)
    c.line(52 * mm, H - 39.5 * mm, 56 * mm, H - 42 * mm); c.line(52 * mm, H - 44.5 * mm, 56 * mm, H - 42 * mm)
    c.setFillColor(GREY); c.setFont("Helvetica", 8)
    c.drawString(10 * mm, H - 51 * mm, fl["from_city"].upper()); c.drawString(62 * mm, H - 51 * mm, fl["to_city"].upper())
    field(c, "DATE", DATE_STR, MAIN - 8 * mm, H - 46 * mm, 11, "right")
    y = H - 64 * mm
    cols = [("GATE", fl["gate"]), ("BOARDING", fl["boarding_time"]), ("DEPARTS", fl["departure_time"]),
            ("SEAT", p["seat"]), ("CLASS", p["cabin"].upper()), ("GROUP", p["boarding_group"]), ("TERMINAL", fl["terminal"])]
    for (lab, val), x in zip(cols, [10, 29, 51, 72, 90, 119, 131]):
        field(c, lab, val, x * mm, y, 12)
    c.setFillColor(GREY); c.setFont("Helvetica", 7)
    c.drawString(10 * mm, 11 * mm, f"PNR {p['pnr']}   |   TICKET {p['ticket_no']}   |   SEQ {int(p['boarding_seq']):03d}   |   BAGGAGE {p['baggage_kg']} KG")
    c.setFillColor(colors.HexColor("#c0392b")); c.setFont("Helvetica-Bold", 7)
    c.drawString(10 * mm, 6 * mm, "DEMO / SPECIMEN - SYNTHETIC DATA - NOT VALID FOR TRAVEL")
    c.setStrokeColor(colors.HexColor("#9aa7b8")); c.setDash(3, 3); c.setLineWidth(0.8)
    c.line(MAIN, 4 * mm, MAIN, H - 16 * mm); c.setDash()
    qs = 40 * mm
    draw_qr(c, URL, MAIN + (STUB - qs) / 2, H - 16 * mm - 6 * mm - qs, qs)
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(MAIN + STUB / 2, 22 * mm, "SCAN FOR LIVE FLIGHT INFO")
    c.setFillColor(GREY); c.setFont("Helvetica", 6.5)
    c.drawCentredString(MAIN + STUB / 2, 18 * mm, "Status | Crew | Pre-flight checks | Weather")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(MAIN + STUB / 2, 11 * mm, f"{FLIGHT}   SEAT {p['seat']}   GATE {fl['gate']}")
    c.setFillColor(GREY); c.setFont("Helvetica", 6.5)
    c.drawCentredString(MAIN + STUB / 2, 6.5 * mm, f"{p['last_name'].upper()}/{p['first_name'].upper()}")
    c.showPage()
c.save()

# ---- e-ticket (largest booking) ----
groups = {}
for p in pax:
    groups.setdefault(p["pnr"], []).append(p)
pnr, members = max(groups.items(), key=lambda kv: len(kv[1]))
ss = getSampleStyleSheet()
small = ParagraphStyle("small", parent=ss["Normal"], fontName="Helvetica", fontSize=8, textColor=GREY, leading=11)
norm = ParagraphStyle("norm", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12)
h2 = ParagraphStyle("h2", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=11, textColor=NAVY, spaceBefore=10, spaceAfter=4)
et_path = os.path.join(OUT, f"e_ticket_{FLIGHT}_{pnr}.pdf")
doc = SimpleDocTemplate(et_path, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
story = []
head = Table([[Paragraph(f"<font color='white' size=16><b>{fl['airline'].upper()}</b></font>", norm),
               Paragraph("<font color='white' size=11><b>ELECTRONIC TICKET - ITINERARY / RECEIPT</b></font>", norm)]],
             colWidths=[70 * mm, 108 * mm])
head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                          ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
story += [head, Spacer(1, 8)]
meta = Table([[Paragraph("<b>Booking reference (PNR)</b>", small), Paragraph("<b>Issue date</b>", small), Paragraph("<b>Passengers</b>", small)],
              [Paragraph(f"<font size=14><b>{pnr}</b></font>", norm), Paragraph("05 NOV 2026", norm), Paragraph(str(len(members)), norm)]],
             colWidths=[70 * mm, 54 * mm, 54 * mm])
meta.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#c9d3e0")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3fa"))]))
story += [meta, Paragraph("Itinerary", h2)]
it = Table([[Paragraph("<b>Flight</b>", small), Paragraph("<b>From</b>", small), Paragraph("<b>To</b>", small), Paragraph("<b>Aircraft</b>", small)],
            [Paragraph(f"<b>{FLIGHT}</b><br/>{DATE_STR}", norm),
             Paragraph(f"<b>{fl['from_city']} ({fl['from_iata']})</b><br/>Dep {fl['departure_time']} | Terminal {fl['terminal']}", norm),
             Paragraph(f"<b>{fl['to_city']} ({fl['to_iata']})</b><br/>Arr {fl['arrival_time']}", norm),
             Paragraph(f"{fl['aircraft']}<br/>Gate {fl['gate']} | Boarding {fl['boarding_time']}", norm)]],
            colWidths=[34 * mm, 52 * mm, 44 * mm, 48 * mm])
it.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#c9d3e0")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3fa")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
story += [it, Paragraph("Passengers", h2)]
rows = [["Passenger", "Ticket number", "Seat", "Cabin", "Baggage", "Meal"]]
for p in members:
    rows.append([f"{p['title']} {p['first_name']} {p['last_name']}", p["ticket_no"], p["seat"], p["cabin"], f"{p['baggage_kg']} kg", p["meal"]])
pt = Table(rows, colWidths=[45 * mm, 38 * mm, 15 * mm, 22 * mm, 20 * mm, 38 * mm])
pt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3e0")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f9fd")]),
                        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
story += [pt, Paragraph("Fare details (INR)", h2)]
total = sum(int(p["fare_inr"]) for p in members); base = int(total * 0.74); taxes = total - base
fare = Table([["Base fare", f"INR {base:,}"], ["Taxes, fees and charges", f"INR {taxes:,}"], ["Total paid", f"INR {total:,}"]], colWidths=[120 * mm, 58 * mm])
fare.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                          ("LINEABOVE", (0, 2), (-1, 2), 0.8, NAVY), ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#c9d3e0"))]))
story += [fare, Paragraph("Live flight information", h2),
          Paragraph(f"Scan the QR code printed on your boarding pass to see live flight status, your crew, pre-flight checks and the weather at {fl['from_city']}. Link encoded: {URL}", norm), Spacer(1, 6)]
qd = Drawing(90, 90); w = qr.QrCodeWidget(URL); b = w.getBounds()
qd.transform = [90 / (b[2] - b[0]), 0, 0, 90 / (b[3] - b[1]), 0, 0]; qd.add(w)
story += [qd, Paragraph("Important information", h2),
          Paragraph("Check-in closes 60 minutes before departure for domestic flights. Carry a valid photo ID. Boarding gates close 20 minutes before departure. Cabin baggage limit: 7 kg.", norm), Spacer(1, 10),
          Paragraph("<font color='#c0392b'><b>DEMO / SPECIMEN - ALL NAMES AND DATA ARE SYNTHETIC. NOT VALID FOR TRAVEL.</b></font>", norm)]
doc.build(story)
print("Done.")
print("QR link :", URL)
print("Saved   :", bp_path)
print("Saved   :", et_path)

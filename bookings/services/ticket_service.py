import io
import os
import qrcode
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_qr_image(data_text):
    """Generate in-memory QR code image BytesIO"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e1b4b", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def generate_ticket_pdf(booking, ticket=None):
    """
    Generate professional PDF ticket using ReportLab.
    If ticket is None, use the first ticket of the booking or booking overview.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom typography styles
    primary_color = colors.HexColor("#4f46e5")   # Indigo
    dark_color = colors.HexColor("#0f172a")      # Dark Slate
    accent_color = colors.HexColor("#7c3aed")    # Purple
    gray_color = colors.HexColor("#64748b")
    bg_light = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
    )

    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=gray_color,
    )

    event_title_style = ParagraphStyle(
        'EventTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=dark_color,
    )

    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=primary_color,
    )

    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=dark_color,
    )

    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#16a34a"),
    )

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>🎟️ EventHub</b>", title_style),
            Paragraph("<b>CONFIRMED ADMISSION TICKET</b><br/><font color='#16a34a'><b>STATUS: PAID / VALID</b></font>", ParagraphStyle('HRight', parent=styles['Normal'], alignment=2, fontSize=11, leading=15, textColor=primary_color))
        ]
    ]
    t_header = Table(header_data, colWidths=[3.5*inch, 4.0*inch])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceBefore=4, spaceAfter=15))

    # Determine ticket data
    tkt = ticket if ticket else booking.tickets.first()
    qr_token = tkt.qr_token if tkt else f"BK-{booking.booking_id}"
    ticket_code = tkt.ticket_code if tkt else f"TKT-{booking.booking_id}-ALL"
    attendee = tkt.attendee_name if tkt else (booking.user.full_name or booking.user.username)
    ticket_type_name = tkt.ticket_type.name if tkt else "Standard Admission"

    # 2. Main Ticket Body (Event details on left, QR Code on right)
    qr_buf = generate_qr_image(f"EVENTHUB:TICKET:{qr_token}")
    qr_img = Image(qr_buf, width=2.0*inch, height=2.0*inch)

    left_content = [
        [Paragraph("EVENT NAME", meta_label_style)],
        [Paragraph(f"<b>{booking.event.title}</b>", event_title_style)],
        [Spacer(1, 6)],
        [Paragraph(f"📅 <b>Date:</b> {booking.event.event_date.strftime('%A, %B %d, %Y')} &nbsp;&nbsp;|&nbsp;&nbsp; ⏰ <b>Time:</b> {booking.event.start_time.strftime('%I:%M %p')}", meta_val_style)],
        [Paragraph(f"📍 <b>Venue:</b> {booking.event.venue}, {booking.event.city}", meta_val_style)],
        [Paragraph(f"🏢 <b>Organizer:</b> {booking.event.organizer}", meta_val_style)],
    ]
    t_left = Table(left_content, colWidths=[5.0*inch])
    t_left.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    right_content = [
        [qr_img],
        [Paragraph(f"<b>Token:</b> {qr_token[:13]}...", ParagraphStyle('QrCaption', parent=styles['Normal'], alignment=1, fontSize=8, textColor=gray_color))],
        [Paragraph("<font color='#16a34a'><b>● SCAN AT GATE</b></font>", ParagraphStyle('QrValid', parent=styles['Normal'], alignment=1, fontSize=9, textColor=colors.HexColor('#16a34a')))],
    ]
    t_right = Table(right_content, colWidths=[2.4*inch])
    t_right.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    body_table = Table([[t_left, t_right]], colWidths=[5.1*inch, 2.4*inch])
    body_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(body_table)
    story.append(Spacer(1, 15))

    # 3. Booking & Attendee Breakdown Details
    details_data = [
        [
            Paragraph("<b>Booking ID</b>", meta_label_style),
            Paragraph("<b>Attendee Name</b>", meta_label_style),
            Paragraph("<b>Ticket Code</b>", meta_label_style),
            Paragraph("<b>Tier</b>", meta_label_style),
            Paragraph("<b>Total Paid</b>", meta_label_style),
        ],
        [
            Paragraph(f"<b>{booking.booking_id}</b>", meta_val_style),
            Paragraph(attendee, meta_val_style),
            Paragraph(ticket_code, meta_val_style),
            Paragraph(f"{ticket_type_name} ({booking.total_tickets}x)", meta_val_style),
            Paragraph(f"<b>₹{booking.total_amount}</b>", ParagraphStyle('Amt', parent=meta_val_style, textColor=primary_color, fontName='Helvetica-Bold')),
        ]
    ]
    t_details = Table(details_data, colWidths=[1.4*inch, 1.8*inch, 1.7*inch, 1.4*inch, 1.2*inch])
    t_details.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e0e7ff")),
        ('TEXTCOLOR', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_details)
    story.append(Spacer(1, 20))

    # 4. Instructions & Security Notice
    instructions = [
        Paragraph("<b>Important Guidelines:</b>", ParagraphStyle('WarnH', parent=styles['Normal'], fontSize=10, textColor=dark_color, fontName='Helvetica-Bold')),
        Paragraph("1. Please present this printed PDF or digital barcode on your mobile device at the entry gate.", subtitle_style),
        Paragraph("2. Each ticket possesses a cryptographically signed QR token and is strictly valid for single check-in.", subtitle_style),
        Paragraph("3. Government-issued photo identification must be presented upon request matching the attendee name.", subtitle_style),
        Paragraph("4. Tickets are non-transferable once scanned or checked in.", subtitle_style),
    ]
    for p in instructions:
        story.append(p)
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=4, spaceAfter=8))
    story.append(Paragraph("EventHub Ticketing System &bull; Powered by Django & Razorpay &bull; www.eventhub.com", ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=9, textColor=gray_color)))

    doc.build(story)
    buffer.seek(0)
    return buffer

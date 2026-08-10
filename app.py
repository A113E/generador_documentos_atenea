import os
import base64
import io
from datetime import datetime
from flask import Flask, request, render_template, send_file, send_from_directory
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PIL import Image as PILImage
import re

app = Flask(__name__, 
            static_folder='static',  # Asegurar que Flask sepa dónde están los estáticos
            static_url_path='/static')  # Ruta URL para estáticos
app.config['SECRET_KEY'] = 'atenea-consultores-secret-key-2026'

# Ruta explícita para archivos estáticos 
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ============================================
# PRICE CONFIGURATION
# ============================================
PRICES = {
    'Pregrado': 80,
    'Diplomado': 80,
    'Especializacion': 80,
    'Maestria': 100,
    'Doctorado': 100
}

# ============================================
# ROUTES
# ============================================
@app.route('/')
def index():
    """Main page with service selector"""
    return render_template('index.html')

@app.route('/form/tesis') 
def thesis_form():
    """Form for thesis service"""
    return render_template('form_tesis.html')

@app.route('/generar-pdf/tesis', methods=['POST'])
def generate_thesis_pdf():
    """Generates the commitment letter PDF for thesis service"""
    try:
        # Get form data
        client_name = request.form.get('clientName', '').strip()
        client_id = request.form.get('clientId', '').strip()
        client_address = request.form.get('clientAddress', '').strip()
        academic_level = request.form.get('academicLevel', '').strip()
        institution = request.form.get('institution', '').strip()
        thesis_topic = request.form.get('thesisTopic', '').strip()
        delivery_date = request.form.get('deliveryDate', '').strip()
        currency = request.form.get('currency', 'USD').strip()
        price = float(request.form.get('price', 0))
        signature_data = request.form.get('signatureData', '')

        # Validate required fields
        required_fields = [
            (client_name, 'Nombre del cliente'),
            (client_id, 'Carnet de Identidad'),
            (client_address, 'Dirección'),
            (academic_level, 'Nivel académico'),
            (institution, 'Institución'),
            (thesis_topic, 'Tema de la tesis'),
            (delivery_date, 'Fecha de entrega')
        ]

        for value, field in required_fields:
            if not value:
                return f"Error: El campo '{field}' es obligatorio", 400

        # Validate ID format (11 digits)
        if not re.match(r'^\d{11}$', client_id):
            return "Error: El Carnet de Identidad debe tener 11 dígitos numéricos", 400

        # Format date
        try:
            date_obj = datetime.strptime(delivery_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d de %B de %Y')
        except:
            formatted_date = delivery_date

        # Generate PDF
        pdf_buffer = generate_commitment_letter(
            client_name=client_name,
            client_id=client_id,
            client_address=client_address,
            academic_level=academic_level,
            institution=institution,
            thesis_topic=thesis_topic,
            delivery_date=formatted_date,
            currency=currency,
            price=price,
            signature_data=signature_data
        )

        # Create filename
        filename = f"carta_compromiso_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            download_name=filename,
            as_attachment=True,
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"❌ Error generating PDF: {str(e)}")
        return f"Error al generar el documento: {str(e)}", 500

# ============================================
# FUNCTION: Generate Commitment Letter
# ============================================
def generate_commitment_letter(client_name, client_id, client_address,
                                academic_level, institution, thesis_topic,
                                delivery_date, currency, price, signature_data):
    """
    Generates the PDF commitment letter for thesis service
    """
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2.5*cm,
        leftMargin=2.5*cm,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm,
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    # ==========================================
    # CUSTOM STYLES
    # ==========================================
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=4,
        textColor=colors.HexColor('#1a3a5c'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=15,
        textColor=colors.HexColor('#5a7a9a')
    )
    
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.HexColor('#1a3a5c'),
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=6
    )
    
    # Estilo para el texto de las tablas (sin negritas)
    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#333333')
    )
    
    # Estilo para el label de las tablas (con negrita)
    table_label_style = ParagraphStyle(
        'TableLabel',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#1a3a5c'),
        fontName='Helvetica-Bold'
    )
    
    signature_style = ParagraphStyle(
        'Signature',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=2
    )
    
    # ==========================================
    # 1. LOGO AND HEADER
    # ==========================================
    try:
        logo_path = os.path.join('static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            logo_img = PILImage.open(logo_path)
            
            max_width = 80
            max_height = 80
            ratio = min(max_width/logo_img.width, max_height/logo_img.height)
            new_size = (int(logo_img.width * ratio), int(logo_img.height * ratio))
            logo_img = logo_img.resize(new_size, PILImage.Resampling.LANCZOS)
            
            img_bytes = io.BytesIO()
            logo_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            header_style = ParagraphStyle(
                'HeaderStyle',
                parent=styles['Title'],
                fontSize=20,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#1a3a5c')
            )
            
            logo_table = Table([
                [Image(img_bytes, width=new_size[0], height=new_size[1]), 
                 Paragraph("ATENEA CONSULTORES<br/><font size='10' color='#5a7a9a'>Asesoría Académica Profesional</font>", 
                          header_style)]
            ], colWidths=[3*cm, 12*cm])
            logo_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (1,0), (1,0), 'CENTER'),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(logo_table)
    except Exception as e:
        print(f"⚠️ Error loading logo: {e}")
        story.append(Paragraph("ATENEA CONSULTORES", title_style))
        story.append(Paragraph("Asesoría Académica Profesional", subtitle_style))
    
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a3a5c'), spaceAfter=15))
    
    # ==========================================
    # 2. TITLE AND INITIAL DATA
    # ==========================================
    story.append(Paragraph("CARTA DE COMPROMISO DE SERVICIO", section_style))
    story.append(Spacer(1, 0.2*cm))
    
    current_date = datetime.now().strftime('La Habana, %d de %B de %Y')
    story.append(Paragraph(current_date, body_style))
    story.append(Spacer(1, 0.3*cm))
    
    story.append(Paragraph(
        f"Por medio de la presente, <b>Atenea Consultores</b> y el cliente <b>{client_name}</b> "
        "acuerdan la prestación de servicios de asesoría académica en los siguientes términos:",
        body_style
    ))
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 3. CLIENT DATA - CORREGIDO (sin etiquetas HTML)
    # ==========================================
    story.append(Paragraph("DATOS DEL CLIENTE", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    # Usar Paragraph en lugar de texto plano para que las negritas funcionen
    client_data = [
        [Paragraph("Nombre:", table_label_style), Paragraph(client_name, table_text_style)],
        [Paragraph("Carnet de Identidad:", table_label_style), Paragraph(client_id, table_text_style)],
        [Paragraph("Dirección:", table_label_style), Paragraph(client_address, table_text_style)],
        [Paragraph("Institución:", table_label_style), Paragraph(institution, table_text_style)]
    ]
    
    client_table = Table(client_data, colWidths=[4*cm, 10.5*cm])
    client_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f4f8')),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 4. SERVICE DATA - CORREGIDO (sin etiquetas HTML)
    # ==========================================
    story.append(Paragraph("DATOS DEL SERVICIO", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    service_data = [
        [Paragraph("Servicio:", table_label_style), Paragraph(f"Asesoría para la confección de tesis de {academic_level}", table_text_style)],
        [Paragraph("Tema:", table_label_style), Paragraph(thesis_topic, table_text_style)],
        [Paragraph("Plazo de entrega:", table_label_style), Paragraph(delivery_date, table_text_style)],
        [Paragraph("Costo total:", table_label_style), Paragraph(f"{price:.2f} {currency}", table_text_style)],
        [Paragraph("Forma de pago:", table_label_style), Paragraph("30% al inicio (firma), 40% en la entrega del borrador, 30% en la entrega final", table_text_style)],
        [Paragraph("Incluye:", table_label_style), Paragraph("2 rondas de correcciones y asesoría continua vía WhatsApp/email", table_text_style)]
    ]
    
    service_table = Table(service_data, colWidths=[4*cm, 10.5*cm])
    service_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f4f8')),
    ]))
    story.append(service_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 5. IMPORTANT NOTE ABOUT DELIVERY DATE
    # ==========================================
    story.append(Paragraph("NOTA IMPORTANTE", section_style))
    note_text = """
    Debido a la situación actual del país (bloqueo económico, limitaciones de conectividad y servicios), 
    la fecha de entrega estipulada puede estar sujeta a cambios. En caso de ser necesario, 
    se notificará al cliente con la debida antelación y se acordará una nueva fecha de mutuo acuerdo.
    """
    story.append(Paragraph(note_text, ParagraphStyle(
        'Note',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#e67e22'),
        backColor=colors.HexColor('#fff8e1'),
        borderPadding=(10, 10, 10, 10),
        borderColor=colors.HexColor('#f39c12'),
        borderWidth=1,
        borderRadius=6
    )))
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 6. SIGNATURES
    # ==========================================
    story.append(Paragraph("FIRMAS DE CONFORMIDAD", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    # ===== CLIENT SIGNATURE =====
    try:
        # Si hay firma, procesarla; si no, mostrar línea en blanco
        if signature_data and len(signature_data) > 100:
            if ',' in signature_data:
                signature_base64 = signature_data.split(',')[1]
            else:
                signature_base64 = signature_data
            
            signature_bytes = base64.b64decode(signature_base64)
            signature_img = PILImage.open(io.BytesIO(signature_bytes))
            
            if signature_img.mode in ('RGBA', 'LA'):
                background = PILImage.new('RGB', signature_img.size, (255, 255, 255))
                background.paste(signature_img, mask=signature_img.split()[-1] if signature_img.mode == 'RGBA' else None)
                signature_img = background
            elif signature_img.mode == 'P':
                signature_img = signature_img.convert('RGB')
            
            max_width = 250
            max_height = 70
            ratio = min(max_width/signature_img.width, max_height/signature_img.height)
            new_size = (int(signature_img.width * ratio), int(signature_img.height * ratio))
            signature_img = signature_img.resize(new_size, PILImage.Resampling.LANCZOS)
            
            img_bytes = io.BytesIO()
            signature_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            signature_table = Table([
                ["Firma del Cliente:", ""],
                [Image(img_bytes, width=new_size[0], height=new_size[1]), ""]
            ], colWidths=[4*cm, 10.5*cm])
            signature_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(signature_table)
        else:
            # Sin firma, mostrar línea
            story.append(Paragraph("Firma del Cliente:", body_style))
            story.append(Paragraph("___________________________________", body_style))
        
        story.append(Paragraph(f"<b>{client_name}</b>", signature_style))
        
    except Exception as e:
        print(f"⚠️ Error processing client signature: {e}")
        story.append(Paragraph("Firma del Cliente:", body_style))
        story.append(Paragraph("___________________________________", body_style))
        story.append(Paragraph(f"{client_name}", body_style))
    
    story.append(Spacer(1, 0.3*cm))
    
    # ===== CONSULTANT SIGNATURE =====
    try:
        consultant_signature_path = os.path.join('static', 'img', 'firma_albe.png')
        if os.path.exists(consultant_signature_path):
            consultant_sig = PILImage.open(consultant_signature_path)
            
            if consultant_sig.mode in ('RGBA', 'LA'):
                background = PILImage.new('RGB', consultant_sig.size, (255, 255, 255))
                background.paste(consultant_sig, mask=consultant_sig.split()[-1] if consultant_sig.mode == 'RGBA' else None)
                consultant_sig = background
            elif consultant_sig.mode == 'P':
                consultant_sig = consultant_sig.convert('RGB')
            
            max_width = 250
            max_height = 70
            ratio = min(max_width/consultant_sig.width, max_height/consultant_sig.height)
            new_size = (int(consultant_sig.width * ratio), int(consultant_sig.height * ratio))
            consultant_sig = consultant_sig.resize(new_size, PILImage.Resampling.LANCZOS)
            
            img_bytes = io.BytesIO()
            consultant_sig.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            consultant_table = Table([
                ["Firma del Consultor (Atenea Consultores):", ""],
                [Image(img_bytes, width=new_size[0], height=new_size[1]), ""]
            ], colWidths=[4*cm, 10.5*cm])
            consultant_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(consultant_table)
        else:
            story.append(Paragraph("Firma del Consultor:", body_style))
            story.append(Paragraph("Atenea Consultores", body_style))
            story.append(Paragraph("___________________________________", body_style))
    except Exception as e:
        print(f"⚠️ Error processing consultant signature: {e}")
        story.append(Paragraph("Firma del Consultor:", body_style))
        story.append(Paragraph("Atenea Consultores", body_style))
        story.append(Paragraph("___________________________________", body_style))
    
    # ==========================================
    # 7. FOOTER
    # ==========================================
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=8))
    story.append(Paragraph(
        "Este documento es un compromiso de servicio entre las partes. "
        "Atenea Consultores se compromete a cumplir con los estándares de calidad y confidencialidad acordados. "
        "Para cualquier consulta, contactar por WhatsApp o correo electrónico.",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#888'),
            alignment=TA_CENTER
        )
    ))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# ============================================
# RUN APPLICATION
# ============================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Para Vercel - exportar la app
app = app
import os
import base64
import io
from datetime import datetime
from flask import Flask, request, render_template, send_file
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PIL import Image as PILImage
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'atenea-consultores-secret-key-2026'

# ============================================
# PRICE CONFIGURATION
# ============================================
PRICES = {
    'Pregrado': 80,
    'Diplomado': 90,
    'Especializacion': 90,
    'Maestria': 110,
    'Doctorado': 120
}

# Precios específicos por servicio y nivel académico (TESIS)
SERVICE_PRICES = {
    'confeccion_completa': {
        'Pregrado': 80,
        'Diplomado': 90,
        'Especializacion': 100,
        'Maestria': 110,
        'Doctorado': 120
    },
    'confeccion_capitulo': {
        'Pregrado': 35,
        'Diplomado': 40,
        'Especializacion': 45,
        'Maestria': 50,
        'Doctorado': 60
    },
    'revision_tesis': {
        'Pregrado': 30,
        'Diplomado': 40,
        'Especializacion': 40,
        'Maestria': 50,
        'Doctorado': 50
    },
    'revision_bibliografica': {
        'Pregrado': 0,
        'Diplomado': 0,
        'Especializacion': 0,
        'Maestria': 0,
        'Doctorado': 0
    }
}

# Descripciones de servicios para mostrar en el PDF (TESIS)
SERVICE_DESCRIPTIONS = {
    'confeccion_completa': 'Elaboración completa de la tesis incluyendo todos los capítulos: Introducción, Marco Teórico, Metodología, Resultados, Discusión, Conclusiones y Bibliografía. Incluye 3 rondas de revisiones gratuitas.',
    'confeccion_capitulo': 'Elaboración de un capítulo específico de la tesis (ej: Marco Teórico, Metodología, etc.). Incluye 2 rondas de revisiones gratuitas.',
    'revision_tesis': 'Revisión exhaustiva del trabajo completo con sugerencias de mejora en estructura, contenido, redacción y formato. No incluye corrección directa del texto, solo sugerencias.',
    'revision_bibliografica': 'Búsqueda y/o revisión de referencias bibliográficas según la norma seleccionada. El precio se calcula multiplicando la cantidad de referencias por 100 CUP.'
}

# ============================================
# CONFIGURACIÓN PARA PUBLICACIÓN CIENTÍFICA
# ============================================
ARTICLE_TYPE_PRICES = {
    'original': 50,
    'revision': 60,
    'ensayo': 70,
    'otros': 50
}

ARTICLE_TYPE_LABELS = {
    'original': 'Artículo original de investigación',
    'revision': 'Artículo de revisión bibliográfica',
    'ensayo': 'Ensayo clínico o estudio de caso',
    'otros': 'Otros'
}

PUBLICATION_SERVICE_DESCRIPTIONS = {
    'confeccion_articulo': 'Elaboración completa del artículo científico con todas las secciones (IMRYD), análisis estadístico, tablas y gráficos. Incluye selección de revista, adaptación a normas, envío y seguimiento de revisiones. Cubre una revista. Reenvío a otra revista: +$25 USD.',
    'revision_articulo': 'Revisión exhaustiva del artículo con sugerencias de mejora en estructura, contenido, redacción y formato, o adaptación al formato específico de la revista seleccionada. No incluye corrección directa del texto.',
    'revision_bibliografica_pub': 'Búsqueda y/o revisión de referencias bibliográficas según la norma seleccionada. El precio se calcula multiplicando la cantidad de referencias por 100 CUP.'
}

PUBLICATION_SERVICE_PRICES = {
    'confeccion_articulo': 50,  # Precio base, se suma el extra según tipo de artículo
    'revision_articulo': 40,
    'revision_bibliografica_pub': 0  # Variable: cantidad × 100 CUP
}

# ============================================
# ROUTES
# ============================================
@app.route('/')
def index():
    """Main page with service selector"""
    return render_template('index.html')

# ============================================
# RUTA: TESIS
# ============================================
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
        
        # NUEVOS CAMPOS
        selected_services = request.form.get('selectedServices', '').strip()
        reference_count = int(request.form.get('referenceCount', 0) or 0)

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

        # Validar que haya al menos un servicio seleccionado
        if not selected_services:
            return "Error: Debe seleccionar al menos un servicio", 400

        # Format date
        try:
            date_obj = datetime.strptime(delivery_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d de %B de %Y')
        except:
            formatted_date = delivery_date

        # Generate PDF
        pdf_buffer = generate_thesis_commitment_letter(
            client_name=client_name,
            client_id=client_id,
            client_address=client_address,
            academic_level=academic_level,
            institution=institution,
            thesis_topic=thesis_topic,
            delivery_date=formatted_date,
            currency=currency,
            price=price,
            signature_data=signature_data,
            selected_services=selected_services,
            reference_count=reference_count
        )

        # Create filename
        filename = f"carta_compromiso_tesis_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
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
# RUTA: BÚSQUEDA BIBLIOGRÁFICA
# ============================================
@app.route('/form/busqueda')
def busqueda_form():
    """Form for bibliographic search service"""
    return render_template('form_busqueda.html')

@app.route('/generar-pdf/busqueda', methods=['POST'])
def generate_busqueda_pdf():
    """Generates the commitment letter PDF for bibliographic search service"""
    try:
        # Get form data
        client_name = request.form.get('clientName', '').strip()
        client_id = request.form.get('clientId', '').strip()
        client_address = request.form.get('clientAddress', '').strip()
        institution = request.form.get('institution', '').strip()
        search_topics = request.form.get('searchTopics', '').strip()
        service_type = request.form.get('serviceType', '').strip()
        citation_style = request.form.get('citationStyle', '').strip()
        reference_count = int(request.form.get('referenceCount', 0))
        observations = request.form.get('observations', '').strip()
        delivery_date = request.form.get('deliveryDate', '').strip()
        price = float(request.form.get('price', 0))
        signature_data = request.form.get('signatureData', '')

        # Validate required fields
        required_fields = [
            (client_name, 'Nombre del cliente'),
            (client_id, 'Carnet de Identidad'),
            (client_address, 'Dirección'),
            (institution, 'Institución'),
            (search_topics, 'Temas de búsqueda'),
            (delivery_date, 'Fecha de entrega')
        ]

        for value, field in required_fields:
            if not value:
                return f"Error: El campo '{field}' es obligatorio", 400

        if reference_count < 1 or reference_count > 300:
            return "Error: La cantidad de referencias debe ser entre 1 y 300", 400

        # Validate ID format
        if not re.match(r'^\d{11}$', client_id):
            return "Error: El Carnet de Identidad debe tener 11 dígitos numéricos", 400

        # Format date
        try:
            date_obj = datetime.strptime(delivery_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d de %B de %Y')
        except:
            formatted_date = delivery_date

        # Generate PDF
        pdf_buffer = generate_busqueda_commitment_letter(
            client_name=client_name,
            client_id=client_id,
            client_address=client_address,
            institution=institution,
            search_topics=search_topics,
            service_type=service_type,
            citation_style=citation_style,
            reference_count=reference_count,
            observations=observations,
            delivery_date=formatted_date,
            price=price,
            signature_data=signature_data
        )

        filename = f"carta_compromiso_busqueda_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
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
# RUTA: PUBLICACIÓN CIENTÍFICA
# ============================================
@app.route('/form/publicacion')
def publicacion_form():
    """Form for scientific publication service"""
    return render_template('form_publicacion.html')

@app.route('/generar-pdf/publicacion', methods=['POST'])
def generate_publicacion_pdf():
    """Generates the commitment letter PDF for scientific publication service"""
    try:
        # Get form data
        client_name = request.form.get('clientName', '').strip()
        client_id = request.form.get('clientId', '').strip()
        client_address = request.form.get('clientAddress', '').strip()
        institution = request.form.get('institution', '').strip()
        article_title = request.form.get('articleTitle', '').strip()
        article_type = request.form.get('articleType', '').strip()
        article_topic = request.form.get('articleTopic', '').strip()
        selected_services = request.form.get('selectedServices', '').strip()
        journal_option = request.form.get('journalOption', '').strip()
        journal_name = request.form.get('journalName', '').strip()
        journal_observations = request.form.get('journalObservations', '').strip()
        delivery_date = request.form.get('deliveryDate', '').strip()
        currency = request.form.get('currency', 'USD').strip()
        price = float(request.form.get('price', 0))
        reference_count = int(request.form.get('referenceCount', 0) or 0)
        signature_data = request.form.get('signatureData', '')

        # Validate required fields
        required_fields = [
            (client_name, 'Nombre del cliente'),
            (client_id, 'Carnet de Identidad'),
            (client_address, 'Dirección'),
            (institution, 'Institución'),
            (article_title, 'Título del artículo'),
            (article_type, 'Tipo de artículo'),
            (article_topic, 'Tema o área de conocimiento'),
            (selected_services, 'Servicios seleccionados'),
            (delivery_date, 'Fecha de entrega')
        ]

        for value, field in required_fields:
            if not value:
                return f"Error: El campo '{field}' es obligatorio", 400

        # Validate ID format
        if not re.match(r'^\d{11}$', client_id):
            return "Error: El Carnet de Identidad debe tener 11 dígitos numéricos", 400

        # Validar que haya al menos un servicio seleccionado
        if not selected_services:
            return "Error: Debe seleccionar al menos un servicio", 400

        # Validar nombre de revista si el cliente la sugiere
        if journal_option == 'cliente' and not journal_name:
            return "Error: Debe indicar el nombre de la revista sugerida", 400

        # Si hay revisión bibliográfica, validar cantidad
        services_list = [s.strip() for s in selected_services.split(',') if s.strip()]
        if 'revision_bibliografica_pub' in services_list:
            if reference_count < 1 or reference_count > 300:
                return "Error: Para la revisión bibliográfica, indique una cantidad de referencias entre 1 y 300", 400

        # Format date
        try:
            date_obj = datetime.strptime(delivery_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d de %B de %Y')
        except:
            formatted_date = delivery_date

        # Generate PDF
        pdf_buffer = generate_publicacion_commitment_letter(
            client_name=client_name,
            client_id=client_id,
            client_address=client_address,
            institution=institution,
            article_title=article_title,
            article_type=article_type,
            article_topic=article_topic,
            selected_services=selected_services,
            journal_option=journal_option,
            journal_name=journal_name,
            journal_observations=journal_observations,
            delivery_date=formatted_date,
            currency=currency,
            price=price,
            reference_count=reference_count,
            signature_data=signature_data
        )

        filename = f"carta_compromiso_publicacion_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
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
# FUNCIÓN: GENERAR PDF PARA TESIS
# ============================================
def generate_thesis_commitment_letter(client_name, client_id, client_address,
                                academic_level, institution, thesis_topic,
                                delivery_date, currency, price, signature_data,
                                selected_services, reference_count):
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
    
    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#333333')
    )
    
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
    # 3. CLIENT DATA
    # ==========================================
    story.append(Paragraph("DATOS DEL CLIENTE", section_style))
    story.append(Spacer(1, 0.1*cm))
    
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
    # 4. SERVICE DATA
    # ==========================================
    story.append(Paragraph("DATOS DEL SERVICIO", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    # Procesar servicios seleccionados
    services_list = [s.strip() for s in selected_services.split(',') if s.strip()]
    services_display = []
    for service_key in services_list:
        if service_key in SERVICE_DESCRIPTIONS:
            services_display.append(SERVICE_DESCRIPTIONS[service_key])
    
    services_text = "\n".join([f"• {desc}" for desc in services_display])
    
    # Construir datos del servicio
    service_data = [
        [Paragraph("Tipo de servicio:", table_label_style), Paragraph("Asesoría para la confección de tesis", table_text_style)],
        [Paragraph("Nivel académico:", table_label_style), Paragraph(academic_level, table_text_style)],
        [Paragraph("Tema:", table_label_style), Paragraph(thesis_topic, table_text_style)],
        [Paragraph("Servicios contratados:", table_label_style), Paragraph(services_text, table_text_style)],
    ]
    
    # Agregar cantidad de referencias si aplica
    if 'revision_bibliografica' in services_list and reference_count > 0:
        service_data.append([
            Paragraph("Referencias bibliográficas:", table_label_style),
            Paragraph(str(reference_count), table_text_style)
        ])
    
    service_data.extend([
        [Paragraph("Plazo de entrega:", table_label_style), Paragraph(delivery_date, table_text_style)],
        [Paragraph("Costo total:", table_label_style), Paragraph(f"{price:.2f} {currency}", table_text_style)],
    ])
    
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
    # 5. FORMA DE PAGO
    # ==========================================
    story.append(Paragraph("CONDICIONES DE PAGO", section_style))
    payment_text = """
    El pago se realizará de la siguiente forma:
    30% al inicio del servicio (firma del compromiso), 40% en la entrega del borrador y 30% en la entrega final.
    """
    story.append(Paragraph(payment_text, body_style))
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 6. NOTA IMPORTANTE SOBRE PLAZOS
    # ==========================================
    story.append(Paragraph("NOTA IMPORTANTE SOBRE PLAZOS", section_style))
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
    # 7. CONDICIONES LEGALES
    # ==========================================
    story.append(Paragraph("CONDICIONES LEGALES", section_style))
    
    legal_conditions = [
        "1. Naturaleza del servicio: El servicio prestado por Atenea Consultores consiste en la asesoría, confección y/o revisión de trabajos académicos. No se garantiza la aceptación o aprobación absoluta por parte de la institución educativa o tribunal evaluador.",
        "2. Responsabilidad del cliente: El cliente es el único responsable de leer, revisar y aprobar el contenido final del trabajo entregado. Atenea Consultores no se hace responsable por errores tipográficos, de contenido o de formato que el cliente no haya señalado durante el proceso de revisión.",
        "3. Política de devoluciones: No se aceptan devoluciones una vez iniciado el servicio. El pago inicial del 30% es no reembolsable y cubre el tiempo de planificación y organización del proyecto.",
        "4. Garantía de calidad: Nuestro trabajo garantiza la confección y revisión del proyecto con los más altos estándares académicos, lo que aumenta significativamente las probabilidades de aceptación, pero no la garantiza.",
        "5. Revisiones adicionales: El servicio incluye hasta 3 rondas de revisiones por parte del cliente. Las revisiones adicionales a las acordadas tendrán un costo extra de $10 USD por ronda de revisión.",
        "6. Plazos: Los plazos de entrega son estimados y pueden verse afectados por factores externos como la disponibilidad de información, conectividad, o situaciones de fuerza mayor. En caso de retraso, se notificará al cliente con antelación."
    ]
    
    for condition in legal_conditions:
        story.append(Paragraph(condition, body_style))
        story.append(Spacer(1, 0.1*cm))
    
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 8. SIGNATURES
    # ==========================================
    story.append(Paragraph("FIRMAS DE CONFORMIDAD", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    # ===== CLIENT SIGNATURE =====
    try:
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
    # 9. FOOTER
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
# FUNCIÓN: GENERAR PDF PARA BÚSQUEDA BIBLIOGRÁFICA
# ============================================
def generate_busqueda_commitment_letter(client_name, client_id, client_address,
                                        institution, search_topics, service_type,
                                        citation_style, reference_count, observations,
                                        delivery_date, price, signature_data):
    """
    Generates the PDF commitment letter for bibliographic search service
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
    
    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#333333')
    )
    
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
    # 3. CLIENT DATA
    # ==========================================
    story.append(Paragraph("DATOS DEL CLIENTE", section_style))
    story.append(Spacer(1, 0.1*cm))
    
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
    # 4. SERVICE DATA
    # ==========================================
    story.append(Paragraph("DATOS DEL SERVICIO", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    # Mapear tipo de servicio para mostrar bonito
    service_type_map = {
        'busqueda': 'Búsqueda bibliográfica',
        'revision': 'Revisión y formato de bibliografía'
    }
    service_type_display = service_type_map.get(service_type, service_type)
    
    service_data = [
        [Paragraph("Tipo de servicio:", table_label_style), Paragraph(service_type_display, table_text_style)],
        [Paragraph("Temas de búsqueda:", table_label_style), Paragraph(search_topics, table_text_style)],
        [Paragraph("Norma bibliográfica:", table_label_style), Paragraph(citation_style, table_text_style)],
        [Paragraph("Cantidad de referencias:", table_label_style), Paragraph(str(reference_count), table_text_style)],
        [Paragraph("Plazo de entrega:", table_label_style), Paragraph(delivery_date, table_text_style)],
        [Paragraph("Costo total:", table_label_style), Paragraph(f"{price:.2f} CUP", table_text_style)]
    ]
    
    # Agregar observaciones si existen
    if observations:
        service_data.append([
            Paragraph("Observaciones:", table_label_style), 
            Paragraph(observations, table_text_style)
        ])
    
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
    # 5. NOTA IMPORTANTE SOBRE PLAZOS
    # ==========================================
    story.append(Paragraph("NOTA IMPORTANTE SOBRE PLAZOS", section_style))
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
    # 6. FORMA DE PAGO
    # ==========================================
    story.append(Paragraph("CONDICIONES DE PAGO", section_style))
    payment_text = """
    El pago se realizará en moneda nacional (CUP) de la siguiente forma:
    50% al inicio del servicio (firma del compromiso) y 50% al momento de la entrega final del trabajo.
    """
    story.append(Paragraph(payment_text, body_style))
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 7. CONDICIONES LEGALES
    # ==========================================
    story.append(Paragraph("CONDICIONES LEGALES", section_style))
    
    legal_conditions = [
        "1. Naturaleza del servicio: El servicio prestado por Atenea Consultores consiste en la búsqueda, revisión y/o formateo de referencias bibliográficas. No se garantiza la aceptación o aprobación absoluta por parte de la institución educativa.",
        "2. Responsabilidad del cliente: El cliente es el único responsable de verificar que las referencias encontradas correspondan a los temas solicitados. Atenea Consultores no se hace responsable por errores en la interpretación de los temas proporcionados.",
        "3. Política de devoluciones: No se aceptan devoluciones una vez iniciado el servicio. El pago inicial del 50% es no reembolsable.",
        "4. Plazos: Los plazos de entrega son estimados y pueden verse afectados por factores externos como la disponibilidad de información, conectividad, o situaciones de fuerza mayor."
    ]
    
    for condition in legal_conditions:
        story.append(Paragraph(condition, body_style))
        story.append(Spacer(1, 0.1*cm))
    
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 8. SIGNATURES
    # ==========================================
    story.append(Paragraph("FIRMAS DE CONFORMIDAD", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    # ===== CLIENT SIGNATURE =====
    try:
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
    # 9. FOOTER
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
# FUNCIÓN: GENERAR PDF PARA PUBLICACIÓN CIENTÍFICA
# ============================================
def generate_publicacion_commitment_letter(client_name, client_id, client_address,
                                          institution, article_title, article_type,
                                          article_topic, selected_services,
                                          journal_option, journal_name,
                                          journal_observations, delivery_date,
                                          currency, price, reference_count,
                                          signature_data):
    """
    Generates the PDF commitment letter for scientific publication service
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
    
    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#333333')
    )
    
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
    # 3. CLIENT DATA
    # ==========================================
    story.append(Paragraph("DATOS DEL CLIENTE", section_style))
    story.append(Spacer(1, 0.1*cm))
    
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
    # 4. SERVICE DATA
    # ==========================================
    story.append(Paragraph("DATOS DEL ARTÍCULO", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    # Mapear tipo de artículo
    article_type_label = ARTICLE_TYPE_LABELS.get(article_type, article_type)
    
    article_data = [
        [Paragraph("Título del artículo:", table_label_style), Paragraph(article_title, table_text_style)],
        [Paragraph("Tipo de artículo:", table_label_style), Paragraph(article_type_label, table_text_style)],
        [Paragraph("Tema o área:", table_label_style), Paragraph(article_topic, table_text_style)],
    ]
    
    article_table = Table(article_data, colWidths=[4*cm, 10.5*cm])
    article_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f4f8')),
    ]))
    story.append(article_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 5. SERVICIOS CONTRATADOS
    # ==========================================
    story.append(Paragraph("SERVICIOS CONTRATADOS", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    services_list = [s.strip() for s in selected_services.split(',') if s.strip()]
    services_display = []
    for service_key in services_list:
        if service_key in PUBLICATION_SERVICE_DESCRIPTIONS:
            services_display.append(PUBLICATION_SERVICE_DESCRIPTIONS[service_key])
    
    services_text = "\n".join([f"• {desc}" for desc in services_display])
    
    services_data = [
        [Paragraph("Servicios contratados:", table_label_style), Paragraph(services_text, table_text_style)],
    ]
    
    # Agregar cantidad de referencias si aplica
    if 'revision_bibliografica_pub' in services_list and reference_count > 0:
        services_data.append([
            Paragraph("Referencias bibliográficas:", table_label_style),
            Paragraph(str(reference_count), table_text_style)
        ])
    
    services_table = Table(services_data, colWidths=[4*cm, 10.5*cm])
    services_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f4f8')),
    ]))
    story.append(services_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 6. SELECCIÓN DE REVISTA
    # ==========================================
    story.append(Paragraph("SELECCIÓN DE REVISTA", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    journal_option_label = "El cliente sugiere la revista" if journal_option == 'cliente' else "Atenea Consultores sugiere la revista"
    
    journal_data = [
        [Paragraph("Opción:", table_label_style), Paragraph(journal_option_label, table_text_style)],
    ]
    
    if journal_option == 'cliente' and journal_name:
        journal_data.append([
            Paragraph("Revista sugerida:", table_label_style),
            Paragraph(journal_name, table_text_style)
        ])
    
    if journal_observations:
        journal_data.append([
            Paragraph("Observaciones:", table_label_style),
            Paragraph(journal_observations, table_text_style)
        ])
    
    journal_table = Table(journal_data, colWidths=[4*cm, 10.5*cm])
    journal_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f4f8')),
    ]))
    story.append(journal_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 7. CONDICIONES ECONÓMICAS
    # ==========================================
    story.append(Paragraph("CONDICIONES ECONÓMICAS", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    economic_data = [
        [Paragraph("Plazo de entrega:", table_label_style), Paragraph(delivery_date, table_text_style)],
        [Paragraph("Costo total:", table_label_style), Paragraph(f"{price:.2f} {currency}", table_text_style)],
    ]
    
    economic_table = Table(economic_data, colWidths=[4*cm, 10.5*cm])
    economic_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f4f8')),
    ]))
    story.append(economic_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 8. FORMA DE PAGO
    # ==========================================
    story.append(Paragraph("CONDICIONES DE PAGO", section_style))
    payment_text = """
    El pago se realizará de la siguiente forma:
    30% al inicio del servicio (firma del compromiso), 40% en la entrega del borrador y 30% en la entrega final.
    """
    story.append(Paragraph(payment_text, body_style))
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 9. NOTA IMPORTANTE SOBRE PLAZOS
    # ==========================================
    story.append(Paragraph("NOTA IMPORTANTE SOBRE PLAZOS", section_style))
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
    # 10. CONDICIONES LEGALES (PUBLICACIÓN)
    # ==========================================
    story.append(Paragraph("CONDICIONES LEGALES", section_style))
    
    legal_conditions = [
        "1. Naturaleza del servicio: El servicio prestado por Atenea Consultores consiste en la asesoría, confección, revisión y/o envío de artículos científicos. No se garantiza la aceptación o publicación del artículo, ya que esto depende de la importancia de la revista, el criterio de los revisores y la política editorial de cada publicación.",
        "2. Garantía de calidad: Nuestro trabajo asegura la integridad científica, la calidad académica y el cumplimiento de los estándares de escritura y formato del artículo, lo que aumenta significativamente las probabilidades de aceptación, pero no la garantiza.",
        "3. Responsabilidad del cliente: El cliente es el único responsable de leer, revisar y aprobar el contenido final del artículo entregado. Atenea Consultores no se hace responsable por errores tipográficos, de contenido o de formato que el cliente no haya señalado durante el proceso de revisión.",
        "4. Política de devoluciones: No se aceptan devoluciones una vez iniciado el servicio. El pago inicial del 30% es no reembolsable y cubre el tiempo de planificación y organización del proyecto.",
        "5. Envío a revistas: El servicio de confección incluye el envío a una revista. En caso de rechazo, el reenvío a otra revista tiene un costo adicional de $25 USD.",
        "6. Revisiones adicionales: El servicio incluye todas las rondas de revisiones solicitadas por el revisor de la revista, siempre que sean razonables y exista una posibilidad real de publicación. Cambios sustanciales o reescritura completa pueden tener costo adicional.",
        "7. Plazos: Los plazos de entrega son estimados y pueden verse afectados por factores externos como la disponibilidad de información, conectividad, o situaciones de fuerza mayor. En caso de retraso, se notificará al cliente con antelación."
    ]
    
    for condition in legal_conditions:
        story.append(Paragraph(condition, body_style))
        story.append(Spacer(1, 0.1*cm))
    
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # 11. SIGNATURES
    # ==========================================
    story.append(Paragraph("FIRMAS DE CONFORMIDAD", section_style))
    story.append(Spacer(1, 0.1*cm))
    
    # ===== CLIENT SIGNATURE =====
    try:
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
    # 12. FOOTER
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
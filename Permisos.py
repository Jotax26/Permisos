# -----------------------------------------------------------
# GENERADOR DE PDF COMPATIBLE (SIN EMOJIS / LATIN-1 SAFE)
# -----------------------------------------------------------
class SolicitudPDF(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path

    def header(self):
        # Franja superior azul
        self.set_fill_color(26, 54, 93)
        self.rect(0, 0, 210, 32, 'F')
        
        # Franja dorada
        self.set_fill_color(214, 158, 46)
        self.rect(0, 32, 210, 2, 'F')

        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, x=12, y=5, h=22)
            except Exception:
                pass

        self.set_xy(50, 6)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "SOLIDARISTAS", align="L", new_x="LMARGIN", new_y="NEXT")
        
        self.set_x(50)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(226, 232, 240)
        self.cell(0, 5, "GESTION DE TALENTO HUMANO - SOLICITUD DE PERMISO", align="L")
        self.ln(18)

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(226, 232, 240)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(3)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(113, 128, 150)
        self.cell(0, 5, "SOLIDARISTAS | Documento Digital Oficial de Control de Asistencia", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, f"Pagina {self.page_no()}", align="C")

def clean_text(txt):
    """Limpia el texto para asegurar compatibilidad con la codificacion Latin-1 de FPDF"""
    if txt is None:
        return ""
    return str(txt).encode('latin-1', 'replace').decode('latin-1')

def generar_pdf_solicitud(datos, logo_path=None):
    pdf = SolicitudPDF(logo_path=logo_path)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # --- ENCABEZADO DE DOCUMENTO / BADGE DE ESTADO ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(45, 55, 72)
    pdf.cell(100, 8, f"FOLIO: #{datos['id']:05d}")
    
    # Badge según el Estado
    estado_str = clean_text(datos['estado']).upper()
    if estado_str == "APROBADO":
        fill_color, text_color = (220, 252, 231), (22, 101, 52)
    elif estado_str == "RECHAZADO":
        fill_color, text_color = (254, 226, 226), (153, 27, 27)
    else:
        fill_color, text_color = (254, 243, 199), (146, 64, 14)

    pdf.set_fill_color(*fill_color)
    pdf.set_text_color(*text_color)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(80, 8, f"  ESTADO: {estado_str}  ", align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(113, 128, 150)
    pdf.cell(0, 5, f"Fecha de emision del reporte: {clean_text(datos['fecha_solicitud'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    def render_seccion(titulo):
        pdf.set_fill_color(237, 242, 247)
        pdf.set_text_color(26, 54, 93)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, f"  {clean_text(titulo)}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def render_fila(label1, valor1, label2="", valor2=""):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(74, 85, 104)
        pdf.cell(40, 6, clean_text(label1), border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(26, 32, 44)
        pdf.cell(50, 6, clean_text(valor1), border=0)
        
        if label2:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(74, 85, 104)
            pdf.cell(40, 6, clean_text(label2), border=0)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(26, 32, 44)
            pdf.cell(50, 6, clean_text(valor2), border=0)
        pdf.ln(6)

    # --- SECCIÓN 1: DATOS DEL COLABORADOR ---
    render_seccion("1. INFORMACION DEL COLABORADOR")
    render_fila("Nombre Completo:", datos['nombre_colaborador'], "Departamento:", datos['departamento'])
    render_fila("Jefe Inmediato:", datos['jefe_inmediato'])
    pdf.ln(4)

    # --- SECCIÓN 2: DETALLES DE LA SOLICITUD ---
    render_seccion("2. DETALLES DEL PERMISO")
    render_fila("Tipo de Permiso:", datos['tipo_permiso'], "Duracion:", f"{datos['cantidad']} {datos['unidad']}")
    render_fila("Fecha de Inicio:", datos['fecha_inicio'], "Fecha de Fin:", datos['fecha_fin'])
    pdf.ln(4)

    # --- SECCIÓN 3: MOTIVO Y JUSTIFICACIÓN ---
    render_seccion("3. MOTIVO Y JUSTIFICACION")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(45, 55, 72)
    motivo_text = clean_text(datos['motivo']).strip() if datos['motivo'] else "Sin observaciones adicionales."
    pdf.set_fill_color(247, 250, 252)
    pdf.multi_cell(0, 5, motivo_text, border=1, fill=True)
    pdf.ln(8)

    # --- SECCIÓN 4: CONFORMIDAD Y FIRMAS ---
    render_seccion("4. CONFORMIDAD Y VALIDACION DIGITAL")
    pdf.ln(4)

    y_inicio_firmas = pdf.get_y()

    # Caja Colaborador
    pdf.set_draw_color(226, 232, 240)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(15, y_inicio_firmas, 85, 38, 'DF')
    
    pdf.set_xy(18, y_inicio_firmas + 4)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(26, 54, 93)
    pdf.cell(79, 5, "COLABORADOR SOLICITANTE", align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(74, 85, 104)
    pdf.cell(79, 4, clean_text(datos['nombre_colaborador']), align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_xy(18, y_inicio_firmas + 22)
    st_colab = "[ X ] FIRMADO DIGITALMENTE" if str(datos['firma_colaborador']).lower() in ['sí', 'si', 'yes', '1', 'true'] else "[  ] PENDIENTE DE FIRMA"
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(34, 197, 94) if "[ X ]" in st_colab else pdf.set_text_color(239, 68, 68)
    pdf.cell(79, 5, st_colab, align="C")

    # Caja Jefe Inmediato
    pdf.rect(110, y_inicio_firmas, 85, 38, 'DF')
    
    pdf.set_xy(113, y_inicio_firmas + 4)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(26, 54, 93)
    pdf.cell(79, 5, "JEFE INMEDIATO / AUTORIZA", align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(113)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(74, 85, 104)
    pdf.cell(79, 4, clean_text(datos['jefe_inmediato']), align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_xy(113, y_inicio_firmas + 22)
    st_jefe = "[ X ] AUTORIZADO DIGITALMENTE" if str(datos['firma_jefe']).lower() in ['sí', 'si', 'yes', '1', 'true'] else "[  ] PENDIENTE DE AUTORIZACION"
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(34, 197, 94) if "[ X ]" in st_jefe else pdf.set_text_color(239, 68, 68)
    pdf.cell(79, 5, st_jefe, align="C")

    return bytes(pdf.output())
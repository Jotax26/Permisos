import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# -----------------------------------------------------------
# 1. CONFIGURACIÓN Y BASE DE DATOS SQLITE
# -----------------------------------------------------------
DATA_DIR = "/var/data" if os.path.exists("/var/data") else "."
DB_PATH = os.path.join(DATA_DIR, "permisos.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla de Empleados / Personal (Para autocomplete)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_colaborador TEXT UNIQUE,
            departamento TEXT,
            jefe_inmediato TEXT
        )
    ''')

    # Tabla de Solicitudes de Permisos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_solicitud TEXT,
            nombre_colaborador TEXT,
            departamento TEXT,
            jefe_inmediato TEXT,
            tipo_permiso TEXT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            cantidad REAL,
            unidad TEXT,
            motivo TEXT,
            estado TEXT DEFAULT 'Pendiente',
            firma_colaborador TEXT,
            firma_jefe TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------
# 2. GENERADOR DE PDF CON MARCA SOLIDARISTAS
# -----------------------------------------------------------
class SolicitudPDF(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path

    def header(self):
        # Banner superior azul
        self.set_fill_color(26, 54, 93) # Azul marino
        self.rect(0, 0, 210, 28, 'F')
        
        # Logo en PDF si existe
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, x=10, y=4, h=20)
            except Exception:
                pass

        self.set_font("Helvetica", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "SOLIDARISTAS", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "SOLICITUD DE PERMISO LABORAL", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "SOLIDARISTAS - Documento generado automáticamente por el Sistema de Gestión.", align="C")

def generar_pdf_solicitud(datos, logo_path=None):
    pdf = SolicitudPDF(logo_path=logo_path)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Folio y Estado
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(100, 6, f"Folio N°: #{datos['id']}")
    
    # Estado con color según el valor
    estado_str = str(datos['estado']).upper()
    if estado_str == "APROBADO":
        pdf.set_text_color(40, 167, 69)
    elif estado_str == "RECHAZADO":
        pdf.set_text_color(220, 53, 69)
    else:
        pdf.set_text_color(255, 193, 7)
        
    pdf.cell(0, 6, f"ESTADO: {estado_str}", align="R", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Fecha de Emisión: {datos['fecha_solicitud']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Función auxiliar para encabezado de secciones
    def crear_seccion(titulo):
        pdf.set_fill_color(237, 242, 247)
        pdf.set_text_color(26, 54, 93)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, f"  {titulo}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # Sección 1: Información del Colaborador
    crear_seccion("1. INFORMACIÓN DEL COLABORADOR")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    
    pdf.cell(50, 6, "Nombre Completo:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(datos['nombre_colaborador']), border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(50, 6, "Departamento / Área:", border=0)
    pdf.cell(0, 6, str(datos['departamento']), border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(50, 6, "Jefe Inmediato:", border=0)
    pdf.cell(0, 6, str(datos['jefe_inmediato']), border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Sección 2: Detalles del Permiso
    crear_seccion("2. DETALLES DEL PERMISO")
    pdf.set_font("Helvetica", "", 10)
    
    pdf.cell(50, 6, "Tipo de Permiso:", border=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, str(datos['tipo_permiso']), border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(50, 6, "Período Solicitado:", border=0)
    pdf.cell(0, 6, f"Desde {datos['fecha_inicio']} hasta {datos['fecha_fin']}", border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(50, 6, "Duración Total:", border=0)
    pdf.cell(0, 6, f"{datos['cantidad']} {datos['unidad']}", border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Sección 3: Motivo
    crear_seccion("3. MOTIVO Y JUSTIFICACIÓN")
    pdf.set_font("Helvetica", "I", 9)
    motivo_text = str(datos['motivo']) if datos['motivo'] else "Sin justificación adicional especificada."
    pdf.multi_cell(0, 5, motivo_text, border=1)
    pdf.ln(8)

    # Sección 4: Firmas
    crear_seccion("4. CONFORMIDAD Y FIRMAS")
    pdf.ln(12)
    
    y_actual = pdf.get_y()
    pdf.set_draw_color(150, 150, 150)
    pdf.line(20, y_actual, 85, y_actual)
    pdf.line(125, y_actual, 190, y_actual)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_xy(20, y_actual + 2)
    pdf.multi_cell(65, 4, f"{datos['nombre_colaborador']}\nColaborador Solicitante\nFirma Digital: {datos['firma_colaborador']}", align="C")

    pdf.set_xy(125, y_actual + 2)
    pdf.multi_cell(65, 4, f"{datos['jefe_inmediato']}\nJefe Inmediato / Autoriza\nFirma Digital: {datos['firma_jefe']}", align="C")

    return bytes(pdf.output())

# -----------------------------------------------------------
# 3. INTERFAZ EN STREAMLIT CON LOGO Y NOMBRE "SOLIDARISTAS"
# -----------------------------------------------------------
st.set_page_config(page_title="SOLIDARISTAS - Gestión de Permisos", page_icon="🏢", layout="wide")

# Gestión del Logo
LOGO_PATH = "logo.png"
uploaded_logo = st.sidebar.file_uploader("Cargar Logo de la Empresa", type=["png", "jpg", "jpeg"])

if uploaded_logo is not None:
    with open(LOGO_PATH, "wb") as f:
        f.write(uploaded_logo.getbuffer())

# Encabezado Principal en la App
col_logo, col_titulo = st.columns([1, 5])

with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=110)
    else:
        st.write("🏢")

with col_titulo:
    st.title("SOLIDARISTAS")
    st.caption("Sistema de Control y Gestión de Solicitudes de Permisos Laborales")

st.sidebar.markdown("---")
st.sidebar.title("SOLIDARISTAS")
menu = ["➕ Nueva Solicitud", "👤 Gestión de Personal", "📊 Base de Datos", "📈 Métricas"]
opcion = st.sidebar.selectbox("Navegación", menu)

# -----------------------------------------------------------
# OPCIÓN 1: NUEVA SOLICITUD
# -----------------------------------------------------------
if opcion == "➕ Nueva Solicitud":
    st.subheader("Formulario de Solicitud")

    conn = get_db_connection()
    empleados_df = pd.read_sql_query("SELECT * FROM empleados ORDER BY nombre_colaborador ASC", conn)
    conn.close()

    lista_empleados = ["-- Seleccionar Colaborador --", "➕ Registrar Nuevo Colaborador"] + empleados_df["nombre_colaborador"].tolist()
    
    col_sel, _ = st.columns([2, 1])
    with col_sel:
        seleccion_emp = st.selectbox("Seleccionar Colaborador de la Base de Datos", lista_empleados)

    nombre_def, dpto_def, jefe_def = "", "Operaciones", ""

    if seleccion_emp not in ["-- Seleccionar Colaborador --", "➕ Registrar Nuevo Colaborador"]:
        emp_data = empleados_df[empleados_df["nombre_colaborador"] == seleccion_emp].iloc[0]
        nombre_def = emp_data["nombre_colaborador"]
        dpto_def = emp_data["departamento"]
        jefe_def = emp_data["jefe_inmediato"]

    with st.form("form_permiso", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            fecha_solicitud = st.date_input("Fecha de Solicitud", datetime.now())
            nombre = st.text_input("Nombre Completo del Colaborador", value=nombre_def)
            
            dptos = ["Operaciones", "Tecnología", "Finanzas", "Talento Humano", "Ventas", "Logística"]
            idx_dpto = dptos.index(dpto_def) if dpto_def in dptos else 0
            departamento = st.selectbox("Departamento / Área", dptos, index=idx_dpto)
            
            jefe = st.text_input("Jefe Inmediato", value=jefe_def)
        
        with col2:
            tipo_permiso = st.selectbox(
                "Tipo de Permiso", 
                ["Cita Médica", "Incapacidad", "Vacaciones", "Permiso Personal", "Duelo / Luto", "Maternidad/Paternidad", "Otro"]
            )
            unidad = st.radio("Unidad de Medida", ["Días", "Horas"], horizontal=True)
            fecha_inicio = st.date_input("Fecha Inicio")
            fecha_fin = st.date_input("Fecha Fin")
            cantidad = st.number_input("Cantidad Solicitada", min_value=0.5, step=0.5)

        motivo = st.text_area("Motivo / Justificación Detallada")
        
        st.markdown("---")
        st.subheader("Firmas y Conformidad")
        c1, c2 = st.columns(2)
        with c1:
            firma_colab = st.checkbox("Firma Colaborador (Declaro conformidad)")
        with c2:
            firma_jefe = st.checkbox("Firma Jefe Inmediato (Autorización Previa)")

        enviar = st.form_submit_button("Guardar Solicitud")

        if enviar:
            if not nombre.strip():
                st.error("⚠️ El nombre del colaborador es obligatorio.")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # 1. Guardar o actualizar colaborador en la base de datos
                cursor.execute('''
                    INSERT INTO empleados (nombre_colaborador, departamento, jefe_inmediato)
                    VALUES (?, ?, ?)
                    ON CONFLICT(nombre_colaborador) DO UPDATE SET
                        departamento = excluded.departamento,
                        jefe_inmediato = excluded.jefe_inmediato
                ''', (nombre.strip(), departamento, jefe.strip()))

                # 2. Guardar la solicitud
                query = '''
                    INSERT INTO solicitudes 
                    (fecha_solicitud, nombre_colaborador, departamento, jefe_inmediato, 
                     tipo_permiso, fecha_inicio, fecha_fin, cantidad, unidad, motivo, estado, firma_colaborador, firma_jefe)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente', ?, ?)
                '''
                cursor.execute(query, (
                    str(fecha_solicitud), nombre.strip(), departamento, jefe.strip(),
                    tipo_permiso, str(fecha_inicio), str(fecha_fin), cantidad, unidad, motivo,
                    "Sí" if firma_colab else "No", "Sí" if firma_jefe else "No"
                ))
                conn.commit()
                conn.close()
                st.success("✅ Solicitud guardada con éxito y persona registrada/actualizada.")

# -----------------------------------------------------------
# OPCIÓN 2: GESTIÓN DE PERSONAL
# -----------------------------------------------------------
elif opcion == "👤 Gestión de Personal":
    st.subheader("Catálogo de Colaboradores Registrados")
    st.caption("Los colaboradores guardados aquí se autocompletan en el formulario.")

    conn = get_db_connection()
    df_emp = pd.read_sql_query("SELECT * FROM empleados ORDER BY nombre_colaborador ASC", conn)
    conn.close()

    if not df_emp.empty:
        st.dataframe(df_emp[["id", "nombre_colaborador", "departamento", "jefe_inmediato"]], use_container_width=True)
    else:
        st.info("No hay colaboradores registrados aún.")

    with st.expander("➕ Registrar Nuevo Colaborador Manualmente"):
        with st.form("form_nuevo_emp", clear_on_submit=True):
            n_nombre = st.text_input("Nombre Completo")
            n_dpto = st.selectbox("Departamento", ["Operaciones", "Tecnología", "Finanzas", "Talento Humano", "Ventas", "Logística"])
            n_jefe = st.text_input("Jefe Inmediato")
            btn_emp = st.form_submit_button("Guardar Personal")

            if btn_emp:
                if n_nombre.strip():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO empleados (nombre_colaborador, departamento, jefe_inmediato) VALUES (?, ?, ?)",
                                       (n_nombre.strip(), n_dpto, n_jefe.strip()))
                        conn.commit()
                        st.success(f"Colaborador {n_nombre} registrado correctamente.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("El colaborador ya existe en la base de datos.")
                    finally:
                        conn.close()

# -----------------------------------------------------------
# OPCIÓN 3: BASE DE DATOS Y DESCARGA DE PDF
# -----------------------------------------------------------
elif opcion == "📊 Base de Datos":
    st.subheader("Histórico de Solicitudes")

    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM solicitudes ORDER BY id DESC", conn)
    conn.close()

    if df.empty:
        st.info("No hay solicitudes registradas.")
    else:
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.subheader("📄 Generar y Descargar Solicitud en PDF")
        
        col_pdf1, col_pdf2 = st.columns([1, 2])
        with col_pdf1:
            id_pdf = st.number_input("Selecciona el ID de la Solicitud", min_value=int(df["id"].min()), max_value=int(df["id"].max()), step=1)
        
        with col_pdf2:
            st.write("")
            st.write("")
            if st.button("📄 Generar PDF"):
                solicitud_sel = df[df["id"] == id_pdf].iloc[0].to_dict()
                pdf_bytes = generar_pdf_solicitud(solicitud_sel, logo_path=LOGO_PATH if os.path.exists(LOGO_PATH) else None)

                st.download_button(
                    label=f"📥 Descargar PDF Solicitud #{id_pdf}",
                    data=pdf_bytes,
                    file_name=f"SOLIDARISTAS_Solicitud_{id_pdf}_{solicitud_sel['nombre_colaborador'].replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

        st.markdown("---")
        st.subheader("Acciones de Administración (Cambiar Estado)")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            sol_id = st.number_input("ID a Modificar", min_value=1, step=1)
        with col_b:
            nuevo_estado = st.selectbox("Nuevo Estado", ["Aprobado", "Rechazado", "Pendiente"])
        with col_c:
            st.write("")
            if st.button("Actualizar Estado"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE solicitudes SET estado = ? WHERE id = ?", (nuevo_estado, sol_id))
                conn.commit()
                conn.close()
                st.success(f"Estado de la solicitud #{sol_id} actualizado.")
                st.rerun()

# -----------------------------------------------------------
# OPCIÓN 4: MÉTRICAS
# -----------------------------------------------------------
elif opcion == "📈 Métricas":
    st.subheader("Métricas de Gestión - SOLIDARISTAS")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM solicitudes", conn)
    conn.close()

    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Solicitudes", len(df))
        m2.metric("Pendientes", len(df[df['estado'] == 'Pendiente']))
        m3.metric("Aprobadas", len(df[df['estado'] == 'Aprobado']))
        m4.metric("Rechazadas", len(df[df['estado'] == 'Rechazado']))

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.bar_chart(df['tipo_permiso'].value_counts())
        with c2:
            st.bar_chart(df['departamento'].value_counts())
    else:
        st.info("No hay datos para mostrar.")
import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from fpdf import FPDF
from sqlalchemy import create_engine, text

# Lista global de departamentos actualizada
DEPARTAMENTOS = [
    "Administración", 
    "Taller", 
    "Operaciones", 
    "Tecnología", 
    "Finanzas", 
    "Talento Humano", 
    "Ventas", 
    "Logística"
]

# -----------------------------------------------------------
# 1. CONEXIÓN A BASE DE DATOS NEON.TECH (POSTGRESQL)
# -----------------------------------------------------------
def get_engine():
    db_url = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL"))
    if not db_url:
        st.error("❌ No se encontró la variable DATABASE_URL en los Secrets.")
        st.stop()
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url, pool_pre_ping=True)

def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS empleados (
                id SERIAL PRIMARY KEY,
                nombre_colaborador TEXT UNIQUE NOT NULL,
                departamento TEXT,
                jefe_inmediato TEXT
            );
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS solicitudes (
                id SERIAL PRIMARY KEY,
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
            );
        '''))

init_db()

# -----------------------------------------------------------
# 2. GENERADOR DE PDF REDISEÑADO Y COMPATIBLE
# -----------------------------------------------------------
class SolicitudPDF(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path

    def header(self):
        # Franja superior azul
        self.set_fill_color(26, 54, 93)
        self.rect(0, 0, 210, 32, 'F')
        
        # Franja decorativa dorada
        self.set_fill_color(214, 158, 46)
        self.rect(0, 32, 210, 2, 'F')

        # Control del logo sin solapamiento
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, x=12, y=6, w=40, h=18)
            except Exception:
                pass

        # Texto del encabezado desplazado a la derecha (x=60)
        self.set_xy(60, 7)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, "SOLIDARISTAS", align="L", new_x="LMARGIN", new_y="NEXT")
        
        self.set_x(60)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(226, 232, 240)
        self.cell(0, 5, "GESTION DE TALENTO HUMANO | SOLICITUD DE PERMISO", align="L")
        self.ln(16)

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(226, 232, 240)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(3)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(113, 128, 150)
        self.cell(0, 4, "SOLIDARISTAS | Documento Oficial de Control de Asistencia", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, f"Pagina {self.page_no()}", align="C")

def clean_text(txt):
    """Limpia el texto para asegurar compatibilidad con la codificación Latin-1 de FPDF"""
    if txt is None:
        return ""
    return str(txt).encode('latin-1', 'replace').decode('latin-1')

def generar_pdf_solicitud(datos, logo_path=None):
    pdf = SolicitudPDF(logo_path=logo_path)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # --- CABECERA DE DOCUMENTO (FOLIO Y ESTADO) ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(45, 55, 72)
    pdf.cell(100, 8, f"FOLIO: #{datos['id']:05d}")
    
    # Badge de Estado
    estado_str = clean_text(datos['estado']).upper()
    if estado_str == "APROBADO":
        fill_color, text_color = (220, 252, 231), (22, 101, 52)
    elif estado_str == "RECHAZADO":
        fill_color, text_color = (254, 226, 226), (153, 27, 27)
    else:
        fill_color, text_color = (254, 243, 199), (146, 64, 14)

    pdf.set_fill_color(*fill_color)
    pdf.set_text_color(*text_color)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(80, 8, f"ESTADO: {estado_str}", align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(113, 128, 150)
    pdf.cell(0, 5, f"Fecha de emision: {clean_text(datos['fecha_solicitud'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    def render_seccion(titulo):
        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(203, 213, 225)
        pdf.set_text_color(30, 41, 59)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, f"   {clean_text(titulo)}", fill=True, border='B', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    def render_bloque(label1, val1, label2, val2):
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(35, 5, clean_text(label1))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(55, 5, clean_text(val1))

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(35, 5, clean_text(label2))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(55, 5, clean_text(val2), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # --- SECCIÓN 1: DATOS DEL COLABORADOR ---
    render_seccion("1. INFORMACION DEL COLABORADOR")
    render_bloque("Nombre Completo:", datos['nombre_colaborador'], "Departamento:", datos['departamento'])
    render_bloque("Jefe Inmediato:", datos['jefe_inmediato'], "", "")
    pdf.ln(2)

    # --- SECCIÓN 2: DETALLES DE LA SOLICITUD ---
    render_seccion("2. DETALLES DEL PERMISO")
    render_bloque("Tipo de Permiso:", datos['tipo_permiso'], "Duracion:", f"{datos['cantidad']} {datos['unidad']}")
    render_bloque("Fecha Inicio:", datos['fecha_inicio'], "Fecha Fin:", datos['fecha_fin'])
    pdf.ln(2)

    # --- SECCIÓN 3: MOTIVO Y JUSTIFICACIÓN ---
    render_seccion("3. MOTIVO Y JUSTIFICACION")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(51, 65, 85)
    motivo_text = clean_text(datos['motivo']).strip() if datos['motivo'] else "Sin observaciones adicionales."
    
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.multi_cell(0, 5, motivo_text, border=1, fill=True)
    pdf.ln(6)

    # --- SECCIÓN 4: CONFORMIDAD Y FIRMAS ---
    render_seccion("4. CONFORMIDAD Y VALIDACION DIGITAL")
    pdf.ln(2)

    y_inicio = pdf.get_y()

    # Caja Colaborador
    pdf.set_draw_color(203, 213, 225)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(15, y_inicio, 85, 34)
    
    pdf.set_xy(15, y_inicio + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(85, 4, "COLABORADOR SOLICITANTE", align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(85, 4, clean_text(datos['nombre_colaborador']), align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_xy(15, y_inicio + 22)
    st_colab = "[ X ] FIRMADO DIGITALMENTE" if str(datos['firma_colaborador']).lower() in ['sí', 'si', 'yes', '1', 'true'] else "[  ] PENDIENTE DE FIRMA"
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(22, 101, 52) if "[ X ]" in st_colab else pdf.set_text_color(185, 28, 28)
    pdf.cell(85, 4, st_colab, align="C")

    # Caja Jefe Inmediato
    pdf.rect(110, y_inicio, 85, 34)
    
    pdf.set_xy(110, y_inicio + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(85, 4, "JEFE INMEDIATO / AUTORIZA", align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(110)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(85, 4, clean_text(datos['jefe_inmediato']), align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_xy(110, y_inicio + 22)
    st_jefe = "[ X ] AUTORIZADO DIGITALMENTE" if str(datos['firma_jefe']).lower() in ['sí', 'si', 'yes', '1', 'true'] else "[  ] PENDIENTE DE AUTORIZACION"
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(22, 101, 52) if "[ X ]" in st_jefe else pdf.set_text_color(185, 28, 28)
    pdf.cell(85, 4, st_jefe, align="C")

    return bytes(pdf.output())

# -----------------------------------------------------------
# 3. INTERFAZ DE USUARIO EN STREAMLIT
# -----------------------------------------------------------
st.set_page_config(page_title="SOLIDARISTAS - Gestión de Permisos", page_icon="🏢", layout="wide")

LOGO_PATH = "logo.png"
uploaded_logo = st.sidebar.file_uploader("Cargar Logo de la Empresa", type=["png", "jpg", "jpeg"])

if uploaded_logo is not None:
    with open(LOGO_PATH, "wb") as f:
        f.write(uploaded_logo.getbuffer())

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

engine = get_engine()

# --- OPCIÓN 1: NUEVA SOLICITUD ---
if opcion == "➕ Nueva Solicitud":
    st.subheader("Formulario de Solicitud")

    empleados_df = pd.read_sql_query("SELECT * FROM empleados ORDER BY nombre_colaborador ASC", engine)

    lista_empleados = ["-- Seleccionar Colaborador --", "➕ Registrar Nuevo Colaborador"] + empleados_df["nombre_colaborador"].tolist()
    
    col_sel, _ = st.columns([2, 1])
    with col_sel:
        seleccion_emp = st.selectbox("Seleccionar Colaborador de la Base de Datos", lista_empleados)

    nombre_def, dpto_def, jefe_def = "", "Administración", ""

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
            
            idx_dpto = DEPARTAMENTOS.index(dpto_def) if dpto_def in DEPARTAMENTOS else 0
            departamento = st.selectbox("Departamento / Área", DEPARTAMENTOS, index=idx_dpto)
            
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
                with engine.begin() as conn:
                    upsert_emp = text('''
                        INSERT INTO empleados (nombre_colaborador, departamento, jefe_inmediato)
                        VALUES (:nombre, :dpto, :jefe)
                        ON CONFLICT (nombre_colaborador) 
                        DO UPDATE SET departamento = EXCLUDED.departamento, jefe_inmediato = EXCLUDED.jefe_inmediato;
                    ''')
                    conn.execute(upsert_emp, {
                        "nombre": nombre.strip(),
                        "dpto": departamento,
                        "jefe": jefe.strip()
                    })

                    insert_sol = text('''
                        INSERT INTO solicitudes 
                        (fecha_solicitud, nombre_colaborador, departamento, jefe_inmediato, 
                         tipo_permiso, fecha_inicio, fecha_fin, cantidad, unidad, motivo, estado, firma_colaborador, firma_jefe)
                        VALUES (:fecha_sol, :nombre, :dpto, :jefe, :tipo, :f_ini, :f_fin, :cant, :uni, :mot, 'Pendiente', :f_col, :f_jef);
                    ''')
                    conn.execute(insert_sol, {
                        "fecha_sol": str(fecha_solicitud),
                        "nombre": nombre.strip(),
                        "dpto": departamento,
                        "jefe": jefe.strip(),
                        "tipo": tipo_permiso,
                        "f_ini": str(fecha_inicio),
                        "f_fin": str(fecha_fin),
                        "cant": cantidad,
                        "uni": unidad,
                        "mot": motivo,
                        "f_col": "Sí" if firma_colab else "No",
                        "f_jef": "Sí" if firma_jefe else "No"
                    })
                st.cache_data.clear()
                st.success("✅ Solicitud guardada con éxito en la base de datos.")

# --- OPCIÓN 2: GESTIÓN DE PERSONAL ---
elif opcion == "👤 Gestión de Personal":
    st.subheader("Catálogo de Colaboradores Registrados")
    st.caption("Los colaboradores guardados aquí se autocompletan en el formulario.")

    df_emp = pd.read_sql_query("SELECT * FROM empleados ORDER BY nombre_colaborador ASC", engine)

    if not df_emp.empty:
        st.dataframe(df_emp[["id", "nombre_colaborador", "departamento", "jefe_inmediato"]], use_container_width=True)
    else:
        st.info("No hay colaboradores registrados aún.")

    with st.expander("➕ Registrar Nuevo Colaborador Manualmente"):
        with st.form("form_nuevo_emp", clear_on_submit=True):
            n_nombre = st.text_input("Nombre Completo")
            n_dpto = st.selectbox("Departamento / Área", DEPARTAMENTOS)
            n_jefe = st.text_input("Jefe Inmediato")
            btn_emp = st.form_submit_button("Guardar Personal")

            if btn_emp:
                if n_nombre.strip():
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                text("INSERT INTO empleados (nombre_colaborador, departamento, jefe_inmediato) VALUES (:n, :d, :j)"),
                                {"n": n_nombre.strip(), "d": n_dpto, "j": n_jefe.strip()}
                            )
                        st.cache_data.clear()
                        st.success(f"Colaborador {n_nombre} registrado correctamente.")
                        st.rerun()
                    except Exception:
                        st.error("El colaborador ya existe en la base de datos.")

# --- OPCIÓN 3: BASE DE DATOS Y GESTIÓN DE REGISTROS ---
elif opcion == "📊 Base de Datos":
    st.subheader("Histórico de Solicitudes")

    df = pd.read_sql_query("SELECT * FROM solicitudes ORDER BY id DESC", engine)

    if df.empty:
        st.info("No hay solicitudes registradas.")
    else:
        st.dataframe(df, use_container_width=True)
        st.markdown("---")
        
        tab_pdf, tab_editar, tab_eliminar = st.tabs(["📄 Generar PDF", "✏️ Modificar Registro", "🗑️ Eliminar Registro"])

        # TAB GENERAR PDF
        with tab_pdf:
            col_pdf1, col_pdf2 = st.columns([1, 2])
            with col_pdf1:
                id_pdf = st.selectbox("Selecciona el ID para PDF", df["id"].tolist(), key="sb_pdf")
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

        # TAB MODIFICAR REGISTRO
        with tab_editar:
            id_edit = st.selectbox("Selecciona el ID del registro a editar", df["id"].tolist(), key="sb_edit")
            registro = df[df["id"] == id_edit].iloc[0]

            tipos = ["Cita Médica", "Incapacidad", "Vacaciones", "Permiso Personal", "Duelo / Luto", "Maternidad/Paternidad", "Otro"]
            
            def safe_date(date_str):
                try:
                    return datetime.strptime(str(date_str), "%Y-%m-%d").date()
                except Exception:
                    return date.today()

            with st.form("form_editar_registro"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    e_nombre = st.text_input("Nombre Colaborador", value=registro["nombre_colaborador"])
                    e_dpto_idx = DEPARTAMENTOS.index(registro["departamento"]) if registro["departamento"] in DEPARTAMENTOS else 0
                    e_dpto = st.selectbox("Departamento / Área", DEPARTAMENTOS, index=e_dpto_idx)
                    e_jefe = st.text_input("Jefe Inmediato", value=registro["jefe_inmediato"])
                    e_estado = st.selectbox("Estado", ["Pendiente", "Aprobado", "Rechazado"], 
                                            index=["Pendiente", "Aprobado", "Rechazado"].index(registro["estado"]) if registro["estado"] in ["Pendiente", "Aprobado", "Rechazado"] else 0)

                with e_col2:
                    e_tipo_idx = tipos.index(registro["tipo_permiso"]) if registro["tipo_permiso"] in tipos else 0
                    e_tipo = st.selectbox("Tipo de Permiso", tipos, index=e_tipo_idx)
                    e_unidad = st.radio("Unidad", ["Días", "Horas"], index=0 if registro["unidad"] == "Días" else 1, horizontal=True)
                    e_f_inicio = st.date_input("Fecha Inicio", safe_date(registro["fecha_inicio"]))
                    e_f_fin = st.date_input("Fecha Fin", safe_date(registro["fecha_fin"]))
                    e_cantidad = st.number_input("Cantidad", value=float(registro["cantidad"]), min_value=0.5, step=0.5)

                e_motivo = st.text_area("Motivo", value=str(registro["motivo"]))

                btn_guardar_edit = st.form_submit_button("💾 Guardar Cambios")

                if btn_guardar_edit:
                    with engine.begin() as conn:
                        conn.execute(text('''
                            UPDATE solicitudes SET
                                nombre_colaborador = :nombre, departamento = :dpto, jefe_inmediato = :jefe,
                                tipo_permiso = :tipo, fecha_inicio = :f_ini, fecha_fin = :f_fin,
                                cantidad = :cant, unidad = :uni, motivo = :mot, estado = :estado
                            WHERE id = :id
                        '''), {
                            "nombre": e_nombre, "dpto": e_dpto, "jefe": e_jefe,
                            "tipo": e_tipo, "f_ini": str(e_f_inicio), "f_fin": str(e_f_fin),
                            "cant": e_cantidad, "uni": e_unidad, "mot": e_motivo,
                            "estado": e_estado, "id": id_edit
                        })
                    st.cache_data.clear()
                    st.success(f"✅ Registro #{id_edit} actualizado en la base de datos.")
                    st.rerun()

        # TAB ELIMINAR REGISTRO
        with tab_eliminar:
            st.warning("⚠️ La eliminación borra permanentemente el registro de la base de datos PostgreSQL.")
            id_del = st.selectbox("Selecciona el ID del registro a eliminar", df["id"].tolist(), key="sb_del")
            registro_del = df[df["id"] == id_del].iloc[0]
            st.write(f"**Colaborador:** {registro_del['nombre_colaborador']} | **Tipo:** {registro_del['tipo_permiso']} | **Inicio:** {registro_del['fecha_inicio']}")

            col_del1, col_del2 = st.columns(2)
            with col_del1:
                if st.button("🗑️ Eliminar Registro", type="primary"):
                    with engine.begin() as conn:
                        # 1. Eliminar la solicitud seleccionada
                        conn.execute(text("DELETE FROM solicitudes WHERE id = :id"), {"id": id_del})
                        
                        # 2. Reajuste seguro de la secuencia
                        conn.execute(text("""
                            DO $$
                            DECLARE
                                max_id INT;
                                seq_name TEXT;
                            BEGIN
                                SELECT pg_get_serial_sequence('solicitudes', 'id') INTO seq_name;
                                SELECT MAX(id) INTO max_id FROM solicitudes;
                                IF max_id IS NULL THEN
                                    EXECUTE format('SELECT setval(%L, 1, false)', seq_name);
                                ELSE
                                    EXECUTE format('SELECT setval(%L, %s)', seq_name, max_id);
                                END IF;
                            END $$;
                        """))
                    
                    st.cache_data.clear()
                    st.success(f"❌ Registro #{id_del} eliminado y correlativo ajustado.")
                    st.rerun()

            with col_del2:
                if st.button("🔄 Renumerar Folios Consecutivos"):
                    with engine.begin() as conn:
                        # 1. Reordena e iguala los IDs existentes (1, 2, 3...) sin dejar huecos
                        conn.execute(text("""
                            WITH renumerado AS (
                                SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS nuevo_id
                                FROM solicitudes
                            )
                            UPDATE solicitudes
                            SET id = renumerado.nuevo_id
                            FROM renumerado
                            WHERE solicitudes.id = renumerado.id;
                        """))
                        
                        # 2. Reajuste seguro de la secuencia
                        conn.execute(text("""
                            DO $$
                            DECLARE
                                max_id INT;
                                seq_name TEXT;
                            BEGIN
                                SELECT pg_get_serial_sequence('solicitudes', 'id') INTO seq_name;
                                SELECT MAX(id) INTO max_id FROM solicitudes;
                                IF max_id IS NULL THEN
                                    EXECUTE format('SELECT setval(%L, 1, false)', seq_name);
                                ELSE
                                    EXECUTE format('SELECT setval(%L, %s)', seq_name, max_id);
                                END IF;
                            END $$;
                        """))
                    st.cache_data.clear()
                    st.success("✅ Todos los folios han sido renumerados en orden consecutivo.")
                    st.rerun()

# --- OPCIÓN 4: MÉTRICAS ---
elif opcion == "📈 Métricas":
    st.subheader("Métricas de Gestión - SOLIDARISTAS")
    df = pd.read_sql_query("SELECT * FROM solicitudes", engine)

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
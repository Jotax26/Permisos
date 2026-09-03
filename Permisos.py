import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from fpdf import FPDF
from sqlalchemy import create_engine, text

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
# 2. GENERADOR DE PDF CON MARCA SOLIDARISTAS
# -----------------------------------------------------------
class SolicitudPDF(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path

    def header(self):
        self.set_fill_color(26, 54, 93)
        self.rect(0, 0, 210, 28, 'F')
        
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
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(100, 6, f"Folio N°: #{datos['id']}")
    
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

    def crear_seccion(titulo):
        pdf.set_fill_color(237, 242, 247)
        pdf.set_text_color(26, 54, 93)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, f"  {titulo}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

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

    crear_seccion("3. MOTIVO Y JUSTIFICACIÓN")
    pdf.set_font("Helvetica", "I", 9)
    motivo_text = str(datos['motivo']) if datos['motivo'] else "Sin justificación adicional especificada."
    pdf.multi_cell(0, 5, motivo_text, border=1)
    pdf.ln(8)

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
# 3. INTERFAZ EN STREAMLIT
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

# -----------------------------------------------------------
# OPCIÓN 1: NUEVA SOLICITUD
# -----------------------------------------------------------
if opcion == "➕ Nueva Solicitud":
    st.subheader("Formulario de Solicitud")

    empleados_df = pd.read_sql_query("SELECT * FROM empleados ORDER BY nombre_colaborador ASC", engine)

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
                st.success("✅ Solicitud guardada con éxito en Neon PostgreSQL.")

# -----------------------------------------------------------
# OPCIÓN 2: GESTIÓN DE PERSONAL
# -----------------------------------------------------------
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
            n_dpto = st.selectbox("Departamento", ["Operaciones", "Tecnología", "Finanzas", "Talento Humano", "Ventas", "Logística"])
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
                        st.success(f"Colaborador {n_nombre} registrado correctamente.")
                        st.rerun()
                    except Exception:
                        st.error("El colaborador ya existe en la base de datos.")

# -----------------------------------------------------------
# OPCIÓN 3: BASE DE DATOS, EDICIÓN, ELIMINACIÓN Y PDF
# -----------------------------------------------------------
elif opcion == "📊 Base de Datos":
    st.subheader("Histórico de Solicitudes")

    df = pd.read_sql_query("SELECT * FROM solicitudes ORDER BY id DESC", engine)

    if df.empty:
        st.info("No hay solicitudes registradas.")
    else:
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        
        # Pestañas para organizar la Edición, Eliminación y PDF
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

            dptos = ["Operaciones", "Tecnología", "Finanzas", "Talento Humano", "Ventas", "Logística"]
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
                    e_dpto_idx = dptos.index(registro["departamento"]) if registro["departamento"] in dptos else 0
                    e_dpto = st.selectbox("Departamento", dptos, index=e_dpto_idx)
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
                        update_query = text('''
                            UPDATE solicitudes SET
                                nombre_colaborador = :nombre,
                                departamento = :dpto,
                                jefe_inmediato = :jefe,
                                tipo_permiso = :tipo,
                                fecha_inicio = :f_ini,
                                fecha_fin = :f_fin,
                                cantidad = :cant,
                                unidad = :uni,
                                motivo = :mot,
                                estado = :estado
                            WHERE id = :id
                        ''')
                        conn.execute(update_query, {
                            "nombre": e_nombre, "dpto": e_dpto, "jefe": e_jefe,
                            "tipo": e_tipo, "f_ini": str(e_f_inicio), "f_fin": str(e_f_fin),
                            "cant": e_cantidad, "uni": e_unidad, "mot": e_motivo,
                            "estado": e_estado, "id": id_edit
                        })
                    st.success(f"✅ Permiso #{id_edit} actualizado con éxito.")
                    st.rerun()

        # TAB ELIMINAR REGISTRO
        with tab_eliminar:
            st.warning("⚠️ La eliminación es permanente y borrará el registro de la base de datos.")
            id_del = st.selectbox("Selecciona el ID del registro a eliminar", df["id"].tolist(), key="sb_del")
            
            registro_del = df[df["id"] == id_del].iloc[0]
            st.write(f"**Colaborador:** {registro_del['nombre_colaborador']} | **Tipo:** {registro_del['tipo_permiso']} | **Inicio:** {registro_del['fecha_inicio']}")

            if st.button("🗑️ Eliminar Definitivamente", type="primary"):
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM solicitudes WHERE id = :id"), {"id": id_del})
                st.success(f"❌ Registro #{id_del} eliminado correctamente.")
                st.rerun()

# -----------------------------------------------------------
# OPCIÓN 4: MÉTRICAS
# -----------------------------------------------------------
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
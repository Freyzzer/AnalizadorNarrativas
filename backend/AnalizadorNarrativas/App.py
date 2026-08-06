"""
Analizador de narrativas — prototipo Streamlit.

Corre con:  streamlit run app.py
Requiere:   GEMINI_API_KEY configurada como variable de entorno.
"""

import streamlit as st
import db
import llm

st.set_page_config(page_title="Analizador de narrativas", page_icon="📖", layout="wide")
db.init_db()


def analizar_y_guardar_capitulo(obra_id: int, capitulo_id: int, numero_cap: int, texto: str):
    """
    Corre el pipeline completo (extracción + registro de hechos + análisis narrativo)
    sobre un capítulo ya guardado en la base de datos, y persiste los resultados.
    Se usa tanto para un capítulo nuevo como para re-analizar uno existente
    (por ejemplo, después de editarlo).
    Devuelve (analisis: dict, nuevas_inconsistencias: list[str]).
    """
    estructura = llm.extraer_estructura(texto)

    for p in estructura.get("personajes", []):
        db.upsert_personaje(obra_id, p["nombre"], p["descripcion"], numero_cap, capitulo_id)

    nuevas_inconsistencias = []
    for h in estructura.get("hechos_continuidad", []):
        resultado = db.registrar_hecho(
            obra_id, h["entidad"], h["atributo"], h["valor"], capitulo_id, numero_cap
        )
        if resultado:
            nuevas_inconsistencias.append(resultado)

    resumen_bible = db.story_bible_resumen(obra_id)
    analisis = llm.analizar_capitulo(texto, resumen_bible)
    db.save_analisis(capitulo_id, analisis)

    return analisis, nuevas_inconsistencias


def mostrar_reporte_analisis(analisis: dict):
    st.markdown(f"**Resumen general:** {analisis.get('resumen_general', '—')}")
    for seccion, etiqueta in [
        ("personajes", "🧑 Personajes"),
        ("trama_y_ritmo", "📈 Trama y ritmo"),
        ("prosa_y_estilo", "🖋️ Prosa y estilo"),
        ("dialogo", "💬 Diálogo"),
    ]:
        datos = analisis.get(seccion, {})
        with st.expander(etiqueta, expanded=True):
            st.markdown(f"**Fortalezas:** {datos.get('fortalezas', '—')}")
            st.markdown(f"**Problemas:** {datos.get('problemas', '—')}")
            st.markdown(f"**Sugerencias:** {datos.get('sugerencias', '—')}")
            ejemplos = datos.get("ejemplos_mostrar_no_contar")
            if ejemplos:
                st.markdown("**Ejemplos de 'contar' en vez de 'mostrar':**")
                for ej in ejemplos:
                    st.markdown(f"> {ej}")

# ---------------- Sidebar: selección/creación de obra ----------------

st.sidebar.title("📖 Tus obras")

obras = db.list_obras()
opciones = {f'{o["titulo"]} ({o["genero"] or "sin género"})': o["id"] for o in obras}

with st.sidebar.expander("➕ Crear nueva obra"):
    nuevo_titulo = st.text_input("Título", key="nuevo_titulo")
    nuevo_genero = st.text_input("Género (opcional)", key="nuevo_genero")
    if st.button("Crear obra"):
        if nuevo_titulo.strip():
            db.create_obra(nuevo_titulo.strip(), nuevo_genero.strip())
            st.rerun()
        else:
            st.warning("Ponle un título a tu obra.")

if not opciones:
    st.info("Crea tu primera obra desde la barra lateral para empezar.")
    st.stop()

seleccion = st.sidebar.selectbox("Obra activa", list(opciones.keys()))
obra_id = opciones[seleccion]

# ---------------- Tabs principales ----------------

tab_nuevo, tab_bible, tab_inconsist, tab_chat = st.tabs(
    ["✍️ Nuevo capítulo", "📚 Story bible", "⚠️ Inconsistencias", "💬 Chat sobre tu historia"]
)

# ---------------- Tab: nuevo capítulo ----------------

with tab_nuevo:
    st.subheader("Analiza un capítulo nuevo")

    ultimo_num = db.get_ultimo_numero_capitulo(obra_id)
    col1, col2 = st.columns([1, 3])
    with col1:
        numero_cap = st.number_input("Número de capítulo", min_value=1, value=ultimo_num + 1)
    with col2:
        titulo_cap = st.text_input("Título del capítulo (opcional)")

    texto = st.text_area("Pega o escribe el capítulo aquí", height=350)

    if st.button("Analizar capítulo", type="primary"):
        if not texto.strip():
            st.warning("Escribe o pega el texto del capítulo primero.")
        else:
            with st.spinner("Extrayendo personajes, hechos de continuidad y analizando..."):
                try:
                    capitulo_id = db.add_capitulo(obra_id, int(numero_cap), texto, titulo_cap)
                    analisis, nuevas_inconsistencias = analizar_y_guardar_capitulo(
                        obra_id, capitulo_id, int(numero_cap), texto
                    )
                except Exception as e:
                    st.error(f"Error al analizar el capítulo: {e}")
                    st.stop()

            if nuevas_inconsistencias:
                st.warning("⚠️ Se detectaron posibles inconsistencias de continuidad:")
                for inc in nuevas_inconsistencias:
                    st.write(f"- {inc}")

            st.success("Análisis completo.")
            mostrar_reporte_analisis(analisis)

    st.divider()
    st.subheader("Capítulos ya analizados")
    capitulos = db.list_capitulos(obra_id)

    for c in capitulos:
        cid = c["id"]
        editando_key = f"editando_{cid}"
        confirmar_key = f"confirmar_borrar_{cid}"

        with st.expander(f'Capítulo {c["numero"]}{" — " + c["titulo"] if c["titulo"] else ""}'):

            # ---- Modo edición ----
            if st.session_state.get(editando_key):
                nuevo_titulo = st.text_input("Título", value=c["titulo"] or "", key=f"titulo_edit_{cid}")
                nuevo_texto = st.text_area("Texto", value=c["texto"], height=250, key=f"texto_edit_{cid}")
                col_guardar, col_cancelar = st.columns(2)
                with col_guardar:
                    if st.button("💾 Guardar cambios", key=f"guardar_{cid}"):
                        db.update_capitulo(cid, nuevo_texto, nuevo_titulo)
                        st.session_state[editando_key] = False
                        st.info(
                            "Texto actualizado. El análisis y la story bible siguen reflejando "
                            "la versión anterior — usa '🔁 Re-analizar' si quieres que se actualicen."
                        )
                        st.rerun()
                with col_cancelar:
                    if st.button("Cancelar", key=f"cancelar_edit_{cid}"):
                        st.session_state[editando_key] = False
                        st.rerun()
                continue  # no mostrar el resto de controles mientras se edita

            # ---- Modo lectura ----
            analisis_previo = db.get_analisis(cid)
            if analisis_previo:
                st.markdown(f"**Resumen:** {analisis_previo.get('resumen_general', '—')}")
            else:
                st.caption("Sin análisis guardado.")
            st.text_area("Texto", c["texto"], height=150, key=f"cap_{cid}", disabled=True)

            col_editar, col_reanalizar, col_eliminar = st.columns(3)

            with col_editar:
                if st.button("✏️ Editar", key=f"editar_{cid}"):
                    st.session_state[editando_key] = True
                    st.rerun()

            with col_reanalizar:
                if st.button("🔁 Re-analizar", key=f"reanalizar_{cid}"):
                    with st.spinner("Re-analizando este capítulo..."):
                        try:
                            db.limpiar_datos_generados_capitulo(cid)
                            analisis, nuevas_inc = analizar_y_guardar_capitulo(
                                obra_id, cid, c["numero"], c["texto"]
                            )
                        except Exception as e:
                            st.error(f"Error al re-analizar: {e}")
                            st.stop()
                    if nuevas_inc:
                        st.warning("⚠️ Inconsistencias detectadas al re-analizar:")
                        for inc in nuevas_inc:
                            st.write(f"- {inc}")
                    st.success("Capítulo re-analizado.")
                    st.rerun()

            with col_eliminar:
                if not st.session_state.get(confirmar_key):
                    if st.button("🗑️ Eliminar", key=f"eliminar_{cid}"):
                        st.session_state[confirmar_key] = True
                        st.rerun()

            if st.session_state.get(confirmar_key):
                st.error(
                    f'¿Eliminar el capítulo {c["numero"]} permanentemente? '
                    "También se borrarán los hechos de continuidad y el análisis asociados a él. "
                    "Esta acción no se puede deshacer."
                )
                col_si, col_no = st.columns(2)
                with col_si:
                    if st.button("Sí, eliminar definitivamente", key=f"confirmar_si_{cid}"):
                        db.delete_capitulo(cid)
                        st.session_state[confirmar_key] = False
                        st.rerun()
                with col_no:
                    if st.button("Cancelar", key=f"confirmar_no_{cid}"):
                        st.session_state[confirmar_key] = False
                        st.rerun()

# ---------------- Tab: story bible ----------------

with tab_bible:
    st.subheader("Personajes establecidos")
    personajes = db.list_personajes(obra_id)
    if not personajes:
        st.info("Todavía no hay personajes registrados. Analiza tu primer capítulo.")
    for p in personajes:
        st.markdown(f'**{p["nombre"]}** _(desde el capítulo {p["primera_aparicion_cap"]})_')
        st.markdown(f'**Estado actual:** {p["descripcion_actual"]}')

        historial = db.get_historial_personaje(p["id"])
        if len(historial) > 1:
            with st.expander(f"📈 Ver evolución ({len(historial)} apariciones)"):
                for h in historial:
                    etiqueta_cap = f'Capítulo {h["capitulo_numero"]}'
                    if h["capitulo_titulo"]:
                        etiqueta_cap += f' — {h["capitulo_titulo"]}'
                    st.markdown(f"**{etiqueta_cap}:** {h['descripcion']}")
        st.divider()

# ---------------- Tab: inconsistencias ----------------

with tab_inconsist:
    st.subheader("Inconsistencias detectadas")
    inconsistencias = db.list_inconsistencias(obra_id)
    if not inconsistencias:
        st.success("No se han detectado inconsistencias de continuidad todavía. 🎉")
    for inc in inconsistencias:
        st.warning(inc["descripcion"])

# ---------------- Tab: chat ----------------

with tab_chat:
    st.subheader("Pregúntale a tu historia")
    st.caption(
        "Ejemplos: '¿qué personajes no he desarrollado en los últimos capítulos?', "
        "'recuérdame qué establecí sobre X personaje'"
    )

    pregunta = st.text_input("Tu pregunta")
    if st.button("Preguntar"):
        if not pregunta.strip():
            st.warning("Escribe una pregunta primero.")
        else:
            with st.spinner("Pensando..."):
                resumen_bible = db.story_bible_resumen(obra_id)
                capitulos = db.list_capitulos(obra_id)
                recientes = "\n\n".join(
                    f'Capítulo {c["numero"]}:\n{c["texto"]}' for c in capitulos[-3:]
                )
                try:
                    respuesta = llm.preguntar_sobre_historia(pregunta, resumen_bible, recientes)
                    st.markdown(respuesta)
                except Exception as e:
                    st.error(f"Error: {e}")
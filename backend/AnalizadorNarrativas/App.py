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


def analizar_y_guardar_capitulo(obra_id: int, capitulo_id: int, numero_cap: int, texto: str, genero: str,
                                 forzar: bool = False):
    """
    Corre el pipeline completo (extracción + registro de hechos + análisis narrativo)
    sobre un capítulo ya guardado en la base de datos, y persiste los resultados.
    Se usa tanto para un capítulo nuevo como para re-analizar uno existente
    (por ejemplo, después de editarlo). `genero` determina qué prompts y qué
    esquema de análisis se usan (ver llm.GENEROS).
    `forzar=True` ignora la caché de respuestas de Gemini y vuelve a llamar al
    modelo aunque ya exista una respuesta guardada para este mismo texto+prompt
    (se usa en "🔁 Re-analizar", para que un reintento explícito nunca devuelva
    silenciosamente el resultado viejo).
    Devuelve (analisis: dict, nuevas_inconsistencias: list[str], desde_cache: bool).
    """
    estructura = llm.extraer_estructura(texto, genero, forzar=forzar)

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
    analisis = llm.analizar_capitulo(texto, resumen_bible, genero, forzar=forzar)
    desde_cache = llm.ultima_fue_cache  # refleja la llamada de análisis, la más relevante para el usuario
    db.save_analisis(capitulo_id, analisis)

    return analisis, nuevas_inconsistencias, desde_cache


def mostrar_reporte_analisis(analisis: dict, genero: str):
    st.markdown(f"**Resumen general:** {analisis.get('resumen_general', '—')}")
    secciones = llm.ANALYSIS_SECCIONES.get(genero, llm.ANALYSIS_SECCIONES[llm.DEFAULT_GENERO])
    for seccion in secciones:
        datos = analisis.get(seccion["key"], {})
        with st.expander(seccion["label"], expanded=True):
            st.markdown(f"**Fortalezas:** {datos.get('fortalezas', '—')}")
            st.markdown(f"**Problemas:** {datos.get('problemas', '—')}")
            st.markdown(f"**Sugerencias:** {datos.get('sugerencias', '—')}")
            ejemplos_key = seccion.get("ejemplos_key")
            if ejemplos_key:
                ejemplos = datos.get(ejemplos_key)
                if ejemplos:
                    st.markdown(f"**{seccion.get('ejemplos_label', 'Ejemplos')}:**")
                    for ej in ejemplos:
                        st.markdown(f"> {ej}")

# ---------------- Sidebar: selección/creación de obra ----------------

st.sidebar.title("📖 Tus obras")

obras = db.list_obras()
opciones = {
    f'{o["titulo"]} ({llm.GENEROS.get(o["genero"], {}).get("label", o["genero"] or "sin género")})': o["id"]
    for o in obras
}

with st.sidebar.expander("➕ Crear nueva obra"):
    nuevo_titulo = st.text_input("Título", key="nuevo_titulo")
    nuevo_genero_label = st.selectbox(
        "Género literario",
        options=list(llm.GENEROS.keys()),
        format_func=lambda k: llm.GENEROS[k]["label"],
        key="nuevo_genero",
        help="Cada género tiene su propio criterio de análisis (por ejemplo, un poema no se evalúa "
             "por su 'diálogo' ni una obra de teatro por su 'musicalidad').",
    )
    st.caption(llm.GENEROS[nuevo_genero_label]["descripcion"])
    if st.button("Crear obra"):
        if nuevo_titulo.strip():
            db.create_obra(nuevo_titulo.strip(), nuevo_genero_label)
            st.rerun()
        else:
            st.warning("Ponle un título a tu obra.")

if not opciones:
    st.info("Crea tu primera obra desde la barra lateral para empezar.")
    st.stop()

seleccion = st.sidebar.selectbox("Obra activa", list(opciones.keys()))
obra_id = opciones[seleccion]

with st.sidebar.expander("🗄️ Caché de respuestas de la IA"):
    n_cache = db.cache_count()
    st.caption(
        f"{n_cache} respuesta(s) guardada(s). Si vuelves a analizar el mismo texto o le "
        "haces al chat la misma pregunta con el mismo contexto, se reutiliza la respuesta "
        "en vez de volver a llamar a Gemini."
    )
    if st.button("🗑️ Vaciar caché"):
        db.cache_clear()
        st.rerun()

obra_actual = db.get_obra(obra_id)
genero_actual = obra_actual["genero"] if obra_actual and obra_actual["genero"] in llm.GENEROS else llm.DEFAULT_GENERO
config_genero = llm.GENEROS[genero_actual]
unidad = config_genero["unidad"]
unidad_articulo = config_genero["unidad_articulo"]

# ---------------- Tabs principales ----------------

tab_nuevo, tab_bible, tab_inconsist, tab_chat = st.tabs(
    [f"✍️ Nuevo {unidad}", "📚 Story bible", "⚠️ Inconsistencias", "💬 Chat sobre tu obra"]
)

# ---------------- Tab: nuevo capítulo/unidad ----------------

with tab_nuevo:
    st.subheader(f"Analiza {unidad_articulo} {unidad} nuevo/a")
    st.caption(f"Género literario de esta obra: {config_genero['label']} — {config_genero['descripcion']}")

    ultimo_num = db.get_ultimo_numero_capitulo(obra_id)
    col1, col2 = st.columns([1, 3])
    with col1:
        numero_cap = st.number_input(f"Número de {unidad}", min_value=1, value=ultimo_num + 1)
    with col2:
        titulo_cap = st.text_input(f"Título de {unidad_articulo} {unidad} (opcional)")

    texto = st.text_area(f"Pega o escribe {unidad_articulo} {unidad} aquí", height=350)

    if st.button("Analizar", type="primary"):
        if not texto.strip():
            st.warning(f"Escribe o pega el texto de {unidad_articulo} {unidad} primero.")
        else:
            with st.spinner("Extrayendo elementos clave y analizando..."):
                try:
                    capitulo_id = db.add_capitulo(obra_id, int(numero_cap), texto, titulo_cap)
                    analisis, nuevas_inconsistencias, desde_cache = analizar_y_guardar_capitulo(
                        obra_id, capitulo_id, int(numero_cap), texto, genero_actual
                    )
                except Exception as e:
                    st.error(f"Error al analizar: {e}")
                    st.stop()

            if nuevas_inconsistencias:
                st.warning("⚠️ Se detectaron posibles inconsistencias de continuidad:")
                for inc in nuevas_inconsistencias:
                    st.write(f"- {inc}")

            if desde_cache:
                st.caption("⚡ Este análisis ya se había pedido antes con el mismo texto — se sirvió "
                           "desde la caché, sin llamar a la IA.")
            st.success("Análisis completo.")
            mostrar_reporte_analisis(analisis, genero_actual)

    st.divider()
    st.subheader(f"{unidad.capitalize()}s ya analizados")
    capitulos = db.list_capitulos(obra_id)

    for c in capitulos:
        cid = c["id"]
        editando_key = f"editando_{cid}"
        confirmar_key = f"confirmar_borrar_{cid}"

        with st.expander(f'{unidad.capitalize()} {c["numero"]}{" — " + c["titulo"] if c["titulo"] else ""}'):

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
                    with st.spinner("Re-analizando..."):
                        try:
                            db.limpiar_datos_generados_capitulo(cid)
                            analisis, nuevas_inc, _ = analizar_y_guardar_capitulo(
                                obra_id, cid, c["numero"], c["texto"], genero_actual, forzar=True
                            )
                        except Exception as e:
                            st.error(f"Error al re-analizar: {e}")
                            st.stop()
                    if nuevas_inc:
                        st.warning("⚠️ Inconsistencias detectadas al re-analizar:")
                        for inc in nuevas_inc:
                            st.write(f"- {inc}")
                    st.success(f"{unidad.capitalize()} re-analizado/a.")
                    st.rerun()

            with col_eliminar:
                if not st.session_state.get(confirmar_key):
                    if st.button("🗑️ Eliminar", key=f"eliminar_{cid}"):
                        st.session_state[confirmar_key] = True
                        st.rerun()

            if st.session_state.get(confirmar_key):
                st.error(
                    f'¿Eliminar {unidad_articulo} {unidad} {c["numero"]} permanentemente? '
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
    st.subheader(config_genero["entidad_label"])
    personajes = db.list_personajes(obra_id)
    if not personajes:
        st.info(f"Todavía no hay nada registrado. Analiza tu primer {unidad}.")
    for p in personajes:
        st.markdown(f'**{p["nombre"]}** _(desde el {unidad} {p["primera_aparicion_cap"]})_')
        st.markdown(f'**Estado actual:** {p["descripcion_actual"]}')

        historial = db.get_historial_personaje(p["id"])
        if len(historial) > 1:
            with st.expander(f"📈 Ver evolución ({len(historial)} apariciones)"):
                for h in historial:
                    etiqueta_cap = f'{unidad.capitalize()} {h["capitulo_numero"]}'
                    if h["capitulo_titulo"]:
                        etiqueta_cap += f' — {h["capitulo_titulo"]}'
                    st.markdown(f"**{etiqueta_cap}:** {h['descripcion']}")
        st.divider()

# ---------------- Tab: inconsistencias ----------------

with tab_inconsist:
    st.subheader("Inconsistencias detectadas")
    todas = db.list_inconsistencias(obra_id)

    if not todas:
        st.success("No se han detectado inconsistencias de continuidad todavía. 🎉")
    else:
        etiquetas_estado = {
            "pendiente": "🔴 Pendiente",
            "intencional": "🟡 Intencional",
            "resuelta": "🟢 Resuelta",
        }

        conteo = {estado: 0 for estado in db.ESTADOS_INCONSISTENCIA}
        for inc in todas:
            conteo[inc["estado"]] = conteo.get(inc["estado"], 0) + 1

        col1, col2, col3 = st.columns(3)
        col1.metric("🔴 Pendientes", conteo["pendiente"])
        col2.metric("🟡 Intencionales", conteo["intencional"])
        col3.metric("🟢 Resueltas", conteo["resuelta"])

        filtro = st.radio(
            "Mostrar", ["Todas", "Pendientes", "Intencionales", "Resueltas"], horizontal=True
        )
        mapa_filtro = {
            "Todas": None,
            "Pendientes": "pendiente",
            "Intencionales": "intencional",
            "Resueltas": "resuelta",
        }
        mostrar = [
            inc for inc in todas
            if mapa_filtro[filtro] is None or inc["estado"] == mapa_filtro[filtro]
        ]

        if not mostrar:
            st.caption("No hay inconsistencias en esta categoría.")

        for inc in mostrar:
            with st.container(border=True):
                st.markdown(inc["descripcion"])
                nuevo_estado = st.selectbox(
                    "Estado",
                    db.ESTADOS_INCONSISTENCIA,
                    index=db.ESTADOS_INCONSISTENCIA.index(inc["estado"]),
                    format_func=lambda e: etiquetas_estado[e],
                    key=f"estado_inc_{inc['id']}",
                    label_visibility="collapsed",
                )
                if nuevo_estado != inc["estado"]:
                    db.actualizar_estado_inconsistencia(inc["id"], nuevo_estado)
                    st.rerun()

# ---------------- Tab: chat ----------------

with tab_chat:
    st.subheader("Pregúntale a tu obra")
    st.caption(
        "Ejemplos: '¿qué elementos no he desarrollado en los últimos fragmentos?', "
        "'recuérdame qué establecí sobre X'"
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
                    f'{unidad.capitalize()} {c["numero"]}:\n{c["texto"]}' for c in capitulos[-3:]
                )
                try:
                    respuesta = llm.preguntar_sobre_historia(pregunta, resumen_bible, recientes, genero_actual)
                    if llm.ultima_fue_cache:
                        st.caption("⚡ Ya habías hecho esta misma pregunta con este mismo contexto — "
                                   "respuesta servida desde caché.")
                    st.markdown(respuesta)
                except Exception as e:
                    st.error(f"Error: {e}")
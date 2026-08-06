"""
Analizador de narrativas — prototipo Streamlit.

Corre con:  streamlit run app.py
Requiere:   GEMINI_API_KEY configurada como variable de entorno.
"""

import streamlit as st
import Db as db
import Llm as llm

st.set_page_config(page_title="Analizador de narrativas", page_icon="📖", layout="wide")
db.init_db()

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
            with st.spinner("Extrayendo personajes y hechos de continuidad..."):
                try:
                    estructura = llm.extraer_estructura(texto)
                except Exception as e:
                    st.error(f"Error al extraer la estructura: {e}")
                    st.stop()

            capitulo_id = db.add_capitulo(obra_id, int(numero_cap), texto, titulo_cap)

            for p in estructura.get("personajes", []):
                db.upsert_personaje(obra_id, p["nombre"], p["descripcion"], int(numero_cap))

            nuevas_inconsistencias = []
            for h in estructura.get("hechos_continuidad", []):
                resultado = db.registrar_hecho(
                    obra_id, h["entidad"], h["atributo"], h["valor"], capitulo_id, int(numero_cap)
                )
                if resultado:
                    nuevas_inconsistencias.append(resultado)

            if nuevas_inconsistencias:
                st.warning("⚠️ Se detectaron posibles inconsistencias de continuidad:")
                for inc in nuevas_inconsistencias:
                    st.write(f"- {inc}")

            with st.spinner("Analizando trama, personajes y prosa..."):
                try:
                    resumen_bible = db.story_bible_resumen(obra_id)
                    analisis = llm.analizar_capitulo(texto, resumen_bible)
                    db.save_analisis(capitulo_id, analisis)
                except Exception as e:
                    st.error(f"Error al analizar el capítulo: {e}")
                    st.stop()

            st.success("Análisis completo.")
            st.markdown(f"**Resumen general:** {analisis['resumen_general']}")

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

    st.divider()
    st.subheader("Capítulos ya analizados")
    capitulos = db.list_capitulos(obra_id)
    for c in capitulos:
        with st.expander(f'Capítulo {c["numero"]}{" — " + c["titulo"] if c["titulo"] else ""}'):
            analisis_previo = db.get_analisis(c["id"])
            if analisis_previo:
                st.markdown(f"**Resumen:** {analisis_previo['resumen_general']}")
            else:
                st.caption("Sin análisis guardado.")
            st.text_area("Texto", c["texto"], height=150, key=f"cap_{c['id']}", disabled=True)

# ---------------- Tab: story bible ----------------

with tab_bible:
    st.subheader("Personajes establecidos")
    personajes = db.list_personajes(obra_id)
    if not personajes:
        st.info("Todavía no hay personajes registrados. Analiza tu primer capítulo.")
    for p in personajes:
        st.markdown(f'**{p["nombre"]}** _(desde el capítulo {p["primera_aparicion_cap"]})_')
        st.markdown(p["descripcion_actual"])
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


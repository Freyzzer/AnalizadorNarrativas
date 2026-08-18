from utils.html import html_a_texto


def test_html_a_texto_plano():
    assert html_a_texto("Hola mundo") == "Hola mundo"


def test_html_a_texto_con_etiquetas():
    assert html_a_texto("<p>Hola</p><p>Mundo</p>") == "Hola\nMundo"
    assert html_a_texto("Línea<br>salto") == "Línea\nsalto"


def test_html_a_texto_vacio_y_espaciado():
    assert html_a_texto("") == ""
    assert html_a_texto(None) == ""
    assert html_a_texto("<div>\n\n\n\n</div><div>x</div>") == "x"


def test_html_a_texto_sin_html():
    assert html_a_texto("texto < sin etiqueta") == "texto < sin etiqueta"

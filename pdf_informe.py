"""Informe en PDF del ejercicio resuelto (sin dependencias de Streamlit).

Reproduce lo que se ve en la página: datos del ejercicio, resultado, tabla de iteraciones,
desarrollo paso a paso (con las fórmulas dibujadas) y gráfica.
"""
import functools
import io
import os
import re
from datetime import datetime

import matplotlib
from matplotlib.mathtext import math_to_image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, Image, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

from presentacion import (
    Formato, construir_tablas, construir_tablas_secante, pasos_iteracion, pasos_iteracion_secante,
    pasos_prueba_error, pasos_prueba_error_secante,
)

# Paleta (la misma de la página)
AZUL = colors.HexColor("#1F4E79")
TEAL = colors.HexColor("#0F8B8D")
GRIS = colors.HexColor("#6B7785")
TEXTO = colors.HexColor("#1F2933")
FONDO = colors.HexColor("#F2F5F9")
BORDE = colors.HexColor("#D5DEE8")
RESALTE = colors.HexColor("#E3EEF6")

DPI_FORMULAS = 180
ESCALA_FORMULAS = 1.2      # 1.0 equivale a texto de 10 pt
MARGEN = 50
ANCHO_UTIL = letter[0] - 2 * MARGEN


# ----------------------------------------------------------------------
# Fuentes (DejaVu Sans viene con matplotlib y trae subíndices, flechas, etc.)
# ----------------------------------------------------------------------
def _registrar_fuentes():
    if "DV" in pdfmetrics.getRegisteredFontNames():
        return
    ruta = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
    for nombre, archivo in (("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"),
                            ("DV-I", "DejaVuSans-Oblique.ttf"), ("DV-BI", "DejaVuSans-BoldOblique.ttf")):
        pdfmetrics.registerFont(TTFont(nombre, os.path.join(ruta, archivo)))
    addMapping("DV", 0, 0, "DV")
    addMapping("DV", 1, 0, "DV-B")
    addMapping("DV", 0, 1, "DV-I")
    addMapping("DV", 1, 1, "DV-BI")


def _estilos():
    base = dict(fontName="DV", textColor=TEXTO, leading=13, fontSize=9.5)
    return {
        "titulo": ParagraphStyle("titulo", **{**base, "fontName": "DV-B", "fontSize": 22, "leading": 26,
                                              "textColor": AZUL}),
        "sub": ParagraphStyle("sub", **{**base, "fontSize": 9, "textColor": GRIS, "spaceAfter": 4}),
        "h2": ParagraphStyle("h2", **{**base, "fontName": "DV-B", "fontSize": 14, "leading": 18,
                                      "textColor": AZUL, "spaceBefore": 16, "spaceAfter": 6, "keepWithNext": 1}),
        "h3": ParagraphStyle("h3", **{**base, "fontName": "DV-B", "fontSize": 11.5, "leading": 15,
                                      "textColor": AZUL, "spaceBefore": 10, "spaceAfter": 4, "keepWithNext": 1}),
        "iter": ParagraphStyle("iter", **{**base, "fontName": "DV-B", "fontSize": 10.5, "leading": 14,
                                          "textColor": AZUL, "backColor": FONDO, "borderPadding": (4, 6, 4, 6),
                                          "spaceBefore": 14, "spaceAfter": 8, "keepWithNext": 1}),
        "paso": ParagraphStyle("paso", **{**base, "spaceBefore": 5, "spaceAfter": 2, "keepWithNext": 1}),
        "texto": ParagraphStyle("texto", **{**base, "spaceAfter": 3}),
        "pequeno": ParagraphStyle("pequeno", **{**base, "fontSize": 8, "leading": 10, "textColor": GRIS}),
        "etq": ParagraphStyle("etq", **{**base, "fontSize": 7.5, "leading": 9, "textColor": GRIS}),
        "valor": ParagraphStyle("valor", **{**base, "fontName": "DV-B", "fontSize": 14, "leading": 18,
                                            "textColor": AZUL}),
        "raiz": ParagraphStyle("raiz", **{**base, "fontName": "DV-B", "fontSize": 24, "leading": 28,
                                          "textColor": AZUL}),
        "centro": ParagraphStyle("centro", **{**base, "alignment": TA_CENTER}),
    }


# ----------------------------------------------------------------------
# Texto con formato (negritas **...** y matemática en línea $...$)
# ----------------------------------------------------------------------
def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_SIMBOLOS = ((r"\leftarrow", "←"), (r"\Rightarrow", "⇒"), (r"\cdot", "·"), (r"\times", "×"), (r"\approx", "≈"),
             (r"\geq", "≥"), (r"\neq", "≠"), (r"\qquad", "  "), (r"\,", " "), (r"\;", " "), (r"\%", "%"))


def _mate_en_linea(tex):
    t = tex.replace("{,}", ",")
    for a, b in _SIMBOLOS:
        t = t.replace(a, b)
    t = _esc(t)
    t = re.sub(r"_\{([^{}]*)\}", r"<sub>\1</sub>", t)
    t = re.sub(r"_([A-Za-z0-9])", r"<sub>\1</sub>", t)
    t = re.sub(r"\^\{([^{}]*)\}", r"<super>\1</super>", t)
    t = re.sub(r"\\[A-Za-z]+", "", t).replace("{", "").replace("}", "")
    return t


def _con_matematica(texto):
    salida, pos = [], 0
    for m in re.finditer(r"\$(.+?)\$", texto):
        salida.append(_esc(texto[pos:m.start()]))
        salida.append(_mate_en_linea(m.group(1)))
        pos = m.end()
    salida.append(_esc(texto[pos:]))
    return "".join(salida)


def _markdown_a_markup(texto):
    partes = texto.split("**")
    return "".join(f"<b>{_con_matematica(p)}</b>" if i % 2 else _con_matematica(p) for i, p in enumerate(partes))


# ----------------------------------------------------------------------
# Fórmulas (LaTeX -> imagen con el motor matemático de matplotlib)
# ----------------------------------------------------------------------
def _a_mathtext(tex):
    t = re.sub(r"\\text\{([^{}]*)\}", lambda m: r"\mathrm{" + m.group(1).replace(" ", r"\ ") + "}", tex)
    return t.replace(r"\;", r"\ ").replace(r"\operatorname{sen}", r"\mathrm{sen}")


@functools.lru_cache(maxsize=4096)
def _formula_png(tex):
    buf = io.BytesIO()
    math_to_image("$" + _a_mathtext(tex) + "$", buf, dpi=DPI_FORMULAS, format="png")
    return buf.getvalue()


def _dimensiones(tex):
    png = _formula_png(tex)
    ancho_px, alto_px = ImageReader(io.BytesIO(png)).getSize()
    return png, ancho_px * 72 / DPI_FORMULAS * ESCALA_FORMULAS, alto_px * 72 / DPI_FORMULAS * ESCALA_FORMULAS


def _imagen_formula(tex):
    """Imagen de la fórmula, reducida si es más ancha que la página."""
    png, ancho, alto = _dimensiones(tex)
    if ancho > ANCHO_UTIL:
        alto, ancho = alto * ANCHO_UTIL / ancho, ANCHO_UTIL
    img = Image(io.BytesIO(png), width=ancho, height=alto)
    img.hAlign = "CENTER"
    return img


def _formula(tex, estilos):
    """Fórmula centrada; si es muy ancha se parte en dos líneas en la flecha ⇒; si no se puede dibujar, texto."""
    try:
        _, ancho, _ = _dimensiones(tex)
        if ancho > ANCHO_UTIL and r"\Rightarrow" in tex:
            izquierda, derecha = tex.split(r"\Rightarrow", 1)
            izquierda = re.sub(r"(\\[;,]|\s)+$", "", izquierda)
            derecha = re.sub(r"^(\\[;,]|\s)+", "", derecha)
            filas = [[_imagen_formula(izquierda)], [_imagen_formula(r"\Rightarrow " + derecha)]]
            t = Table(filas, colWidths=[ANCHO_UTIL])
            t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
            return _con_espacio(t)
        return _con_espacio(_imagen_formula(tex))
    except Exception:
        plano = re.sub(r"\\[A-Za-z]+|[{}]", " ", tex)
        return Paragraph(_esc(plano), estilos["centro"])


def _con_espacio(flowable, arriba=3, abajo=5):
    t = Table([[flowable]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), arriba), ("BOTTOMPADDING", (0, 0), (-1, -1), abajo),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    return t


def _items_a_flowables(items, estilos):
    """Convierte la lista ('md'|'latex', texto) de presentacion.py en elementos del PDF."""
    out = []
    for tipo, texto in items:
        if tipo == "latex":
            out.append(_formula(texto, estilos))
        elif texto.startswith("### "):
            out.append(Paragraph(_esc(texto[4:]), estilos["h3"]))
        elif texto.startswith("**") and texto.endswith("**") and texto.count("**") == 2:
            out.append(Paragraph(_markdown_a_markup(texto), estilos["paso"]))
        else:
            out.append(Paragraph(_markdown_a_markup(texto), estilos["texto"]))
    return out


# ----------------------------------------------------------------------
# Piezas del informe
# ----------------------------------------------------------------------
def _criterio_texto(res, F):
    c, lim = res["criterio"], res["limite"]
    if c == "ea":
        return f"Error aproximado Ea menor que {F.lim(lim)} %"
    if c == "et":
        return f"Error verdadero Et menor que {F.lim(lim)} %"
    return f"{int(lim)} iteraciones"


def _tarjeta_datos(es_biseccion, res, F, estilos):
    if es_biseccion:
        inicio = ("Intervalo inicial", f"[Xi, Xf] = [{F.x(res['xi0'])} ; {F.x(res['xf0'])}]")
    else:
        inicio = ("Puntos iniciales", f"x₋₁ = {F.x(res['x_ant0'])}    x₀ = {F.x(res['x_act0'])}")
    vv = res["valor_verdadero"]
    filas = [inicio, ("Criterio de parada", _criterio_texto(res, F)),
             ("Valor verdadero", F.x(vv) if vv is not None else "No indicado"),
             ("Decimales mostrados", str(res["dec"]))]
    datos = [[Paragraph(_esc(a), estilos["etq"]), Paragraph(_esc(b), estilos["texto"])] for a, b in filas]
    t = Table(datos, colWidths=[110, ANCHO_UTIL - 110])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, BORDE), ("LINEBELOW", (0, 0), (-1, -2), 0.4, BORDE),
                           ("BACKGROUND", (0, 0), (0, -1), FONDO), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def _tarjeta_resultado(res, F, estilos):
    its = res["iteraciones"]
    metricas = [("ITERACIONES", str(len(its)))]
    if its:
        ea = its[-1]["ea"]
        metricas.append(("Ea FINAL", f"{F.e(ea)} %" if ea is not None else "—"))
        if res["valor_verdadero"] is not None:
            metricas.append(("Et FINAL", f"{F.e(its[-1]['ept'])} %"))

    def celda(etiqueta, parrafo, ancho):
        c = Table([[Paragraph(etiqueta, estilos["etq"])], [parrafo]], colWidths=[ancho])
        c.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        return c

    ancho_raiz, ancho_met = ANCHO_UTIL * 0.4, ANCHO_UTIL * 0.6 / len(metricas)
    fila = [celda("RAÍZ APROXIMADA", Paragraph(_esc(F.x(res["raiz"])), estilos["raiz"]), ancho_raiz - 16)]
    fila += [celda(e, Paragraph(_esc(v), estilos["valor"]), ancho_met - 14) for e, v in metricas]
    t = Table([fila], colWidths=[ancho_raiz] + [ancho_met] * len(metricas))
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, BORDE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 10),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    return t


def _aviso(texto, ok, estilos):
    fondo, borde, color = ((colors.HexColor("#E6F4EA"), colors.HexColor("#1E8E3E"), colors.HexColor("#1B5E32"))
                           if ok else (colors.HexColor("#FFF4D6"), colors.HexColor("#E0A800"), colors.HexColor("#7A5B00")))
    estilo = ParagraphStyle("aviso", parent=estilos["texto"], textColor=color)
    t = Table([[Paragraph(_esc(texto), estilo)]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), fondo), ("LINEBEFORE", (0, 0), (0, -1), 3, borde),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


def _tabla_iteraciones(df, estilos):
    cab = ParagraphStyle("cab", parent=estilos["texto"], fontName="DV-B", fontSize=7.8, leading=10,
                         textColor=AZUL, alignment=TA_CENTER)
    celda = ParagraphStyle("celda", parent=estilos["texto"], fontSize=7.8, leading=10, alignment=TA_CENTER)
    celda_b = ParagraphStyle("celda_b", parent=celda, fontName="DV-B")
    filas = [[Paragraph(_esc(str(c)), cab) for c in df.columns]]
    ultima = len(df) - 1
    for i, (_, fila) in enumerate(df.iterrows()):
        filas.append([Paragraph(_esc(str(v)), celda_b if i == ultima else celda) for v in fila])
    n = len(df.columns)
    primera = 30
    anchos = [primera] + [(ANCHO_UTIL - primera) / (n - 1)] * (n - 1)
    t = Table(filas, colWidths=anchos, repeatRows=1)
    estilo = [("GRID", (0, 0), (-1, -1), 0.4, BORDE), ("BACKGROUND", (0, 0), (-1, 0), FONDO),
              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3.5),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("LEFTPADDING", (0, 0), (-1, -1), 2),
              ("RIGHTPADDING", (0, 0), (-1, -1), 2)]
    if len(df):
        estilo.append(("BACKGROUND", (0, ultima + 1), (-1, ultima + 1), RESALTE))
    t.setStyle(TableStyle(estilo))
    return t


# ----------------------------------------------------------------------
# Informe completo
# ----------------------------------------------------------------------
def generar_pdf(metodo, res, fn, coma, grafica_png, proyecto="", detalle="", integrantes=""):
    """Devuelve los bytes del PDF.

    metodo: "biseccion" | "secante";  res: resultado del método;  fn: función parseada;
    coma: True para mostrar los decimales con coma;  grafica_png: bytes de la gráfica final.
    """
    _registrar_fuentes()
    estilos = _estilos()
    es_biseccion = metodo == "biseccion"
    F = Formato(res.get("modo", "completa"), res["dec"], coma)
    its = res["iteraciones"]
    titulo = "Método de Bisección" if es_biseccion else "Método de la Secante"

    historia = [Paragraph(titulo, estilos["titulo"]),
                HRFlowable(width=60, thickness=3, color=TEAL, hAlign="LEFT", spaceBefore=3, spaceAfter=5),
                Paragraph(f"Informe del ejercicio · generado el {datetime.now():%d/%m/%Y a las %H:%M}",
                          estilos["sub"]),
                Paragraph("Ejercicio", estilos["h2"]),
                _formula(f"f(x) = {fn.latex}", estilos), Spacer(1, 4),
                _tarjeta_datos(es_biseccion, res, F, estilos),
                Paragraph("Resultado", estilos["h2"]),
                _tarjeta_resultado(res, F, estilos), Spacer(1, 6),
                _aviso(re.sub(r"(?<=\d)\.(?=\d)", ",", res["motivo"]) if coma else res["motivo"],
                       res["convergio"], estilos)]
    if res.get("advertencia"):
        historia += [Spacer(1, 4), _aviso(res["advertencia"], False, estilos)]

    if its:
        df, _ = (construir_tablas if es_biseccion else construir_tablas_secante)(res, F)
        historia += [Paragraph("Tabla de iteraciones", estilos["h2"]), _tabla_iteraciones(df, estilos)]
        notas = ("Ea = error aproximado relativo porcentual." if es_biseccion else
                 "xᵢ₊₁ = xᵢ − f(xᵢ)·(xᵢ − xᵢ₋₁) / (f(xᵢ) − f(xᵢ₋₁)).  Ea = error aproximado relativo porcentual.")
        if res["valor_verdadero"] is not None:
            notas += "  Et = error verdadero = |(valor verdadero − aproximación) / valor verdadero| × 100."
        historia += [Spacer(1, 3), Paragraph(_esc(notas), estilos["pequeno"])]

        historia.append(Paragraph("Desarrollo paso a paso", estilos["h2"]))
        for it in its:
            ea = f"{F.e(it['ea'])} %" if it["ea"] is not None else "—"
            if es_biseccion:
                cab = f"Iteración {it['n']}  ·  Xr = {F.x(it['xr'])}  ·  Ea = {ea}"
                pasos = pasos_iteracion(it, fn, F, res, ultima=(it is its[-1]))
            else:
                cab = f"Iteración {it['n']}  ·  xᵢ₊₁ = {F.x(it['x_sig'])}  ·  Ea = {ea}"
                pasos = pasos_iteracion_secante(it, fn, F, res, ultima=(it is its[-1]))
            historia.append(Paragraph(_esc(cab), estilos["iter"]))
            historia += _items_a_flowables(pasos, estilos)
        historia += _items_a_flowables((pasos_prueba_error if es_biseccion else pasos_prueba_error_secante)(res, fn, F),
                                       estilos)

    if grafica_png:
        ancho_px, alto_px = ImageReader(io.BytesIO(grafica_png)).getSize()
        ancho = min(ANCHO_UTIL, 470)
        grafica = Image(io.BytesIO(grafica_png), width=ancho, height=ancho * alto_px / ancho_px)
        grafica.hAlign = "CENTER"
        historia += [Paragraph("Gráfica", estilos["h2"]), grafica, Spacer(1, 3),
                     Paragraph("La función, las aproximaciones y la raíz encontrada (en rojo).",
                               estilos["pequeno"])]

    pie_izq = " · ".join(x for x in (proyecto, detalle, integrantes) if x)

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(BORDE)
        canvas.line(MARGEN, 38, letter[0] - MARGEN, 38)
        canvas.setFont("DV", 7.5)
        canvas.setFillColor(GRIS)
        canvas.drawString(MARGEN, 26, pie_izq[:110])
        canvas.drawRightString(letter[0] - MARGEN, 26, f"Página {doc.page}")
        canvas.restoreState()

    salida = io.BytesIO()
    doc = BaseDocTemplate(salida, pagesize=letter, leftMargin=MARGEN, rightMargin=MARGEN, topMargin=46,
                          bottomMargin=52, title=f"{titulo} - informe del ejercicio", author=proyecto or "")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(MARGEN, 52, ANCHO_UTIL, letter[1] - 98,
                                                              leftPadding=0, rightPadding=0, topPadding=0,
                                                              bottomPadding=0)], onPage=pie)])
    doc.build(historia)
    return salida.getvalue()

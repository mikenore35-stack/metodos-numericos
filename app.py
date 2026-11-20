import io
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from ayuda import boton_ayuda
from metodos import ErrorMetodo, biseccion, explorar, secante
from pdf_informe import generar_pdf
from parser_seguro import parsear_funcion
from presentacion import (
    Formato,
    construir_tablas,
    construir_tablas_secante,
    pasos_iteracion,
    pasos_iteracion_secante,
    pasos_prueba_error,
    pasos_prueba_error_secante,
)

st.set_page_config(page_title="Métodos Numéricos", page_icon="📐", layout="wide")

# ----------------------------------------------------------------------
# Diseño: textos del pie de página y paleta (la paleta del tema está en .streamlit/config.toml)
# ----------------------------------------------------------------------
PROYECTO = "Plataforma de Métodos Numéricos"
DETALLE = "Proyecto académico · Bisección y Secante · 2026"
INTEGRANTES = ""  # Opcional. Ejemplo: "Nombre Apellido · Nombre Apellido"

AZUL = "#1F4E79"      # color principal
TEAL = "#0F8B8D"      # acento
NARANJA = "#D9822B"   # aproximaciones
ROJO = "#B83B3B"      # raíz encontrada
VERDE = "#2E7D5B"     # valor verdadero
GRIS = "#6B7785"

ESTILO = """
<style>
.block-container {padding-top: 2.5rem; padding-bottom: 2rem; max-width: 1180px;}
h1, h2, h3 {color: #1F4E79; letter-spacing: -0.01em;}
[data-testid="stMetric"] {padding: 0.1rem 0;}
.hero {padding: 0.4rem 0 1.4rem 0;}
.hero h1 {font-size: 2.7rem; margin: 0 0 0.3rem 0; padding: 0;}
.hero p {font-size: 1.15rem; color: #52606D; margin: 0;}
.hero .linea {width: 64px; height: 4px; background: #0F8B8D; border-radius: 2px; margin-top: 1rem;}
.res-etq {font-size: 0.8rem; color: #6B7785; text-transform: uppercase; letter-spacing: 0.07em;}
.res-val {font-size: 2.6rem; font-weight: 700; color: #1F4E79; line-height: 1.15;}
.pie {text-align: center; color: #6B7785; font-size: 0.85rem; margin-top: 3rem; padding-top: 1rem;
      border-top: 1px solid #E1E8F0;}
</style>
"""

AYUDA_FUNCION = ("Ejemplos: sen(x) - x^2, x^3 - x - 2, cos(x) - x, exp(-x) - x, ln(x) + x. "
                 "Potencias con ^ o **. En esta página log es base 10 y ln es natural.")
CRITERIOS = {
    "Error aproximado (%) menor que": "ea",
    "Error verdadero (%) menor que": "et",
    "Número fijo de iteraciones": "iter",
}


def coma_texto(texto, coma):
    """Cambia el punto decimal por coma en un texto (solo entre dígitos)."""
    return re.sub(r"(?<=\d)\.(?=\d)", ",", texto) if coma else texto


# ----------------------------------------------------------------------
# Gráficas
# ----------------------------------------------------------------------
def _evaluar(fn, xs):
    ys = []
    for v in xs:
        try:
            ys.append(fn(v))
        except ValueError:
            ys.append(np.nan)
    return ys


def _estilo_ejes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("x")
    ax.set_ylabel("f(x)")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=9)


def graficar_biseccion(fn, res, k=None):
    """Gráfica de la bisección. Con `k` muestra el estado hasta la iteración k (deslizador)."""
    vv = res["valor_verdadero"]
    its = res["iteraciones"]
    n = len(its)
    k = n if k is None else k
    claves = [res["xi0"], res["xf0"], res["raiz"]] + ([vv] if vv is not None else [])
    x_min, x_max = min(claves), max(claves)
    margen = (x_max - x_min) * 0.25 or 1.0
    xs = np.linspace(x_min - margen, x_max + margen, 500)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(xs, _evaluar(fn, xs), linewidth=2.2, color=AZUL, label="f(x)")
    ax.axhline(0, color=GRIS, linewidth=1)
    ax.axvline(res["xi0"], color=GRIS, linestyle=":", label="Intervalo inicial")
    ax.axvline(res["xf0"], color=GRIS, linestyle=":")
    if vv is not None:
        ax.axvline(vv, color=VERDE, linestyle="--", label=f"Valor verdadero = {vv:g}")
    if its:
        actual = its[k - 1]
        ax.axvspan(actual["xi"], actual["xf"], color=TEAL, alpha=0.12, label=f"Intervalo de la iteración {k}")
        previos = its[:k]
        pts = [it["xr"] for it in previos]
        ax.scatter(pts, _evaluar(fn, pts), color=NARANJA, zorder=3, s=30, label="Aproximaciones Xr")
        for it in previos:
            try:
                ax.annotate(str(it["n"]), (it["xr"], fn(it["xr"])), textcoords="offset points",
                            xytext=(0, 7), ha="center", fontsize=8)
            except ValueError:
                pass
        x_marca = actual["xr"]
        etiqueta = f"Raíz ≈ {x_marca:g}" if k == n else f"Xr de la iteración {k} = {x_marca:g}"
    else:
        x_marca, etiqueta = res["raiz"], f"Raíz ≈ {res['raiz']:g}"
    try:
        ax.scatter([x_marca], [fn(x_marca)], color=ROJO, zorder=4, s=70, label=etiqueta)
    except ValueError:
        pass
    _estilo_ejes(ax)
    return fig


def graficar_secante(fn, res, k=None):
    """Gráfica de la secante. Con `k` muestra las rectas y aproximaciones hasta la iteración k."""
    vv = res["valor_verdadero"]
    its = res["iteraciones"]
    n = len(its)
    k = n if k is None else k
    claves = [res["x_ant0"], res["x_act0"], res["raiz"]] + [it["x_sig"] for it in its]
    if vv is not None:
        claves.append(vv)
    x_min, x_max = min(claves), max(claves)
    margen = (x_max - x_min) * 0.25 or 1.0
    xs = np.linspace(x_min - margen, x_max + margen, 500)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(xs, _evaluar(fn, xs), linewidth=2.2, color=AZUL, label="f(x)")
    ax.axhline(0, color=GRIS, linewidth=1)
    previas = its[:max(k - 1, 0)][-12:]
    for i, it in enumerate(previas):
        ax.plot([it["x_ant"], it["x_sig"]], [it["f_ant"], 0], linestyle="--", linewidth=1,
                color=TEAL, alpha=0.45, label="Rectas anteriores" if i == 0 else None)
    iniciales = [(res["x_ant0"], res["f_ant0"], "x₋₁"), (res["x_act0"], res["f_act0"], "x₀")]
    ax.scatter([p[0] for p in iniciales], [p[1] for p in iniciales], color=GRIS, marker="s",
               zorder=3, label="Puntos iniciales")
    for x, y, nombre in iniciales:
        ax.annotate(nombre, (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    if vv is not None:
        ax.axvline(vv, color=VERDE, linestyle="--", label=f"Valor verdadero = {vv:g}")
    if its:
        actual = its[k - 1]
        ax.plot([actual["x_ant"], actual["x_sig"]], [actual["f_ant"], 0], linewidth=1.8, color=TEAL,
                label=f"Recta secante de la iteración {k}")
        ax.plot([actual["x_sig"], actual["x_sig"]], [0, actual["f_sig"]], linestyle=":", linewidth=1, color=TEAL)
        hechas = its[:k]
        ax.scatter([it["x_sig"] for it in hechas], [it["f_sig"] for it in hechas], color=NARANJA,
                   zorder=3, s=30, label="Aproximaciones xᵢ₊₁")
        for it in hechas:
            ax.annotate(str(it["n"]), (it["x_sig"], it["f_sig"]), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=8)
        x_marca = actual["x_sig"]
        etiqueta = f"Raíz ≈ {x_marca:g}" if k == n else f"xᵢ₊₁ de la iteración {k} = {x_marca:g}"
    else:
        x_marca, etiqueta = res["raiz"], f"Raíz ≈ {res['raiz']:g}"
    try:
        ax.scatter([x_marca], [fn(x_marca)], color=ROJO, zorder=4, s=70, label=etiqueta)
    except ValueError:
        pass
    _estilo_ejes(ax)
    return fig


def graficar_exploracion(fn, ex, x_min, x_max):
    xs = np.linspace(x_min, x_max, 500)
    ys_curva = np.array(_evaluar(fn, xs), dtype=float)
    pts = [(x, y) for x, y in zip(ex["xs"], ex["ys"]) if y is not None]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    if pts:  # rango vertical según la tabla; lo que se sale (saltos como 1/x o tan) se corta
        ys = [p[1] for p in pts]
        pad = (max(ys) - min(ys)) * 0.1 or 1.0
        lo, hi = min(ys) - pad, max(ys) + pad
        ys_curva[(ys_curva < lo) | (ys_curva > hi)] = np.nan
        ax.set_ylim(lo, hi)
    ax.plot(xs, ys_curva, linewidth=2.2, color=AZUL, label="f(x)")
    ax.axhline(0, color=GRIS, linewidth=1)
    for i, c in enumerate(ex["cambios"]):
        ax.axvspan(c["a"], c["b"], color=NARANJA, alpha=0.18, label="Cambio de signo" if i == 0 else None)
    if pts:
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], color=AZUL, s=22, zorder=3, label="Puntos de la tabla")
    _estilo_ejes(ax)
    return fig


# ----------------------------------------------------------------------
# Bisección
# ----------------------------------------------------------------------
SIN_EJEMPLO = "— Elige un ejemplo —"
CLAVES_PUNTOS = {"bis": ("bis_xi", "bis_xf"), "sec": ("sec_xant", "sec_xact")}
# Desplegable de ejemplos: lo que se ve es solo el ejercicio; al elegirlo se escribe en la casilla tal como
# se debe colocar. Formato: nombre: (función como se escribe, punto 1, punto 2, valor verdadero)
_LISTA_EJEMPLOS = {
    "x² − 3": ("x^2 - 3", 1.0, 2.0, 1.732),
    "x³ − x − 2": ("x^3 - x - 2", 1.0, 2.0, 1.52138),
    "sen(x) = x²": ("sen(x) = x^2", 0.5, 1.0, 0.876),
    "cos(x) − x": ("cos(x) - x", 0.0, 1.0, 0.739085),
    "tan(x) = 1": ("tan(x) = 1", 0.0, 1.0, 0.785398),
    "√(x + 3) = x": ("sqrt(x + 3) = x", 2.0, 3.0, 2.302776),
    "eˣ = 3x": ("exp(x) = 3*x", 0.0, 1.0, 0.619061),
    "ln(x) + x = 2": ("ln(x) + x = 2", 1.0, 2.0, 1.557146),
    "ln(x²) = 0,7": ("ln(x^2) = 0.7", 1.0, 2.0, 1.419068),
    "log(x) = 0,5": ("log(x) = 0.5", 3.0, 4.0, 3.162278),
    "x·sen(x) = 1": ("x*sen(x) = 1", 0.0, 2.0, 1.114157),
    "1/x = x − 1": ("1/x = x - 1", 1.0, 2.0, 1.618034),
}
EJEMPLOS = {"bis": _LISTA_EJEMPLOS, "sec": _LISTA_EJEMPLOS}


def proximo_id():
    st.session_state["_calc_id"] = st.session_state.get("_calc_id", 0) + 1
    return st.session_state["_calc_id"]


def valores_en_blanco(p):
    """Formulario en blanco: función vacía (se ve el mensaje «Coloca la función») y valores por defecto."""
    ka, kb = CLAVES_PUNTOS[p]
    return {f"{p}_f": "", ka: 0.0, kb: 1.0, f"{p}_vv": None, f"{p}_ej": SIN_EJEMPLO,
            f"{p}_crit": list(CRITERIOS)[0], f"{p}_lim_ea": 1.0, f"{p}_lim_et": 1.0,
            f"{p}_lim_iter": 5, f"{p}_dec": 6, f"{p}_max": 50}


def estado_inicial(p):
    """Valores iniciales de los campos (se guardan en session_state para poder cambiarlos con botones)."""
    for clave, valor in valores_en_blanco(p).items():
        st.session_state.setdefault(clave, valor)


def cargar_ejemplo(p):
    nombre = st.session_state.get(f"{p}_ej")
    if nombre not in EJEMPLOS[p]:
        return
    f, x1, x2, vv = EJEMPLOS[p][nombre]
    ka, kb = CLAVES_PUNTOS[p]
    st.session_state.update({f"{p}_f": f, ka: x1, kb: x2, f"{p}_vv": vv})
    st.session_state.pop(f"{p}_res", None)


def limpiar(p):
    """Deja el formulario en blanco para empezar otro ejercicio."""
    st.session_state.update(valores_en_blanco(p))
    st.session_state.pop(f"{p}_res", None)


def enviar_a(destino, texto, a, b):
    """Lleva la función y el intervalo del explorador al método elegido."""
    p = "bis" if destino == "Bisección" else "sec"
    ka, kb = CLAVES_PUNTOS[p]
    st.session_state.update({f"{p}_f": texto, ka: float(a), kb: float(b), f"{p}_vv": None,
                             f"{p}_ej": SIN_EJEMPLO, "metodo": destino})
    st.session_state.pop(f"{p}_res", None)


def tarjeta_resultado(res, F, its):
    """Tarjeta con la raíz destacada y los datos finales, más el motivo de parada."""
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        c1.markdown(f'<div class="res-etq">Raíz aproximada</div><div class="res-val">{F.x(res["raiz"])}</div>',
                    unsafe_allow_html=True)
        c2.metric("Iteraciones", len(its))
        if its:
            ea = its[-1]["ea"]
            c3.metric("Ea final", f"{F.e(ea)} %" if ea is not None else "—", help="Error aproximado final")
            if res["valor_verdadero"] is not None:
                c4.metric("Et final", f"{F.e(its[-1]['ept'])} %", help="Error verdadero final")


def estilizar_tabla(df):
    """Resalta la última fila (la raíz aproximada)."""
    ultima = len(df) - 1

    def resaltar(fila):
        return ["background-color: #E3EEF6; font-weight: 600" if fila.name == ultima else "" for _ in fila]

    return df.style.apply(resaltar, axis=1)


def bloque_parada(prefijo):
    """Campos del criterio de parada, valor verdadero y opciones (igual en ambos métodos)."""
    with st.container(border=True):
        st.markdown("**2 · Criterio de parada y opciones**")
        c1, c2, c3 = st.columns(3)
        etiqueta = c1.selectbox("Detener cuando…", list(CRITERIOS), key=f"{prefijo}_crit")
        criterio = CRITERIOS[etiqueta]
        if criterio == "iter":
            limite = c2.number_input("Número de iteraciones", min_value=1, max_value=500, step=1,
                                     key=f"{prefijo}_lim_iter")
        else:
            limite = c2.number_input("Porcentaje (%)", min_value=0.0001, step=0.1, format="%.4f",
                                     key=f"{prefijo}_lim_{criterio}")
        vv_valor = c3.number_input("Valor verdadero (opcional)", value=None, format="%.6f",
                                   key=f"{prefijo}_vv", placeholder="Para calcular Et",
                                   help="Si lo escribes, la tabla y el paso a paso incluyen el error verdadero Et. "
                                        "Déjalo vacío si el ejercicio no lo da.")
        c4, c5, _ = st.columns(3)
        dec = c4.number_input("Decimales a mostrar", min_value=1, max_value=10, step=1, key=f"{prefijo}_dec")
        max_iter = c5.number_input("Máx. iteraciones", min_value=1, max_value=500, step=1,
                                   key=f"{prefijo}_max", help="Límite de seguridad si no se cumple el criterio.")
    return criterio, limite, vv_valor, int(dec), int(max_iter)


def ir_a(pagina):
    st.session_state["metodo"] = pagina


def pagina_inicio():
    st.markdown(
        '<div class="hero"><h1>Métodos Numéricos</h1>'
        "<p>Resuelve ecuaciones paso a paso con los métodos de bisección y secante.</p>"
        '<div class="linea"></div></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("### 🔍 Explorador")
            st.write("Tabula y grafica f(x) y encuentra los intervalos donde cambia de signo, "
                     "para usarlos en los métodos.")
            st.button("Abrir explorador →", key="ir_exp", on_click=ir_a, args=("Explorador",))
    with c2:
        with st.container(border=True):
            st.markdown("### 📐 Bisección")
            st.write("Encuentra una raíz dentro de un intervalo donde la función cambia de signo, "
                     "dividiéndolo a la mitad en cada iteración.")
            st.button("Usar bisección →", key="ir_bis", on_click=ir_a, args=("Bisección",))
    with c3:
        with st.container(border=True):
            st.markdown("### 📏 Secante")
            st.write("Parte de dos puntos iniciales y usa la recta que los une para acercarse a la raíz. "
                     "No necesita cambio de signo.")
            st.button("Usar secante →", key="ir_sec", on_click=ir_a, args=("Secante",))

    st.markdown("#### Qué incluye")
    f1, f2, f3 = st.columns(3)
    f1.markdown("**🧮 Paso a paso**\n\nCada iteración desarrollada con la fórmula y los números sustituidos.")
    f2.markdown("**📊 Errores Ea y Et**\n\nError aproximado y error verdadero en cada iteración, "
                "con distintos criterios de parada.")
    f3.markdown("**📈 Gráficas**\n\nLa función, las aproximaciones y un deslizador para ver cada iteración.")
    st.info("¿Primera vez? Abre **❓ Ayuda** en el menú lateral para ver cómo usar la página.")


def pie_de_pagina():
    extra = f"<br>{INTEGRANTES}" if INTEGRANTES else ""
    st.markdown(f'<div class="pie"><b>{PROYECTO}</b><br>{DETALLE}{extra}</div>', unsafe_allow_html=True)


def png_de(fig):
    """Bytes PNG de una figura de matplotlib (y la cierra)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def bloque_pdf(p, guardado, fn, res, coma, metodo):
    """Botón que genera el PDF del ejercicio (datos, tabla, paso a paso y gráfica) y botón para descargarlo."""
    clave = f"{p}_pdf"
    c1, c2, _ = st.columns([1.2, 1.2, 3])
    if c1.button("📄 Generar PDF", key=f"{p}_pdf_btn",
                 help="Crea un PDF con todo el ejercicio: datos, tabla de iteraciones, paso a paso y gráfica."):
        try:
            with st.spinner("Generando el PDF…"):
                fig = graficar_biseccion(fn, res) if metodo == "biseccion" else graficar_secante(fn, res)
                datos = generar_pdf(metodo, res, fn, coma, png_de(fig), PROYECTO, DETALLE, INTEGRANTES)
            st.session_state[clave] = {"id": guardado.get("id"), "coma": coma, "datos": datos}
        except Exception as e:  # el PDF nunca debe dejar la página sin resultados
            st.session_state.pop(clave, None)
            st.error(f"⚠️ No se pudo generar el PDF: {e}")
    listo = st.session_state.get(clave)
    if listo and listo["id"] == guardado.get("id") and listo["coma"] == coma:
        c2.download_button("⬇️ Descargar PDF", listo["datos"], file_name=f"{metodo}_ejercicio.pdf",
                           mime="application/pdf", key=f"{p}_pdf_dl")


def render_pasos(items):
    for tipo, texto in items:
        if tipo == "latex":
            st.latex(texto)
        else:
            st.markdown(texto)


def mostrar_biseccion(guardado, coma):
    res = guardado["res"]
    fn = parsear_funcion(guardado["texto"])
    F = Formato(res["modo"], res["dec"], coma)
    its = res["iteraciones"]

    st.divider()
    st.latex(f"f(x) = {fn.latex}")
    motivo = coma_texto(res["motivo"], coma)
    tarjeta_resultado(res, F, its)
    (st.success if res["convergio"] else st.warning)(motivo)
    bloque_pdf("bis", guardado, fn, res, coma, "biseccion")
    if not its:
        return

    tab_tabla, tab_pasos, tab_grafica = st.tabs(["📋 Tabla de iteraciones", "🧮 Paso a paso", "📈 Gráfica"])

    with tab_tabla:
        df_txt, _ = construir_tablas(res, F)
        st.dataframe(estilizar_tabla(df_txt), hide_index=True)
        notas = "Ea = error aproximado relativo porcentual."
        if res["valor_verdadero"] is not None:
            notas += " Et = error verdadero = |(valor verdadero − Xr) / valor verdadero| × 100."
        st.caption(notas)

    with tab_pasos:
        todas = st.toggle("Expandir todas las iteraciones", value=False, key="bis_expandir")
        for it in its:
            ea = f"{F.e(it['ea'])} %" if it["ea"] is not None else "—"
            titulo = f"Iteración {it['n']}  ·  Xr = {F.x(it['xr'])}  ·  Ea = {ea}"
            with st.expander(titulo, expanded=todas or it["n"] == 1):
                render_pasos(pasos_iteracion(it, fn, F, res, ultima=(it is its[-1])))
        render_pasos(pasos_prueba_error(res, fn, F))

    with tab_grafica:
        n, k = len(its), len(its)
        if n > 1:
            k = st.slider("Iteración mostrada", 1, n, n, key=f"bis_k_{guardado.get('id', 0)}")
        fig = graficar_biseccion(fn, res, k)
        st.pyplot(fig)
        plt.close(fig)
        it = its[k - 1]
        st.caption(f"Iteración {k}: [Xi, Xf] = [{F.x(it['xi'])}, {F.x(it['xf'])}]  →  "
                   f"Xr = {F.x(it['xr'])},  f(Xr) = {F.f(it['fr'])}")


def pagina_biseccion(coma):
    st.header("Método de Bisección")
    estado_inicial("bis")

    with st.container(border=True):
        st.markdown("**1 · Función e intervalo**")
        st.selectbox("Cargar un ejemplo", [SIN_EJEMPLO] + list(EJEMPLOS["bis"]), key="bis_ej",
                     on_change=cargar_ejemplo, args=("bis",))
        c1, c2, c3 = st.columns([2, 1, 1])
        texto = c1.text_input("Función f(x)", key="bis_f", help=AYUDA_FUNCION,
                              placeholder="Coloca la función")
        xi = c2.number_input("Xi (límite inferior)", format="%.4f", key="bis_xi")
        xf = c3.number_input("Xf (límite superior)", format="%.4f", key="bis_xf")

    criterio, limite, vv_valor, dec, max_iter = bloque_parada("bis")

    b1, b2, _ = st.columns([1, 1, 4])
    calcular = b1.button("Calcular", type="primary", key="bis_calc")
    b2.button("🧹 Limpiar", key="bis_limpiar", on_click=limpiar, args=("bis",))

    if calcular:
        try:
            fn = parsear_funcion(texto)
            if vv_valor == 0:
                raise ValueError("El valor verdadero no puede ser 0: el error verdadero divide entre él.")
            res = biseccion(fn, xi, xf, criterio=criterio, limite=limite, valor_verdadero=vv_valor,
                            max_iter=max_iter, modo="completa", dec=dec)
            st.session_state["bis_res"] = {"res": res, "texto": fn.texto, "id": proximo_id()}
        except ValueError as e:
            st.session_state.pop("bis_res", None)
            st.error(f"⚠️ {e}")

    if "bis_res" in st.session_state:
        mostrar_biseccion(st.session_state["bis_res"], coma)


# ----------------------------------------------------------------------
# Secante
# ----------------------------------------------------------------------
def mostrar_secante(guardado, coma):
    res = guardado["res"]
    fn = parsear_funcion(guardado["texto"])
    F = Formato("completa", res["dec"], coma)
    its = res["iteraciones"]

    st.divider()
    st.latex(f"f(x) = {fn.latex}")
    motivo = coma_texto(res["motivo"], coma)
    tarjeta_resultado(res, F, its)
    (st.success if res["convergio"] else st.warning)(motivo)
    if res["advertencia"]:
        st.warning(res["advertencia"])
    bloque_pdf("sec", guardado, fn, res, coma, "secante")
    if not its:
        return

    tab_tabla, tab_pasos, tab_grafica = st.tabs(["📋 Tabla de iteraciones", "🧮 Paso a paso", "📈 Gráfica"])

    with tab_tabla:
        df_txt, _ = construir_tablas_secante(res, F)
        st.dataframe(estilizar_tabla(df_txt), hide_index=True)
        notas = ("xᵢ₊₁ = xᵢ − f(xᵢ)·(xᵢ − xᵢ₋₁) / (f(xᵢ) − f(xᵢ₋₁)).  "
                 "Ea = error aproximado relativo porcentual.")
        if res["valor_verdadero"] is not None:
            notas += "  Et = error verdadero = |(valor verdadero − xᵢ₊₁) / valor verdadero| × 100."
        st.caption(notas)

    with tab_pasos:
        todas = st.toggle("Expandir todas las iteraciones", value=False, key="sec_expandir")
        for it in its:
            ea = f"{F.e(it['ea'])} %" if it["ea"] is not None else "—"
            titulo = f"Iteración {it['n']}  ·  xᵢ₊₁ = {F.x(it['x_sig'])}  ·  Ea = {ea}"
            with st.expander(titulo, expanded=todas or it["n"] == 1):
                render_pasos(pasos_iteracion_secante(it, fn, F, res, ultima=(it is its[-1])))
        render_pasos(pasos_prueba_error_secante(res, fn, F))

    with tab_grafica:
        n, k = len(its), len(its)
        if n > 1:
            k = st.slider("Iteración mostrada", 1, n, n, key=f"sec_k_{guardado.get('id', 0)}")
        fig = graficar_secante(fn, res, k)
        st.pyplot(fig)
        plt.close(fig)
        it = its[k - 1]
        st.caption(f"Iteración {k}: xᵢ₋₁ = {F.x(it['x_ant'])}, xᵢ = {F.x(it['x_act'])}  →  "
                   f"xᵢ₊₁ = {F.x(it['x_sig'])},  f(xᵢ₊₁) = {F.f(it['f_sig'])}")


def pagina_secante(coma):
    st.header("Método de la Secante")
    estado_inicial("sec")

    with st.container(border=True):
        st.markdown("**1 · Función y puntos iniciales**")
        st.selectbox("Cargar un ejemplo", [SIN_EJEMPLO] + list(EJEMPLOS["sec"]), key="sec_ej",
                     on_change=cargar_ejemplo, args=("sec",))
        c1, c2, c3 = st.columns([2, 1, 1])
        texto = c1.text_input("Función f(x)", key="sec_f", help=AYUDA_FUNCION,
                              placeholder="Coloca la función")
        x_ant = c2.number_input("x₋₁ (primer punto)", format="%.6f", key="sec_xant")
        x_act = c3.number_input("x₀ (segundo punto)", format="%.6f", key="sec_xact")

    criterio, limite, vv_valor, dec, max_iter = bloque_parada("sec")

    b1, b2, _ = st.columns([1, 1, 4])
    calcular = b1.button("Calcular", type="primary", key="sec_calc")
    b2.button("🧹 Limpiar", key="sec_limpiar", on_click=limpiar, args=("sec",))

    if calcular:
        try:
            fn = parsear_funcion(texto)
            if vv_valor == 0:
                raise ValueError("El valor verdadero no puede ser 0: el error verdadero divide entre él.")
            res = secante(fn, x_ant, x_act, criterio=criterio, limite=limite,
                          valor_verdadero=vv_valor, max_iter=max_iter)
            res["dec"] = dec
            st.session_state["sec_res"] = {"res": res, "texto": fn.texto, "id": proximo_id()}
        except ValueError as e:
            st.session_state.pop("sec_res", None)
            st.error(f"⚠️ {e}")

    if "sec_res" in st.session_state:
        mostrar_secante(st.session_state["sec_res"], coma)


# ----------------------------------------------------------------------
# Explorador de la función
# ----------------------------------------------------------------------
# Ejemplos del explorador: nombre: (función como se escribe, x mínimo, x máximo, paso)
EJEMPLOS_EXP = {
    "x³ − x − 2": ("x^3 - x - 2", 0.0, 3.0, 0.5),
    "sen(x) = x²": ("sen(x) = x^2", 0.5, 1.0, 0.05),
    "cos(x) − x": ("cos(x) - x", 0.0, 2.0, 0.25),
    "√(x + 3) = x": ("sqrt(x + 3) = x", 0.0, 5.0, 0.5),
    "eˣ = 3x": ("exp(x) = 3*x", 0.0, 2.0, 0.25),
    "ln(x) + x = 2": ("ln(x) + x = 2", 0.0, 5.0, 0.5),
    "x·sen(x) = 1": ("x*sen(x) = 1", 0.0, 10.0, 0.5),
    "−2x⁶ − 1,5x⁴ + 10x + 2": ("-2*x^6 - 1.5*x^4 + 10*x + 2", -2.0, 2.0, 0.5),
    "tan(x)": ("tan(x)", 0.0, 3.5, 0.25),
}
EXP_EN_BLANCO = {"exp_f": "", "exp_min": 0.0, "exp_max": 5.0, "exp_paso": 0.5, "exp_ej": SIN_EJEMPLO}


def cargar_ejemplo_exp():
    nombre = st.session_state.get("exp_ej")
    if nombre in EJEMPLOS_EXP:
        f, a, b, paso = EJEMPLOS_EXP[nombre]
        st.session_state.update({"exp_f": f, "exp_min": a, "exp_max": b, "exp_paso": paso})


def limpiar_exp():
    st.session_state.update(EXP_EN_BLANCO)


def pagina_explorador(coma):
    st.header("Explorador de la función")
    for clave, valor in EXP_EN_BLANCO.items():
        st.session_state.setdefault(clave, valor)

    with st.container(border=True):
        st.markdown("**Función y rango a explorar**")
        st.selectbox("Cargar un ejemplo", [SIN_EJEMPLO] + list(EJEMPLOS_EXP), key="exp_ej",
                     on_change=cargar_ejemplo_exp)
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        texto = c1.text_input("Función f(x)", key="exp_f", help=AYUDA_FUNCION, placeholder="Coloca la función")
        x_min = c2.number_input("x mínimo", format="%.4f", key="exp_min")
        x_max = c3.number_input("x máximo", format="%.4f", key="exp_max")
        paso = c4.number_input("Paso", min_value=0.0001, format="%.4f", key="exp_paso")
        st.button("🧹 Limpiar", key="exp_limpiar", on_click=limpiar_exp)

    if not texto.strip():
        st.info("Coloca la función para tabularla y encontrar dónde cambia de signo.")
        return
    try:
        fn = parsear_funcion(texto)
        ex = explorar(fn, x_min, x_max, paso)
    except ValueError as e:
        st.error(f"⚠️ {e}")
        return

    F = Formato("completa", 4, coma)
    st.latex(f"f(x) = {fn.latex}")

    cambios = ex["cambios"]
    if cambios:
        st.success(f"Se detectó cambio de signo en {len(cambios)} intervalo(s). Puedes usarlos como "
                   "Xi y Xf (bisección) o como x₋₁ y x₀ (secante).")
        for i, c in enumerate(cambios):
            with st.container(border=True):
                t1, t2, t3 = st.columns([3, 1, 1])
                t1.markdown(f"**[{F.x(c['a'])}, {F.x(c['b'])}]**  —  f({F.x(c['a'])}) = {F.f(c['fa'])},  "
                            f"f({F.x(c['b'])}) = {F.f(c['fb'])}")
                if c["sospechoso"]:
                    t1.warning("Posible discontinuidad: el signo cambia por un salto de la función, no por una raíz.")
                t2.button("→ Bisección", key=f"exp_b_{i}", on_click=enviar_a,
                          args=("Bisección", texto, c["a"], c["b"]))
                t3.button("→ Secante", key=f"exp_s_{i}", on_click=enviar_a,
                          args=("Secante", texto, c["a"], c["b"]))
    else:
        st.info("No se detectó cambio de signo en este rango. Prueba con otro rango o con un paso más pequeño.")
    if ex["exactas"]:
        st.success("f(x) = 0 exactamente en x = " + ", ".join(F.x(e["x"]) for e in ex["exactas"]) + ".")
    if ex["indefinidos"]:
        st.warning(f"La función no está definida en {ex['indefinidos']} punto(s) del rango; se omiten en la tabla.")

    tab_tabla, tab_grafica = st.tabs(["📋 Tabla de valores", "📈 Gráfica"])
    with tab_tabla:
        signo = lambda y: "—" if y is None else ("+" if y > 0 else ("−" if y < 0 else "0"))  # noqa: E731
        df = pd.DataFrame({"x": [F.x(x) for x in ex["xs"]],
                           "f(x)": [F.f(y) if y is not None else "no definida" for y in ex["ys"]],
                           "Signo": [signo(y) for y in ex["ys"]]})
        resaltar = {c["i"] for c in cambios} | {c["i"] + 1 for c in cambios}
        st.dataframe(df.style.apply(
            lambda fila: ["background-color: #FFF1D6" if fila.name in resaltar else "" for _ in fila], axis=1),
            hide_index=True)
        st.caption("Las filas resaltadas son los puntos entre los que f(x) cambia de signo.")
    with tab_grafica:
        fig = graficar_exploracion(fn, ex, x_min, x_max)
        st.pyplot(fig)
        plt.close(fig)


# ----------------------------------------------------------------------
# Programa principal
# ----------------------------------------------------------------------
def main():
    st.markdown(ESTILO, unsafe_allow_html=True)
    st.sidebar.title("📐 Métodos Numéricos")
    boton_ayuda()
    opcion = st.sidebar.radio("Navegación", ["Inicio", "Explorador", "Bisección", "Secante"], key="metodo",
                              label_visibility="collapsed")
    coma = st.sidebar.checkbox("Usar coma como separador decimal", value=True)

    if opcion == "Inicio":
        pagina_inicio()
    elif opcion == "Explorador":
        pagina_explorador(coma)
    elif opcion == "Bisección":
        pagina_biseccion(coma)
    else:
        pagina_secante(coma)
    pie_de_pagina()


if __name__ == "__main__":
    main()

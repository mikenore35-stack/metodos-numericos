"""Formato de números, tabla de iteraciones y desarrollo paso a paso (sin Streamlit)."""
import math
from decimal import Decimal

import pandas as pd

from metodos import ajustar


class Formato:
    """Convierte números a texto con la notación del curso (coma decimal, cifras fijas)."""

    def __init__(self, modo="truncar", dec=3, coma=True):
        self.modo, self.dec, self.coma = modo, dec, coma

    # -- base -----------------------------------------------------------
    def _num(self, v, dec, latex):
        if v is None:
            return "—"
        v = 0.0 if v == 0 else float(v)
        if not math.isfinite(v):
            return "—"
        if self.modo == "completa":
            if v != 0 and abs(v) < 10 ** (-dec):
                m, e = f"{v:.3e}".split("e")
                s = rf"{m}\times10^{{{int(e)}}}" if latex else f"{m}e{int(e)}"
            else:
                s = f"{v:.{dec}f}"
        else:
            s = format(Decimal(repr(round(v, 12))), "f")
            if "." not in s:
                s += "."
            actuales = len(s.split(".")[1])
            s += "0" * max(0, dec - actuales)
            s = s.rstrip(".")
        if self.coma:
            s = s.replace(".", "{,}" if latex else ",")
        return s

    # -- tipos de valores -------------------------------------------------
    def x(self, v, latex=False):      # aproximaciones y extremos
        return self._num(v, self.dec, latex)

    def f(self, v, latex=False):      # valores de la función (adaptativo)
        return self._num(v, self.dec, latex)

    def p(self, v, latex=False):      # productos f(Xi)·f(Xr)
        if v is not None and self.modo != "completa":
            v = ajustar(v, self.modo, 2 * self.dec)
        return self._num(v, 2 * self.dec if self.modo != "completa" else self.dec, latex)

    def e(self, v, latex=False):      # errores porcentuales
        return self._num(v, 2 if self.modo != "completa" else 4, latex)

    def lim(self, v, latex=False):    # límite del criterio de parada
        s = f"{v:g}"
        return s.replace(".", "{,}" if latex else ",") if self.coma else s


# ----------------------------------------------------------------------
# Tabla de iteraciones
# ----------------------------------------------------------------------
def construir_tablas(res, F):
    """Devuelve (tabla con texto formateado, tabla numérica para exportar)."""
    its = res["iteraciones"]
    con_vv = res["valor_verdadero"] is not None
    txt, num = [], []
    for it in its:
        t = {"N°": it["n"], "Xi": F.x(it["xi"]), "Xf": F.x(it["xf"]), "Xr": F.x(it["xr"]),
             "f(Xi)": F.f(it["fi"]), "f(Xf)": F.f(it["ff"]), "f(Xr)": F.f(it["fr"])}
        n = {"N": it["n"], "Xi": it["xi"], "Xf": it["xf"], "Xr": it["xr"],
             "f(Xi)": it["fi"], "f(Xf)": it["ff"], "f(Xr)": it["fr"]}
        if con_vv:
            t["Et (%)"] = F.e(it["ept"])
            n["Et (%)"] = it["ept"]
        t["Ea (%)"] = F.e(it["ea"])
        n["Ea (%)"] = it["ea"]
        txt.append(t)
        num.append(n)
    return pd.DataFrame(txt), pd.DataFrame(num)


# ----------------------------------------------------------------------
# Desarrollo paso a paso
# ----------------------------------------------------------------------
def _cumple(it, res, F, ev="E_t"):
    """Texto que explica si la iteración cumple el criterio de parada."""
    c, lim = res["criterio"], res["limite"]
    L = lambda v: F.e(v, True)  # noqa: E731
    if c == "ea":
        if it["ea"] is None:
            return r"\text{Con una sola aproximación no se puede calcular } E_a \text{; se continúa.}"
        ok = it["ea"] < lim
        sig = "<" if ok else r"\geq"
        accion = r"\text{se detiene}" if ok else r"\text{se continúa}"
        return rf"E_a = {L(it['ea'])}\,\% \; {sig} \; {F.lim(lim, True)}\,\% \;\Rightarrow\; {accion}"
    if c == "et":
        ok = it["ept"] is not None and it["ept"] < lim
        sig = "<" if ok else r"\geq"
        accion = r"\text{se detiene}" if ok else r"\text{se continúa}"
        return rf"{ev} = {L(it['ept'])}\,\% \; {sig} \; {F.lim(lim, True)}\,\% \;\Rightarrow\; {accion}"
    return rf"\text{{Iteración }} {it['n']} \text{{ de }} {int(lim)}"


def pasos_iteracion(it, fn, F, res, ultima=False):
    """Lista de ('md'|'latex', texto) con el desarrollo de una iteración."""
    X = lambda v: F.x(v, True)   # noqa: E731
    Fv = lambda v: F.f(v, True)  # noqa: E731
    P = lambda v: F.p(v, True)   # noqa: E731
    E = lambda v: F.e(v, True)   # noqa: E731
    sust = lambda v: fn.latex_sustituido(X(v))  # noqa: E731
    vv = res["valor_verdadero"]
    out = []

    out.append(("md", f"Intervalo de trabajo: $X_i = {X(it['xi'])}$ y $X_f = {X(it['xf'])}$"))

    if it["n"] == 1:
        out.append(("md", "**1. Evaluar la función en los extremos**"))
        out.append(("latex", rf"f(X_i) = f({X(it['xi'])}) = {sust(it['xi'])} = {Fv(it['fi'])}"))
        out.append(("latex", rf"f(X_f) = f({X(it['xf'])}) = {sust(it['xf'])} = {Fv(it['ff'])}"))
    else:
        out.append(("md", "**1. Valores de la función en los extremos** (ya calculados en iteraciones anteriores)"))
        out.append(("latex", rf"f(X_i) = {Fv(it['fi'])} \qquad f(X_f) = {Fv(it['ff'])}"))

    out.append(("md", "**2. Verificar el cambio de signo**"))
    out.append(("latex",
                rf"f(X_i)\cdot f(X_f) = ({Fv(it['fi'])})({Fv(it['ff'])}) = {P(it['prod_ext'])} < 0"
                r" \;\Rightarrow\; \text{hay una raíz en } [X_i,\,X_f]"))

    out.append(("md", "**3. Aproximación de la raíz (punto medio)**"))
    out.append(("latex",
                rf"X_r = \frac{{X_i + X_f}}{{2}} = \frac{{{X(it['xi'])} + {X(it['xf'])}}}{{2}} = {X(it['xr'])}"))

    out.append(("md", "**4. Evaluar la función en $X_r$**"))
    out.append(("latex", rf"f(X_r) = f({X(it['xr'])}) = {sust(it['xr'])} = {Fv(it['fr'])}"))

    out.append(("md", "**5. Decidir en qué subintervalo está la raíz**"))
    signo = {"izquierda": "<", "derecha": ">", "exacta": "="}[it["decision"]]
    if it["decision"] == "izquierda":
        concl = rf"\text{{la raíz está en }} [X_i,\,X_r] \;\Rightarrow\; X_f = X_r = {X(it['xr'])}"
    elif it["decision"] == "derecha":
        concl = rf"\text{{la raíz está en }} [X_r,\,X_f] \;\Rightarrow\; X_i = X_r = {X(it['xr'])}"
    else:
        concl = rf"\text{{ }} X_r = {X(it['xr'])} \text{{ es la raíz exacta}}"
    out.append(("latex",
                rf"f(X_i)\cdot f(X_r) = ({Fv(it['fi'])})({Fv(it['fr'])}) = {P(it['prod'])} {signo} 0"
                rf" \;\Rightarrow\; {concl}"))

    paso = 6
    if vv is not None:
        out.append(("md", f"**{paso}. Error verdadero** (raíz verdadera $V_v = {X(vv)}$)"))
        out.append(("latex",
                    rf"E_t = \left|\frac{{V_v - X_r}}{{V_v}}\right|\times 100"
                    rf" = \left|\frac{{{X(vv)} - {X(it['xr'])}}}{{{X(vv)}}}\right|\times 100"
                    rf" = {E(it['ept'])}\,\%"))
        paso += 1

    out.append(("md", f"**{paso}. Error aproximado**"))
    if it["xr_ant"] is None:
        out.append(("md", "En la primera iteración no existe una aproximación anterior, por lo que $E_a$ no se calcula."))
    else:
        out.append(("latex",
                    rf"E_a = \left|\frac{{X_r^{{\text{{actual}}}} - X_r^{{\text{{anterior}}}}}}{{X_r^{{\text{{actual}}}}}}\right|\times 100"
                    rf" = \left|\frac{{{X(it['xr'])} - {X(it['xr_ant'])}}}{{{X(it['xr'])}}}\right|\times 100"
                    rf" = {E(it['ea'])}\,\%"))
    paso += 1

    out.append(("md", f"**{paso}. Criterio de parada**"))
    out.append(("latex", _cumple(it, res, F)))
    if it["decision"] != "exacta" and not ultima:
        out.append(("md", f"Siguiente intervalo: $X_i = {X(it['xi_sig'])}$, $X_f = {X(it['xf_sig'])}$"))
    return out


def pasos_prueba_error(res, fn, F):
    """Bloque final 'Prueba de error' y conclusión."""
    X = lambda v: F.x(v, True)   # noqa: E731
    Fv = lambda v: F.f(v, True)  # noqa: E731
    E = lambda v: F.e(v, True)   # noqa: E731
    raiz = res["raiz"]
    fr = res["iteraciones"][-1]["fr"] if res["iteraciones"] else 0.0
    out = [("md", "### Prueba de error"),
           ("md", "Se evalúa la función en la raíz aproximada; el resultado debe ser cercano a cero."),
           ("latex", rf"f({X(raiz)}) = {fn.latex_sustituido(X(raiz))} = {Fv(fr)} \approx 0")]
    if res["valor_verdadero"] is not None and res["iteraciones"]:
        last = res["iteraciones"][-1]
        out.append(("md", "### Error verdadero final"))
        out.append(("latex", rf"E_t = {E(last['ept'])}\,\%"))
    return out


# ----------------------------------------------------------------------
# Secante
# ----------------------------------------------------------------------
def construir_tablas_secante(res, F):
    """Tabla como en el cuaderno: Iter, xᵢ₋₁, xᵢ, f(xᵢ₋₁), f(xᵢ), xᵢ₊₁, Ea, Et (+ f(xᵢ₊₁))."""
    con_vv = res["valor_verdadero"] is not None
    txt, num = [], []
    for it in res["iteraciones"]:
        t = {"Iter": it["n"], "xᵢ₋₁": F.x(it["x_ant"]), "xᵢ": F.x(it["x_act"]),
             "f(xᵢ₋₁)": F.f(it["f_ant"]), "f(xᵢ)": F.f(it["f_act"]),
             "xᵢ₊₁": F.x(it["x_sig"]), "f(xᵢ₊₁)": F.f(it["f_sig"]), "Ea (%)": F.e(it["ea"])}
        n = {"Iter": it["n"], "x_i-1": it["x_ant"], "x_i": it["x_act"],
             "f(x_i-1)": it["f_ant"], "f(x_i)": it["f_act"],
             "x_i+1": it["x_sig"], "f(x_i+1)": it["f_sig"], "Ea (%)": it["ea"]}
        if con_vv:
            t["Et (%)"] = F.e(it["ept"])
            n["Et (%)"] = it["ept"]
        txt.append(t)
        num.append(n)
    return pd.DataFrame(txt), pd.DataFrame(num)


def pasos_iteracion_secante(it, fn, F, res, ultima=False):
    """Desarrollo de una iteración de la secante, con la fórmula del cuaderno."""
    X = lambda v: F.x(v, True)   # noqa: E731
    Fv = lambda v: F.f(v, True)  # noqa: E731
    E = lambda v: F.e(v, True)   # noqa: E731
    par = lambda s: rf"\left({s}\right)" if s.startswith("-") else s  # noqa: E731
    sust = lambda v: fn.latex_sustituido(X(v))  # noqa: E731
    vv = res["valor_verdadero"]
    out = [("md", f"Puntos de trabajo: $x_{{i-1}} = {X(it['x_ant'])}$ y $x_i = {X(it['x_act'])}$")]

    if it["n"] == 1:
        out.append(("md", "**1. Evaluar la función en los dos puntos iniciales**"))
        out.append(("latex", rf"f(x_{{i-1}}) = f({X(it['x_ant'])}) = {sust(it['x_ant'])} = {Fv(it['f_ant'])}"))
        out.append(("latex", rf"f(x_i) = f({X(it['x_act'])}) = {sust(it['x_act'])} = {Fv(it['f_act'])}"))
    else:
        out.append(("md", "**1. Valores de la función en los dos puntos** (ya calculados en la iteración anterior)"))
        out.append(("latex", rf"f(x_{{i-1}}) = {Fv(it['f_ant'])} \qquad f(x_i) = {Fv(it['f_act'])}"))

    out.append(("md", "**2. Verificar el denominador** (no puede ser cero)"))
    out.append(("latex",
                rf"f(x_i) - f(x_{{i-1}}) = {Fv(it['f_act'])} - {par(Fv(it['f_ant']))} = {Fv(it['den'])}"
                r" \neq 0 \;\Rightarrow\; \text{se puede aplicar la fórmula}"))

    out.append(("md", "**3. Calcular la nueva aproximación con la fórmula de la secante**"))
    out.append(("latex", r"x_{i+1} = x_i - f(x_i)\,\frac{x_i - x_{i-1}}{f(x_i) - f(x_{i-1})}"))
    out.append(("latex",
                rf"x_{{i+1}} = {X(it['x_act'])} - ({Fv(it['f_act'])})\,"
                rf"\frac{{{X(it['x_act'])} - {par(X(it['x_ant']))}}}{{{Fv(it['f_act'])} - {par(Fv(it['f_ant']))}}}"
                rf" = {X(it['x_sig'])}"))

    out.append(("md", "**4. Evaluar la función en $x_{i+1}$**"))
    out.append(("latex", rf"f(x_{{i+1}}) = f({X(it['x_sig'])}) = {sust(it['x_sig'])} = {Fv(it['f_sig'])}"))

    out.append(("md", "**5. Error aproximado**"))
    if it["ea"] is None and it["n"] == 1:
        out.append(("md", "En la primera iteración no se calcula $E_a$: todavía no hay una aproximación "
                          "anterior obtenida con el método (los puntos iniciales son solo el punto de partida)."))
    elif it["ea"] is None:
        out.append(("md", "No se puede calcular $E_a$ porque $x_{i+1} = 0$."))
    else:
        out.append(("latex",
                    rf"E_a = \left|\frac{{x_{{i+1}} - x_i}}{{x_{{i+1}}}}\right|\times 100"
                    rf" = \left|\frac{{{X(it['x_sig'])} - {X(it['x_act'])}}}{{{X(it['x_sig'])}}}\right|\times 100"
                    rf" = {E(it['ea'])}\,\%"))

    paso = 6
    if vv is not None:
        out.append(("md", f"**{paso}. Error verdadero** (raíz verdadera $V_v = {X(vv)}$)"))
        out.append(("latex",
                    rf"E_t = \left|\frac{{V_v - x_{{i+1}}}}{{V_v}}\right|\times 100"
                    rf" = \left|\frac{{{X(vv)} - {X(it['x_sig'])}}}{{{X(vv)}}}\right|\times 100"
                    rf" = {E(it['ept'])}\,\%"))
        paso += 1

    out.append(("md", f"**{paso}. Criterio de parada**"))
    out.append(("latex", _cumple(it, res, F, ev="E_t")))
    if not ultima:
        out.append(("md",
                    f"**Actualizar los puntos para la siguiente iteración:** "
                    f"$x_{{i-1}} \\leftarrow x_i = {X(it['x_act'])}$ y $x_i \\leftarrow x_{{i+1}} = {X(it['x_sig'])}$"))
    return out


def pasos_prueba_error_secante(res, fn, F):
    X = lambda v: F.x(v, True)   # noqa: E731
    Fv = lambda v: F.f(v, True)  # noqa: E731
    E = lambda v: F.e(v, True)   # noqa: E731
    raiz = res["raiz"]
    fr = res["iteraciones"][-1]["f_sig"] if res["iteraciones"] else 0.0
    out = [("md", "### Prueba de error"),
           ("md", "Se evalúa la función en la raíz aproximada; el resultado debe ser cercano a cero."),
           ("latex", rf"f({X(raiz)}) = {fn.latex_sustituido(X(raiz))} = {Fv(fr)} \approx 0")]
    if res["valor_verdadero"] is not None and res["iteraciones"]:
        out.append(("md", "### Error verdadero final"))
        out.append(("latex", rf"E_t = {E(res['iteraciones'][-1]['ept'])}\,\%"))
    return out

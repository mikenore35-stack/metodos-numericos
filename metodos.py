"""Métodos numéricos: bisección y secante (sin dependencias de Streamlit)."""
import math
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

MODOS = ("truncar", "redondear", "completa")


class ErrorMetodo(ValueError):
    """Error de uso del método (intervalo inválido, división por cero, etc.)."""


# ----------------------------------------------------------------------
# Control de cifras decimales (para reproducir el cálculo "a mano")
# ----------------------------------------------------------------------
def ajustar(valor, modo, dec):
    """Trunca o redondea `valor` a `dec` decimales según el modo."""
    if valor is None or modo == "completa" or not math.isfinite(valor):
        return valor
    cuantos = Decimal(1).scaleb(-dec)
    regla = ROUND_DOWN if modo == "truncar" else ROUND_HALF_UP
    d = Decimal(repr(round(float(valor), 12)))
    return float(d.quantize(cuantos, rounding=regla))


def ajustar_f(valor, modo, dec):
    """Como `ajustar`, pero conserva 2 cifras significativas si el valor es muy
    pequeño (así 0.0019 no se vuelve 0.001 ni 0.000)."""
    if valor is None or modo == "completa" or valor == 0 or not math.isfinite(valor):
        return valor
    if abs(valor) < 10 ** (-(dec - 1)):
        dec = 1 - math.floor(math.log10(abs(valor)))
    return ajustar(valor, modo, dec)


def _pct(valor, modo):
    return ajustar(valor, modo, 2)


# ----------------------------------------------------------------------
# Bisección
# ----------------------------------------------------------------------
def biseccion(f, xi, xf, *, criterio="ea", limite=1.0, valor_verdadero=None,
              max_iter=50, modo="completa", dec=6):
    """Método de bisección.

    criterio: "ea"   -> parar cuando el error aproximado (%) sea menor que `limite`
              "et"   -> parar cuando el error verdadero Et (%) sea menor que `limite`
              "iter" -> parar al completar `limite` iteraciones
    modo:     "truncar" | "redondear" | "completa" (cifras decimales en cada paso)
    Devuelve un diccionario con las iteraciones y el resultado.
    """
    if modo not in MODOS:
        raise ErrorMetodo("Modo de cálculo desconocido.")
    if criterio == "et" and valor_verdadero is None:
        raise ErrorMetodo("Para parar por error verdadero debes indicar el valor verdadero.")
    if criterio == "et" and valor_verdadero == 0:
        raise ErrorMetodo("El valor verdadero no puede ser 0 para calcular el error verdadero relativo.")
    if valor_verdadero == 0:
        valor_verdadero = None
    if xi >= xf:
        raise ErrorMetodo("Se debe cumplir Xi < Xf.")

    vv = valor_verdadero
    ev = lambda v: ajustar_f(f(v), modo, dec)  # noqa: E731
    fi, ff = ev(xi), ev(xf)

    base = {"modo": modo, "dec": dec, "criterio": criterio, "limite": limite,
            "valor_verdadero": vv, "xi0": xi, "xf0": xf, "fi0": fi, "ff0": ff}

    # Alguno de los extremos ya es raíz
    for x0, f0, nombre in ((xi, fi, "Xi"), (xf, ff, "Xf")):
        if f0 == 0:
            return {**base, "iteraciones": [], "raiz": x0, "convergio": True,
                    "motivo": f"f({nombre}) = 0: {nombre} = {x0:g} ya es una raíz exacta."}

    if fi * ff > 0:
        raise ErrorMetodo(
            f"No hay cambio de signo en [{xi:g}, {xf:g}]: f(Xi) = {fi:.6g} y f(Xf) = {ff:.6g} "
            "tienen el mismo signo. Elige un intervalo donde f(Xi)·f(Xf) < 0.")

    iteraciones, xr_ant = [], None
    total = int(limite) if criterio == "iter" else int(max_iter)
    motivo, convergio = None, False

    for n in range(1, total + 1):
        prod_ext = fi * ff
        xr = ajustar((xi + xf) / 2, modo, dec)
        fr = ev(xr)
        prod = fi * fr

        ea = None
        if xr_ant is not None and xr != 0:
            ea = _pct(abs((xr - xr_ant) / xr) * 100, modo)
        ev_firmado = ept = None
        if vv is not None:
            # Et = (valor verdadero - Xr) / valor verdadero * 100; en clase se ignora el signo
            ev_firmado = _pct((vv - xr) / vv * 100, modo)
            ept = abs(ev_firmado)

        if prod < 0:
            decision, xi_sig, xf_sig = "izquierda", xi, xr
        elif prod > 0:
            decision, xi_sig, xf_sig = "derecha", xr, xf
        else:
            decision, xi_sig, xf_sig = "exacta", xi, xf

        iteraciones.append({
            "n": n, "xi": xi, "xf": xf, "xr": xr, "xr_ant": xr_ant,
            "fi": fi, "ff": ff, "fr": fr,
            "prod_ext": prod_ext, "prod": prod,
            "ea": ea, "ev_firmado": ev_firmado, "ept": ept,
            "decision": decision, "xi_sig": xi_sig, "xf_sig": xf_sig,
        })

        if decision == "exacta":
            motivo, convergio = f"f(Xr) = 0 en la iteración {n}: Xr = {xr:g} es la raíz exacta.", True
            break
        if criterio == "ea" and ea is not None and ea < limite:
            motivo, convergio = f"Ea = {ea:g} % es menor que {limite:g} %.", True
            break
        if criterio == "et" and ept is not None and ept < limite:
            motivo, convergio = f"Et = {ept:g} % es menor que {limite:g} %.", True
            break
        if criterio == "iter" and n >= total:
            motivo, convergio = f"Se completaron las {total} iteraciones pedidas.", True
            break

        xr_ant = xr
        if decision == "izquierda":
            xf, ff = xr, fr
        else:
            xi, fi = xr, fr

    if motivo is None:
        motivo = (f"Se llegó al máximo de {total} iteraciones sin cumplir el criterio de parada.")

    return {**base, "iteraciones": iteraciones, "raiz": iteraciones[-1]["xr"],
            "convergio": convergio, "motivo": motivo}


# ----------------------------------------------------------------------
# Secante
# ----------------------------------------------------------------------
def secante(f, x_ant, x_act, *, criterio="ea", limite=1.0, valor_verdadero=None, max_iter=50):
    """Método de la secante:  x_{i+1} = x_i - f(x_i)·(x_i - x_{i-1}) / (f(x_i) - f(x_{i-1})).

    x_ant, x_act: los dos puntos iniciales (x₋₁ y x₀); no necesitan cambio de signo.
    criterio: "ea" | "et" | "iter" (igual que en la bisección).
    El error aproximado Ea = |(x_{i+1} - x_i)/x_{i+1}|·100 se calcula desde la 2.ª iteración.
    """
    if x_ant == x_act:
        raise ErrorMetodo("Los dos puntos iniciales deben ser distintos.")
    if criterio == "et" and not valor_verdadero:
        raise ErrorMetodo("Para parar por error verdadero debes indicar un valor verdadero distinto de 0.")
    vv = valor_verdadero or None

    f_ant, f_act = f(x_ant), f(x_act)
    base = {"criterio": criterio, "limite": limite, "valor_verdadero": vv,
            "x_ant0": x_ant, "x_act0": x_act, "f_ant0": f_ant, "f_act0": f_act, "advertencia": None}

    for nombre, x0, f0 in (("x₋₁", x_ant, f_ant), ("x₀", x_act, f_act)):
        if f0 == 0:
            return {**base, "iteraciones": [], "raiz": x0, "convergio": True,
                    "motivo": f"f({nombre}) = 0: {nombre} = {x0:g} ya es una raíz exacta."}

    its, motivo, convergio = [], None, False
    total = int(limite) if criterio == "iter" else int(max_iter)

    for n in range(1, total + 1):
        den = f_act - f_ant
        if den == 0 or abs(den) <= 1e-12 * max(abs(f_act), abs(f_ant)):
            texto = (f"División por cero (o casi cero) en la iteración {n}: f(xᵢ) − f(xᵢ₋₁) = {den:g}. "
                     "Prueba con otros puntos iniciales.")
            if not its:
                raise ErrorMetodo(texto)
            motivo = texto + " El método se detuvo."
            break
        x_sig = x_act - f_act * (x_act - x_ant) / den
        try:
            f_sig = f(x_sig)
        except ValueError as e:
            if not its:
                raise ErrorMetodo(str(e)) from None
            motivo = f"{e} (iteración {n}). El método se detuvo."
            break

        # Ea compara dos aproximaciones calculadas por el método: se obtiene desde la 2.ª iteración
        ea = abs((x_sig - x_act) / x_sig) * 100 if (its and x_sig != 0) else None
        ev_firmado = ept = None
        if vv is not None:
            ev_firmado = (vv - x_sig) / vv * 100
            ept = abs(ev_firmado)

        its.append({"n": n, "x_ant": x_ant, "x_act": x_act, "f_ant": f_ant, "f_act": f_act,
                    "den": den, "x_sig": x_sig, "f_sig": f_sig,
                    "ea": ea, "ev_firmado": ev_firmado, "ept": ept})

        if f_sig == 0:
            motivo, convergio = f"f(xᵢ₊₁) = 0 en la iteración {n}: x = {x_sig:g} es la raíz exacta.", True
            break
        if criterio == "ea" and ea is not None and ea < limite:
            motivo, convergio = f"Ea = {ea:g} % es menor que {limite:g} %.", True
            break
        if criterio == "et" and ept is not None and ept < limite:
            motivo, convergio = f"Et = {ept:g} % es menor que {limite:g} %.", True
            break
        if criterio == "iter" and n >= total:
            motivo, convergio = f"Se completaron las {total} iteraciones pedidas.", True
            break
        x_ant, f_ant, x_act, f_act = x_act, f_act, x_sig, f_sig

    if motivo is None:
        motivo = "Se llegó al máximo de %d iteraciones sin cumplir el criterio de parada." % total

    advertencia = None
    if its and abs(its[-1]["f_sig"]) > max(abs(base["f_ant0"]), abs(base["f_act0"])):
        advertencia = ("La secante parece alejarse de la raíz (|f| creció respecto a los puntos iniciales). "
                       "Prueba con puntos iniciales más cercanos a la raíz.")

    return {**base, "iteraciones": its, "convergio": convergio, "motivo": motivo,
            "raiz": its[-1]["x_sig"] if its else x_act, "advertencia": advertencia}


# ----------------------------------------------------------------------
# Explorador de la función (tabulación previa)
# ----------------------------------------------------------------------
MAX_PUNTOS = 2000


def _parece_discontinuidad(f, a, b, fa, fb):
    """Biseca 40 veces el intervalo con cambio de signo: si al final |f| sigue siendo grande,
    el cambio de signo viene de un salto (por ejemplo 1/x) y no de una raíz."""
    lo, flo, hi = a, fa, b
    for _ in range(40):
        mid = (lo + hi) / 2
        try:
            fm = f(mid)
        except ValueError:
            return True
        if fm == 0:
            return False
        if flo * fm < 0:
            hi = mid
        else:
            lo, flo = mid, fm
    try:
        return abs(f((lo + hi) / 2)) > 0.5 * max(abs(fa), abs(fb))
    except ValueError:
        return True


def explorar(f, x_min, x_max, paso):
    """Tabula f(x) en [x_min, x_max] con el paso dado y detecta cambios de signo.

    Devuelve {"xs", "ys", "cambios", "exactas", "indefinidos"}; ys usa None donde f no está definida.
    """
    if x_min >= x_max:
        raise ErrorMetodo("x mínimo debe ser menor que x máximo.")
    if paso <= 0:
        raise ErrorMetodo("El paso debe ser positivo.")
    n = int(round((x_max - x_min) / paso))
    if n + 1 > MAX_PUNTOS:
        raise ErrorMetodo(f"Demasiados puntos ({n + 1}). Aumenta el paso (máximo {MAX_PUNTOS} puntos).")
    xs = [round(x_min + paso * i, 12) for i in range(n + 1)]
    if xs[-1] > x_max + 1e-9:
        xs.pop()
    ys = []
    for x in xs:
        try:
            ys.append(f(x))
        except ValueError:
            ys.append(None)

    cambios, exactas = [], []
    for i, (x, y) in enumerate(zip(xs, ys)):
        if y == 0:
            exactas.append({"i": i, "x": x})
    for i in range(len(xs) - 1):
        ya, yb = ys[i], ys[i + 1]
        if ya is None or yb is None or ya == 0 or yb == 0:
            continue
        if ya * yb < 0:
            cambios.append({"i": i, "a": xs[i], "b": xs[i + 1], "fa": ya, "fb": yb,
                            "sospechoso": _parece_discontinuidad(f, xs[i], xs[i + 1], ya, yb)})
    return {"xs": xs, "ys": ys, "cambios": cambios, "exactas": exactas,
            "indefinidos": sum(1 for y in ys if y is None)}

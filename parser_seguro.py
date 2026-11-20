"""Lectura SEGURA de funciones f(x) escritas como texto.

Antes de interpretar la expresión se valida con una lista blanca (solo x,
números, operadores y funciones matemáticas conocidas), de modo que nunca se
ejecuta código arbitrario.
"""
import math
import re

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

X = sp.Symbol("x")
MAX_LONGITUD = 150
TRANSFORMACIONES = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


class FuncionInvalida(ValueError):
    """La expresión escrita no es válida o no está permitida."""


def _log10(a, **_):
    return sp.log(a) / sp.log(10)


_FUNCIONES = {
    "sin": sp.sin, "sen": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "exp": sp.exp, "ln": sp.log, "log": _log10,
    "sqrt": sp.sqrt, "abs": sp.Abs,
}
_CONSTANTES = {"e": sp.E, "pi": sp.pi}
_PERMITIDOS = {"x"} | set(_FUNCIONES) | set(_CONSTANTES)
_CARACTERES = re.compile(r"[a-z0-9\s\.\+\-\*/\^\(\)]*")
_PALABRAS = re.compile(r"[a-z]+")
_NUMERO = re.compile(r"\d+\.?\d*(?:e[+-]?\d+)?|\.\d+(?:e[+-]?\d+)?")


def _normalizar(texto: str) -> str:
    t = (texto or "").strip().lower()
    for viejo, nuevo in (("−", "-"), ("×", "*"), ("·", "*"), ("²", "^2"),
                         ("³", "^3"), (",", "."), ("**", "^")):
        t = t.replace(viejo, nuevo)
    if not t:
        raise FuncionInvalida("Coloca la función f(x).")
    t = re.sub(r"^f\s*\(\s*x\s*\)\s*=(?!=)", "", t).strip()  # admite «f(x) = ...»
    if t.count("=") > 1:
        raise FuncionInvalida("Solo puede haber un signo = en la ecuación.")
    if "=" in t:  # ecuación «izquierda = derecha»  ->  izquierda - (derecha) = 0
        izquierda, derecha = (lado.strip() for lado in t.split("="))
        if not izquierda or not derecha:
            raise FuncionInvalida("Escribe una expresión a ambos lados del signo =.")
        t = f"({izquierda}) - ({derecha})"
    if not t:
        raise FuncionInvalida("Coloca la función f(x).")
    if len(t) > MAX_LONGITUD:
        raise FuncionInvalida(f"La expresión es demasiado larga (máximo {MAX_LONGITUD} caracteres).")
    if not _CARACTERES.fullmatch(t):
        raise FuncionInvalida(
            "La expresión contiene caracteres no permitidos. Usa solo x, números, "
            "+ - * / ^, paréntesis y funciones como sin, cos, tan, exp, ln, log, sqrt.")
    for m in re.finditer(r"([a-z])(\d)", t):
        es_exponente = m.group(1) == "e" and m.start() > 0 and (t[m.start() - 1].isdigit() or t[m.start() - 1] == ".")
        if not es_exponente:
            raise FuncionInvalida(
                f"Revisa «{m.group(0)}»: escribe el operador, por ejemplo x*2 o x^2.")
    for palabra in _PALABRAS.findall(t):
        if palabra not in _PERMITIDOS:
            raise FuncionInvalida(
                f"Nombre no permitido: «{palabra}». Usa x, e, pi o las funciones "
                "sin (sen), cos, tan, asin, acos, atan, sinh, cosh, tanh, exp, ln, log, sqrt, abs.")
    return t


def _a_flotantes(t: str) -> str:
    """Convierte los enteros en flotantes (evita cálculos enormes con enteros exactos)."""
    def rep(m):
        s = m.group(0)
        return s if ("." in s or "e" in s) else s + ".0"
    return _NUMERO.sub(rep, t)


def _parse(t: str, **local):
    nombres = {**_FUNCIONES, **_CONSTANTES, "x": X, **local}
    return parse_expr(t, local_dict=nombres, transformations=TRANSFORMACIONES, evaluate=False)


def _latex(expr) -> str:
    s = sp.latex(expr, order="none")
    s = re.sub(r"\\sin(?![a-z])", r"\\operatorname{sen}", s)
    return re.sub(r"\\log(?![a-z])", r"\\ln", s)


class FuncionParseada:
    def __init__(self, texto, f_num, latex):
        self.texto = texto
        self._f = f_num
        self.latex = latex

    def __call__(self, valor: float) -> float:
        try:
            with np.errstate(all="ignore"):
                r = float(self._f(float(valor)))
        except Exception:
            raise ValueError(f"f(x) no está definida en x = {valor:g}.") from None
        if not math.isfinite(r):
            raise ValueError(f"f(x) no está definida (o no es finita) en x = {valor:g}.")
        return r

    def latex_sustituido(self, valor_latex: str) -> str:
        """LaTeX de f con x reemplazada por el número ya formateado (sin simplificar)."""
        nombre = valor_latex
        if nombre.startswith("-"):
            nombre = r"\left(" + nombre + r"\right)"
        return _latex(_parse(self.texto, x=sp.Symbol(nombre)))


def parsear_funcion(texto: str) -> FuncionParseada:
    t = _normalizar(texto)
    try:
        expr_num = _parse(_a_flotantes(t))
        if not expr_num.free_symbols <= {X}:
            raise FuncionInvalida("La función solo puede depender de la variable x.")
        f_num = sp.lambdify(X, expr_num, modules=["numpy"])
        with np.errstate(all="ignore"):
            f_num(1.0)  # prueba rápida: detecta desbordes y errores de sintaxis
        latex = _latex(_parse(t))
    except FuncionInvalida:
        raise
    except OverflowError:
        raise FuncionInvalida("La expresión produce números demasiado grandes.") from None
    except Exception:
        raise FuncionInvalida(
            "No se pudo interpretar la expresión. Revisa paréntesis y operadores "
            "(ejemplo: sen(x) - x^2).") from None
    return FuncionParseada(t, f_num, latex)

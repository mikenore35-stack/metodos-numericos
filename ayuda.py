"""Ventana de ayuda de la página (tutorial de uso)."""
import streamlit as st


def contenido_ayuda():
    t1, t2, t_exp, t3, t4, t5 = st.tabs([
        "🚀 Primeros pasos", "✏️ Escribir la función", "🔍 Explorador", "📐 Bisección", "📏 Secante",
        "❓ Problemas comunes",
    ])

    # ------------------------------------------------------------------
    with t1:
        st.markdown("""
**1. Elige el método** en el menú lateral: *Bisección* o *Secante*.

**2. Escribe la función** f(x). Mira la pestaña *Escribir la función* para ver cómo.

**3. Ingresa los datos iniciales**
- *Bisección:* el intervalo **Xi** y **Xf**, donde la función cambie de signo.
- *Secante:* dos puntos distintos **x₋₁** y **x₀** (no necesitan cambio de signo).
- ¿No sabes qué intervalo usar? Abre el **Explorador** en el menú lateral: tabula la función y te sugiere intervalos con cambio de signo.

**4. Elige el criterio de parada** y su valor:
- *Error aproximado (%)*: se detiene cuando Ea sea menor que el porcentaje indicado.
- *Error verdadero (%)*: se detiene cuando Et sea menor que el porcentaje indicado (necesita el valor verdadero).
- *Número fijo de iteraciones*: realiza exactamente las iteraciones que pidas.

**5. (Opcional) Escribe el valor verdadero de la raíz** si el ejercicio lo da. Así se calcula el error verdadero Et en cada iteración.

**6. Presiona Calcular** y revisa los resultados:
- El **resumen** con la raíz aproximada, las iteraciones y los errores finales.
- La pestaña **Tabla de iteraciones** con todos los valores.
- La pestaña **Paso a paso**, con cada iteración desarrollada con fórmulas y números.
- La pestaña **Gráfica** con la función y las aproximaciones.
- El botón **📄 Generar PDF**: crea un PDF con todo el ejercicio (datos, resultado, tabla, paso a paso y gráfica). Cuando esté listo aparece **⬇️ Descargar PDF**. Con muchas iteraciones puede tardar unos segundos.

**Otros ajustes**
- *Cargar un ejemplo:* en cada método y en el explorador llena los campos con un ejercicio de prueba, para ver cómo funciona sin escribir nada.
- *🧹 Limpiar:* deja el formulario en blanco para empezar otro ejercicio.
- *Deslizador de iteraciones:* en la pestaña Gráfica, muévelo para ver cómo avanza cada iteración.
- *Decimales a mostrar:* cuántas cifras ver en los resultados (los cálculos siempre usan todos los decimales).
- *Máx. iteraciones:* límite de seguridad por si el criterio de parada nunca se cumple.
- *Usar coma como separador decimal* (menú lateral): muestra los resultados con coma, como en clase.
        """)

    # ------------------------------------------------------------------
    with t2:
        st.markdown("""
Escribe la función con la variable **`x`**. Puedes usar `^` o `**` para las potencias y funciones como
`sen`, `cos`, `tan`, `exp`, `ln`, `log`, `sqrt`. **Escribe los decimales con punto** (por ejemplo `0.5`).

**Funciones disponibles**

| Escribe | Significa |
|---|---|
| `sen(x)` o `sin(x)`, `cos(x)`, `tan(x)` | seno, coseno y tangente (en radianes) |
| `asin(x)`, `acos(x)`, `atan(x)` | funciones trigonométricas inversas |
| `sinh(x)`, `cosh(x)`, `tanh(x)` | funciones hiperbólicas |
| `exp(x)` | e elevado a x |
| `ln(x)` | logaritmo natural |
| `log(x)` | logaritmo en base 10 |
| `sqrt(x)` | raíz cuadrada |
| `abs(x)` | valor absoluto |
| `e` y `pi` | las constantes e y π |

**Ejemplos**

| Ecuación | Cómo escribirla |
|---|---|
| x³ − x − 2 | `x^3 - x - 2` |
| sen x = x² | `sen(x) = x^2` |
| ln(x²) = 0,7 | `ln(x^2) = 0.7` |
| e⁻ˣ − x | `exp(-x) - x` |
| √x − 2 | `sqrt(x) - 2` |
| (x + 1)(x − 2) | `(x+1)*(x-2)` |

**Consejos**
- Si la ecuación tiene un signo `=`, puedes escribirla completa: la página la pasa a la forma f(x) = 0 y muestra la función resultante.
- Usa paréntesis en los argumentos: `sen(x)`, no `senx`. Entre variables y funciones usa `*`: `x*sen(x)`.
- **Máximos y mínimos:** si el ejercicio pide el máximo o el mínimo de f(x), el método se aplica a la **derivada**, porque ahí f'(x) = 0. Por ejemplo, para f(x) = −2x⁶ − 1,5x⁴ + 10x + 2 escribe `-12x^5 - 6x^3 + 10`.
- Cuidado con el dominio: `ln(x)` y `sqrt(x)` no existen para valores negativos, ni `1/x` en x = 0.
        """)

    # ------------------------------------------------------------------
    with t_exp:
        st.markdown("""
**¿Para qué sirve?** Para encontrar el intervalo [Xi, Xf] de la bisección o los puntos iniciales de la secante,
como cuando tabulas f(x) en el cuaderno.

1. Escribe la función, el rango (**x mínimo** y **x máximo**) y el **paso** entre valores. También puedes elegir un ejercicio en **Cargar un ejemplo**, y **🧹 Limpiar** deja todo en blanco.
2. La página calcula f(x) en cada punto y muestra la tabla (con el signo de cada valor) y la gráfica.
3. Si f(x) cambia de signo entre dos puntos, aparece un intervalo detectado. Presiona **→ Bisección** o
   **→ Secante** y la función y el intervalo pasan solos al método elegido.

**Consejos**
- Si no detecta nada, prueba con un paso más pequeño (por ejemplo 0,1) o con otro rango.
- Un cambio de signo no siempre es una raíz: en funciones como `1/x` o `tan(x)` el signo cambia por un salto.
  La página lo marca como *posible discontinuidad*.
- Una raíz donde la curva solo toca el eje, sin cruzarlo (como en x²), no produce cambio de signo, y en ese caso la bisección no aplica.
- Si la función no existe en algunos puntos (por ejemplo `ln(x)` con x ≤ 0), esos puntos se omiten.
- El explorador admite hasta 2000 puntos.
        """)

    # ------------------------------------------------------------------
    with t3:
        st.markdown("""
**¿Qué hace?** Encuentra una raíz de f(x) = 0 dentro de un intervalo [Xi, Xf] **donde la función cambia de signo**,
es decir, f(Xi)·f(Xf) < 0. Va reduciendo el intervalo a la mitad en cada iteración.

**¿Cómo elegir el intervalo?** Evalúa f(x) en varios valores de x (una tabulación, como en clase) hasta que veas que
cambia de positivo a negativo, o al revés. Esos dos valores son Xi y Xf, con Xi < Xf.

**En cada iteración:**
        """)
        st.latex(r"X_r = \frac{X_i + X_f}{2}")
        st.markdown("""
- Si f(Xi)·f(Xr) < 0, la raíz está en [Xi, Xr] y **Xf = Xr**.
- Si f(Xi)·f(Xr) > 0, la raíz está en [Xr, Xf] y **Xi = Xr**.
- Si f(Xr) = 0, Xr es la raíz exacta.

**Errores**
        """)
        st.latex(r"E_a = \left|\frac{X_r^{\text{actual}} - X_r^{\text{anterior}}}{X_r^{\text{actual}}}\right|\times 100")
        st.latex(r"E_t = \left|\frac{V_v - X_r}{V_v}\right|\times 100")
        st.markdown("""
- **Ea** (error aproximado) necesita dos aproximaciones, por eso se calcula desde la 2.ª iteración.
- **Et** (error verdadero) usa el valor verdadero V<sub>v</sub> de la raíz; el signo se ignora.
        """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    with t4:
        st.markdown("""
**¿Qué hace?** Encuentra una raíz de f(x) = 0 a partir de **dos puntos iniciales distintos**, x₋₁ y x₀.
**No necesita cambio de signo**, pero funciona mejor si los puntos están cerca de la raíz.

**En cada iteración** traza la recta que pasa por (xᵢ₋₁, f(xᵢ₋₁)) y (xᵢ, f(xᵢ)) y toma el punto donde corta el eje x:
        """)
        st.latex(r"x_{i+1} = x_i - f(x_i)\,\frac{x_i - x_{i-1}}{f(x_i) - f(x_{i-1})}")
        st.markdown("""
Después se desplazan los puntos: xᵢ₋₁ pasa a ser xᵢ, y xᵢ pasa a ser xᵢ₊₁.

**Errores**
        """)
        st.latex(r"E_a = \left|\frac{x_{i+1} - x_i}{x_{i+1}}\right|\times 100")
        st.latex(r"E_t = \left|\frac{V_v - x_{i+1}}{V_v}\right|\times 100")
        st.markdown("""
- **Ea** se calcula desde la 2.ª iteración. **Et** necesita el valor verdadero V<sub>v</sub>; el signo se ignora.

**Precauciones**
- Si f(xᵢ) = f(xᵢ₋₁), el denominador es cero y el método no puede continuar: cambia los puntos iniciales.
- Si los puntos están lejos de la raíz, el método puede alejarse en lugar de acercarse.
        """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    with t5:
        st.markdown("""
| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| No hay cambio de signo en [Xi, Xf] | f(Xi) y f(Xf) tienen el mismo signo, así que no se asegura una raíz en el intervalo | Elige otro intervalo (tabula f(x) hasta ver el cambio de signo). Si el ejercicio pide un máximo o mínimo, usa la derivada |
| f(x) no está definida en x = … | La función no existe en ese punto (por ejemplo ln(0), 1/0 o la raíz de un negativo) | Cambia los valores iniciales para que no incluyan ese punto |
| División por cero en la iteración … | En la secante, f(xᵢ) = f(xᵢ₋₁) | Cambia los puntos iniciales |
| Se llegó al máximo de iteraciones | No se cumplió el criterio de parada | Aumenta el máximo de iteraciones o usa un porcentaje mayor |
| La secante parece alejarse de la raíz | Los puntos iniciales están lejos de la raíz | Elige puntos más cercanos a la raíz |
| Caracteres no permitidos / No se pudo interpretar | La función tiene un símbolo o nombre que no se reconoce | Revisa paréntesis, operadores y los nombres de la lista de funciones |
| El valor verdadero no puede ser 0 | El error verdadero divide entre ese valor | Deja el campo vacío o escribe un valor distinto de 0 |

Si la página se queda con datos viejos o algo no responde, recárgala con **F5**.
        """)


def boton_ayuda():
    """Botón «Ayuda» en el menú lateral que abre el tutorial en una ventana."""
    if hasattr(st, "dialog"):
        @st.dialog("❓ Ayuda", width="large")
        def _ventana():
            contenido_ayuda()

        if st.sidebar.button("❓ Ayuda"):
            _ventana()
    else:  # versiones antiguas de Streamlit: se muestra desplegable
        with st.sidebar.expander("❓ Ayuda"):
            contenido_ayuda()

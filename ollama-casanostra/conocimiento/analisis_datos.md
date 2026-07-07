# Apuntes maestros de análisis de datos (Excel y Python)

## El proceso completo (de tabla a decisión)
1. PREGUNTA primero: "¿qué decisión quiero tomar con esto?" Un análisis sin
   pregunta es turismo por los datos.
2. DATOS: consíguelos y mira 20 filas a ojo antes de nada (formatos, huecos,
   cosas raras).
3. LIMPIEZA (el 70% del trabajo real): duplicados fuera, nulos decididos
   (¿borrar, rellenar, marcar?), formatos unificados (fechas, mayúsculas,
   espacios), categorías normalizadas ("Madrid"/"madrid "/"MADRID" = una).
4. ANÁLISIS: empieza por lo simple — totales, medias, medianas, por grupo y
   en el tiempo. Lo simple bien hecho gana a lo sofisticado mal entendido.
5. VISUAL: un gráfico por mensaje, con título que CONCLUYE ("Las ventas caen
   20% desde marzo", no "Gráfico de ventas").
6. DECISIÓN: cierra con "por tanto, deberíamos...". Si el análisis no cambia
   ninguna acción, no era necesario.

## Excel: las 6 herramientas que resuelven el 90%
- TABLAS (Ctrl+T): dan nombre, filtros y orden a todo.
- TABLAS DINÁMICAS: resumen por grupos en 30 segundos; la herramienta más
  rentable de Excel.
- BUSCARV / XLOOKUP: cruzar dos tablas por un campo común.
- SI + SUMAR.SI / CONTAR.SI: lógica y totales condicionales.
- Formato condicional: que los problemas se vean en rojo solos.
- Validación de datos: listas desplegables que evitan errores de entrada.

## Python/pandas: el kit mínimo
- df = pd.read_csv("datos.csv"); df.head(); df.info(); df.describe()
- Limpiar: df.drop_duplicates(); df.dropna() o df.fillna(valor);
  df["col"].str.strip().str.lower()
- Agrupar: df.groupby("categoria")["ventas"].sum().sort_values()
- Cruzar: pd.merge(df1, df2, on="id")
- Gráfico rápido: df.plot(kind="bar") con matplotlib.

## Qué gráfico usar
- Evolución en el tiempo → líneas. Comparar categorías → barras.
- Proporción del total → barras apiladas (la tarta engaña con >4 trozos).
- Relación entre 2 variables → dispersión. Distribución → histograma.

## Trampas que invalidan conclusiones (memoriza)
- CORRELACIÓN NO ES CAUSALIDAD: helados y ahogamientos suben juntos (verano).
- La MEDIA miente con extremos: usa mediana para sueldos, precios de casas.
- Ejes truncados exageran diferencias; empezar en cero salvo buena razón.
- Muestras sesgadas: encuestar solo a clientes contentos "demuestra" que todos
  están contentos.
- Porcentajes sin base: "+50%" puede ser de 2 a 3 casos. Da siempre el N.
- Cherry-picking de fechas: elegir el rango que confirma lo que querías.

## Checklist antes de presentar conclusiones
¿Responde a la pregunta inicial? ¿El N es suficiente? ¿Comparé contra algo
(periodo anterior, otro grupo)? ¿Alguien podría explicar el resultado por otra
causa? ¿Los números cuadran con el sentido común? Si algo sorprende mucho,
antes de presentarlo, sospecha de un error propio: revisa la limpieza.

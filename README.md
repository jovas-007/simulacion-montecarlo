# Simulación Monte Carlo – Arquitectura productor/consumidor

Este repositorio contiene un ejemplo completo de simulación Monte Carlo que
modela la utilidad (ganancia) de un producto con demanda, precio y costos
incertidumbre. El flujo está dividido en dos hilos:

* **Productor**: genera escenarios utilizando distribuciones de probabilidad
  (demanda normal, precio triangular, costos uniformes, etc.).
* **Consumidor**: calcula la utilidad para cada escenario y acumula los
  resultados para obtener la utilidad mínima, máxima y la media esperada.

Al finalizar la ejecución se muestra por consola el resumen estadístico y se
grafica la convergencia de la utilidad media esperada.

## Requisitos

* Python 3.10 o superior.
* Las dependencias del entorno base (utiliza solo bibliotecas estándar) y
  `matplotlib` para generar la gráfica.

Instala la dependencia adicional con:

```bash
pip install matplotlib
```

## Ejecución

```bash
python montecarlo.py
```

El programa utiliza una semilla determinista (`4`) para generar siempre la
misma gráfica de referencia. Si deseas explorar otros comportamientos o
intentar reproducir una figura distinta a la de ejemplo, puedes ajustar el
número de escenarios y la semilla del generador de números aleatorios desde la
línea de comandos:

```bash
python montecarlo.py --simulaciones 20000 --semilla 123
```

Ten en cuenta que al variar la semilla los escenarios cambian y, por lo tanto,
la forma de la gráfica puede diferir del material de referencia que hayas
proporcionado.


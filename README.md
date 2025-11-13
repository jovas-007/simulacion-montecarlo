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

Puedes modificar el número de simulaciones ejecutadas editando la constante
`simulations` en la función `main`.


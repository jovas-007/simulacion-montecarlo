# Simulación Monte Carlo – Arquitectura productor/consumidor

Este proyecto implementa el ejemplo de simulación Monte Carlo del prototipo de
impresora descrito en las diapositivas proporcionadas. El cálculo se realiza
mediante una arquitectura productor/consumidor:

- **Productor:** genera combinaciones de costes de mano de obra, componentes y
  demanda siguiendo las distribuciones especificadas.
- **Consumidor:** calcula la utilidad para cada combinación y actualiza las
  estadísticas acumuladas (mínimo, máximo y media esperada).

## Requisitos

El proyecto utiliza únicamente la biblioteca estándar de Python 3.10 o
superior.

## Uso

```bash
python -m src.montecarlo [iteraciones] [--seed SEMILLA]
```

- `iteraciones` (opcional): número de escenarios a simular (por defecto 10 000).
- `--seed`: semilla para reproducibilidad de los resultados.

El programa muestra por pantalla la utilidad mínima, máxima y media esperada
tras procesar todas las simulaciones.

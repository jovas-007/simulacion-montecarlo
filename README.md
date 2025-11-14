# Simulación Monte Carlo – Arquitectura productor/consumidor

Este proyecto implementa el ejemplo de simulación Monte Carlo para estimar la
utilidad anual esperada de una impresora portátil siguiendo una arquitectura de
productor/consumidor.

## Descripción

- **Productor:** genera combinaciones de variables aleatorias (coste de mano de
  obra, coste de componentes y demanda del primer año) utilizando las
  distribuciones digitadas del caso de estudio: discreta para la mano de obra,
  uniforme para componentes y normal truncada para la demanda.
- **Consumidor:** calcula la utilidad de cada combinación, acumula los
  resultados y obtiene la utilidad mínima, máxima y media esperada.
- **Resultados:** el programa guarda una gráfica de convergencia de la utilidad
  media y un reporte en texto plano con las métricas principales de la
  simulación.

## Ejecución

```bash
python src/monte_carlo.py
```

Los artefactos se generan en el directorio `output/`:

- `convergencia_utilidad.svg`: gráfica de la convergencia de la utilidad media.
- `reporte_simulacion.txt`: resumen de la simulación con utilidad mínima,
  máxima y media esperada, además de los supuestos utilizados.

## Parámetros del ejemplo

Los supuestos base se guardan en `data/parametros_ejemplo.json`, digitados a
partir de la imagen de referencia del enunciado. Si necesitas replicar otro
escenario basta con editar ese archivo (o proporcionar uno alternativo en
`SimulationConfig.parameters_file`) respetando la misma estructura JSON:

```json
{
  "precio_venta": 70000,
  "costos_fijos": {
    "administracion": 160000000,
    "marketing": 80000000
  },
  "distribuciones": {
    "mano_obra": {
      "tipo": "discreta",
      "valores": [10000, 13000, 16000, 19000, 22000],
      "probabilidades": [0.10, 0.30, 0.30, 0.20, 0.10]
    },
    "componentes": { "tipo": "uniforme", "min": 25000, "max": 35000 },
    "demanda": { "tipo": "normal", "media": 14500, "desviacion": 4000, "min": 0 }
  }
}
```

El programa carga automáticamente estos valores y genera resultados cercanos a
los mostrados en la imagen de referencia (utilidad media ≈ 1.16×10⁸).

## Configuración opcional

El módulo expone la función `run_simulation` y la clase `SimulationConfig` para
personalizar el número de iteraciones, semilla aleatoria y nombres de los
archivos de salida.

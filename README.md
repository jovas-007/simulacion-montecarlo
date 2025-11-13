# Simulación Monte Carlo – Arquitectura productor/consumidor

Este proyecto implementa el ejemplo de simulación Monte Carlo para estimar la
utilidad anual esperada de una impresora portátil siguiendo una arquitectura de
productor/consumidor.

## Descripción

- **Productor:** genera combinaciones de variables aleatorias (coste de mano de
  obra, coste de componentes y demanda del primer año) usando distribuciones
  triangulares basadas en los rangos y modas del problema.
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
    "administracion": 16000000,
    "marketing": 8000000
  },
  "distribuciones": {
    "mano_obra": { "min": 10000, "moda": 15000, "max": 22000 },
    "componentes": { "min": 25000, "moda": 30000, "max": 35000 },
    "demanda": { "min": 9000, "moda": 20000, "max": 28500 }
  }
}
```

El programa carga automáticamente estos valores para garantizar que la
simulación respete los datos del ejemplo.

## Configuración opcional

El módulo expone la función `run_simulation` y la clase `SimulationConfig` para
personalizar el número de iteraciones, semilla aleatoria y nombres de los
archivos de salida.

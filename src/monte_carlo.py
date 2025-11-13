"""Simulación Monte Carlo utilizando arquitectura productor-consumidor.

Este módulo ejecuta una simulación Monte Carlo para estimar la utilidad de la
comercialización de una impresora portátil. Se utiliza una arquitectura
productor-consumidor donde el productor genera combinaciones de variables
aleatorias y el consumidor calcula la utilidad correspondiente.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import List, Tuple


SENTINEL = object()


@dataclass
class SimulationConfig:
    """Configuración de la simulación Monte Carlo."""

    iterations: int = 10_000
    seed: int | None = None
    output_dir: Path = Path("output")
    histogram_filename: str = "histograma_utilidad.svg"
    report_filename: str = "reporte_simulacion.txt"
    parameters_file: Path | None = Path("data/parametros_ejemplo.json")

    def ensure_output_dir(self) -> Path:
        """Garantiza la existencia del directorio de salida."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


@dataclass(frozen=True)
class TriangularDistribution:
    """Representa una distribución triangular usando los parámetros del ejemplo."""

    minimum: float
    maximum: float
    mode: float

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.minimum, self.maximum, self.mode)


@dataclass(frozen=True)
class ProblemParameters:
    """Agrupa los parámetros determinísticos y estocásticos del problema."""

    price_per_unit: float
    admin_cost: float
    marketing_cost: float
    labor_cost: TriangularDistribution
    component_cost: TriangularDistribution
    demand: TriangularDistribution

    @property
    def fixed_costs(self) -> float:
        return self.admin_cost + self.marketing_cost


@dataclass
class SimulationResults:
    """Resultados acumulados de la simulación."""

    utilities: List[float] = field(default_factory=list)

    def register(self, value: float) -> None:
        self.utilities.append(value)

    @property
    def minimum(self) -> float:
        return min(self.utilities)

    @property
    def maximum(self) -> float:
        return max(self.utilities)

    @property
    def mean(self) -> float:
        return sum(self.utilities) / len(self.utilities)


def load_parameters(path: Path | None) -> ProblemParameters:
    """Carga los parámetros del problema a partir de un archivo JSON."""

    if path is None:
        raise ValueError("Se requiere un archivo de parámetros para ejecutar la simulación.")

    data = json.loads(Path(path).read_text(encoding="utf-8"))

    distributions = data["distribuciones"]

    def build_distribution(key: str) -> TriangularDistribution:
        dist = distributions[key]
        return TriangularDistribution(
            minimum=float(dist["min"]),
            maximum=float(dist["max"]),
            mode=float(dist["moda"]),
        )

    return ProblemParameters(
        price_per_unit=float(data["precio_venta"]),
        admin_cost=float(data["costos_fijos"]["administracion"]),
        marketing_cost=float(data["costos_fijos"]["marketing"]),
        labor_cost=build_distribution("mano_obra"),
        component_cost=build_distribution("componentes"),
        demand=build_distribution("demanda"),
    )


def producer(queue: Queue, iterations: int, rng: random.Random, parameters: ProblemParameters) -> None:
    """Genera combinaciones aleatorias y las coloca en la cola."""

    for _ in range(iterations):
        labor_cost = rng.triangular(*parameters.labor_cost.to_tuple())
        component_cost = rng.triangular(*parameters.component_cost.to_tuple())
        demand = rng.triangular(*parameters.demand.to_tuple())
        queue.put((labor_cost, component_cost, demand))

    queue.put(SENTINEL)


def consumer(queue: Queue, results: SimulationResults, parameters: ProblemParameters) -> None:
    """Consume combinaciones de la cola y registra la utilidad."""

    while True:
        data = queue.get()
        try:
            if data is SENTINEL:
                break

            labor_cost, component_cost, demand = data
            utility = calculate_utility(labor_cost, component_cost, demand, parameters)
            results.register(utility)
        finally:
            queue.task_done()


def calculate_utility(
    labor_cost: float, component_cost: float, demand: float, parameters: ProblemParameters
) -> float:
    """Calcula la utilidad para una combinación específica de variables."""

    net_unit_margin = parameters.price_per_unit - labor_cost - component_cost
    return net_unit_margin * demand - parameters.fixed_costs


def generate_histogram(results: SimulationResults, output_path: Path) -> None:
    """Genera un histograma en formato SVG con las utilidades simuladas."""

    utilities = results.utilities
    min_value = min(utilities)
    max_value = max(utilities)

    bin_count = 30
    if max_value == min_value:
        bins = [len(utilities)] + [0] * (bin_count - 1)
        bin_edges = [min_value + i for i in range(bin_count + 1)]
    else:
        bin_width = (max_value - min_value) / bin_count
        bin_edges = [min_value + i * bin_width for i in range(bin_count + 1)]
        bins = [0] * bin_count
        for value in utilities:
            index = min(int((value - min_value) / bin_width), bin_count - 1)
            bins[index] += 1

    max_frequency = max(bins)
    width, height, margin = 800, 400, 40
    chart_width = width - 2 * margin
    chart_height = height - 2 * margin

    def x_position(index: int) -> float:
        return margin + index * (chart_width / bin_count)

    def bar_height(count: int) -> float:
        if max_frequency == 0:
            return 0
        return (count / max_frequency) * chart_height

    svg_lines = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "  <style>text { font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 12px; }</style>",
        "  <rect width='100%' height='100%' fill='white'/>",
    ]

    # Ejes
    svg_lines.append(
        f"  <line x1='{margin}' y1='{height - margin}' x2='{width - margin}' y2='{height - margin}' stroke='black'/>"
    )
    svg_lines.append(
        f"  <line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height - margin}' stroke='black'/>"
    )

    # Barras
    bar_width = chart_width / bin_count * 0.9
    for index, count in enumerate(bins):
        bar_h = bar_height(count)
        x = x_position(index) + (chart_width / bin_count - bar_width) / 2
        y = height - margin - bar_h
        svg_lines.append(
            f"  <rect x='{x:.2f}' y='{y:.2f}' width='{bar_width:.2f}' height='{bar_h:.2f}' fill='#1f77b4' stroke='black' stroke-width='0.5'/>"
        )

    # Etiquetas de frecuencia (eje Y)
    for i in range(6):
        value = i / 5 * max_frequency
        y = height - margin - (value / max_frequency if max_frequency else 0) * chart_height
        svg_lines.append(
            f"  <line x1='{margin - 5}' y1='{y:.2f}' x2='{margin}' y2='{y:.2f}' stroke='black'/>"
        )
        svg_lines.append(
            f"  <text x='{margin - 10}' y='{y + 4:.2f}' text-anchor='end'>{value:.0f}</text>"
        )

    # Etiquetas del eje X (valores)
    for i in range(0, bin_count + 1, 5):
        value = bin_edges[i]
        x = margin + i * (chart_width / bin_count)
        svg_lines.append(
            f"  <line x1='{x:.2f}' y1='{height - margin}' x2='{x:.2f}' y2='{height - margin + 5}' stroke='black'/>"
        )
        svg_lines.append(
            f"  <text x='{x:.2f}' y='{height - margin + 20}' text-anchor='middle'>{value:,.0f}</text>"
        )

    svg_lines.append(
        f"  <text x='{width / 2}' y='{margin - 10}' text-anchor='middle' font-size='16'>Distribución de utilidades - Simulación Monte Carlo</text>"
    )
    svg_lines.append(
        f"  <text x='{width / 2}' y='{height - 5}' text-anchor='middle'>Utilidad</text>"
    )
    svg_lines.append(
        f"  <text x='{15}' y='{height / 2}' transform='rotate(-90 {15} {height / 2})' text-anchor='middle'>Frecuencia</text>"
    )
    svg_lines.append("</svg>")

    output_path.write_text("\n".join(svg_lines) + "\n", encoding="utf-8")


def write_report(
    results: SimulationResults, output_path: Path, config: SimulationConfig, parameters: ProblemParameters
) -> None:
    """Genera un reporte en texto plano con los resultados clave."""

    lines = [
        "REPORTE DE SIMULACIÓN MONTE CARLO",
        "================================",
        f"Iteraciones: {config.iterations}",
        "",
        "Resultados:",
        f"  Utilidad mínima: {results.minimum:,.2f}",
        f"  Utilidad máxima: {results.maximum:,.2f}",
        f"  Utilidad media esperada: {results.mean:,.2f}",
        "",
        "Supuestos:",
        f"  Precio de venta por unidad: {parameters.price_per_unit:,.2f}",
        f"  Coste administrativo: {parameters.admin_cost:,.2f}",
        f"  Presupuesto de publicidad: {parameters.marketing_cost:,.2f}",
        f"  Coste de mano de obra (triangular): {parameters.labor_cost.to_tuple()}",
        f"  Coste de componentes (triangular): {parameters.component_cost.to_tuple()}",
        f"  Demanda anual (triangular): {parameters.demand.to_tuple()}",
        "",
        "Fuente de parámetros:",
        f"  Archivo: {config.parameters_file}",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_simulation(config: SimulationConfig | None = None) -> SimulationResults:
    """Ejecuta toda la simulación y devuelve los resultados."""

    config = config or SimulationConfig()
    results = SimulationResults()
    parameters = load_parameters(config.parameters_file)
    config.ensure_output_dir()

    rng = random.Random(config.seed)
    queue: Queue = Queue(maxsize=1_000)

    producer_thread = Thread(
        target=producer,
        args=(queue, config.iterations, rng, parameters),
        name="Producer",
    )
    consumer_thread = Thread(
        target=consumer,
        args=(queue, results, parameters),
        name="Consumer",
    )

    producer_thread.start()
    consumer_thread.start()

    producer_thread.join()
    queue.join()
    consumer_thread.join()

    histogram_path = config.output_dir / config.histogram_filename
    report_path = config.output_dir / config.report_filename

    generate_histogram(results, histogram_path)
    write_report(results, report_path, config, parameters)

    return results


if __name__ == "__main__":
    run_simulation()

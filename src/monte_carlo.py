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
from typing import List, Protocol, Tuple

SENTINEL = object()


@dataclass
class SimulationConfig:
    """Configuración de la simulación Monte Carlo."""

    iterations: int = 10_000
    seed: int | None = None
    output_dir: Path = Path("output")
    chart_filename: str = "convergencia_utilidad.svg"
    report_filename: str = "reporte_simulacion.txt"
    parameters_file: Path | None = Path("data/parametros_ejemplo.json")

    def ensure_output_dir(self) -> Path:
        """Garantiza la existencia del directorio de salida."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


class RandomVariable(Protocol):
    """Contrato común de las distribuciones aleatorias empleadas."""

    def sample(self, rng: random.Random) -> float:
        """Devuelve una muestra pseudoaleatoria."""

    def describe(self) -> str:
        """Describe la distribución de manera legible."""


@dataclass(frozen=True)
class TriangularDistribution:
    """Representa una distribución triangular."""

    minimum: float
    maximum: float
    mode: float

    def sample(self, rng: random.Random) -> float:
        return rng.triangular(self.minimum, self.maximum, self.mode)

    def describe(self) -> str:
        return (
            "Triangular(min={min:,.2f}, moda={mode:,.2f}, max={max:,.2f})".format(
                min=self.minimum, mode=self.mode, max=self.maximum
            )
        )


@dataclass(frozen=True)
class DiscreteDistribution:
    """Distribución discreta con probabilidades asociadas."""

    values: Tuple[float, ...]
    probabilities: Tuple[float, ...]

    def sample(self, rng: random.Random) -> float:
        return rng.choices(self.values, weights=self.probabilities, k=1)[0]

    def describe(self) -> str:
        formatted = ", ".join(
            f"({value:,.2f}, p={prob:.2f})" for value, prob in zip(self.values, self.probabilities)
        )
        return f"Discreta[{formatted}]"


@dataclass(frozen=True)
class UniformDistribution:
    """Distribución uniforme continua."""

    minimum: float
    maximum: float

    def sample(self, rng: random.Random) -> float:
        return rng.uniform(self.minimum, self.maximum)

    def describe(self) -> str:
        return f"Uniforme(min={self.minimum:,.2f}, max={self.maximum:,.2f})"


@dataclass(frozen=True)
class TruncatedNormalDistribution:
    """Distribución normal que respeta límites opcionales."""

    mean: float
    std_dev: float
    minimum: float | None = None
    maximum: float | None = None

    def sample(self, rng: random.Random) -> float:
        while True:
            value = rng.gauss(self.mean, self.std_dev)
            if self.minimum is not None and value < self.minimum:
                continue
            if self.maximum is not None and value > self.maximum:
                continue
            return value

    def describe(self) -> str:
        bounds = []
        if self.minimum is not None:
            bounds.append(f"min={self.minimum:,.2f}")
        if self.maximum is not None:
            bounds.append(f"max={self.maximum:,.2f}")
        extra = f", {' '.join(bounds)}" if bounds else ""
        return f"Normal(media={self.mean:,.2f}, desv={self.std_dev:,.2f}{extra})"


@dataclass(frozen=True)
class ProblemParameters:
    """Agrupa los parámetros determinísticos y estocásticos del problema."""

    price_per_unit: float
    admin_cost: float
    marketing_cost: float
    labor_cost: RandomVariable
    component_cost: RandomVariable
    demand: RandomVariable

    @property
    def fixed_costs(self) -> float:
        return self.admin_cost + self.marketing_cost


@dataclass
class SimulationResults:
    """Resultados acumulados de la simulación."""

    utilities: List[float] = field(default_factory=list)
    _cumulative_sum: float = 0.0
    running_means: List[float] = field(default_factory=list)

    def register(self, value: float) -> None:
        self.utilities.append(value)
        self._cumulative_sum += value
        self.running_means.append(self._cumulative_sum / len(self.utilities))

    @property
    def minimum(self) -> float:
        return min(self.utilities)

    @property
    def maximum(self) -> float:
        return max(self.utilities)

    @property
    def mean(self) -> float:
        return self._cumulative_sum / len(self.utilities)


def load_parameters(path: Path | None) -> ProblemParameters:
    """Carga los parámetros del problema a partir de un archivo JSON."""

    if path is None:
        raise ValueError("Se requiere un archivo de parámetros para ejecutar la simulación.")

    data = json.loads(Path(path).read_text(encoding="utf-8"))

    distributions = data["distribuciones"]

    def build_distribution(key: str) -> RandomVariable:
        dist = distributions[key]
        kind = dist.get("tipo", "triangular").lower()

        if kind == "triangular":
            return TriangularDistribution(
                minimum=float(dist["min"]),
                maximum=float(dist["max"]),
                mode=float(dist["moda"]),
            )

        if kind == "discreta":
            values = tuple(float(v) for v in dist["valores"])
            probabilities = tuple(float(p) for p in dist["probabilidades"])
            if len(values) != len(probabilities):
                raise ValueError(
                    f"La distribución discreta '{key}' requiere la misma cantidad de valores y probabilidades."
                )
            return DiscreteDistribution(values=values, probabilities=probabilities)

        if kind == "uniforme":
            return UniformDistribution(
                minimum=float(dist["min"]),
                maximum=float(dist["max"]),
            )

        if kind == "normal":
            minimum = dist.get("min")
            maximum = dist.get("max")
            return TruncatedNormalDistribution(
                mean=float(dist["media"]),
                std_dev=float(dist["desviacion"]),
                minimum=float(minimum) if minimum is not None else None,
                maximum=float(maximum) if maximum is not None else None,
            )

        raise ValueError(f"Tipo de distribución no soportado para '{key}': {kind}")

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
        labor_cost = parameters.labor_cost.sample(rng)
        component_cost = parameters.component_cost.sample(rng)
        demand = parameters.demand.sample(rng)
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


def generate_convergence_plot(results: SimulationResults, output_path: Path) -> None:
    """Genera una gráfica SVG de la convergencia de la utilidad media."""

    mean_values = results.running_means
    final_mean = results.mean
    iterations = len(mean_values)

    width, height = 960, 540
    margin_left, margin_right = 80, 40
    margin_top, margin_bottom = 70, 70
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    min_value = min(mean_values + [final_mean])
    max_value = max(mean_values + [final_mean])
    if min_value == max_value:
        min_value -= 1
        max_value += 1

    padding = 0.05 * (max_value - min_value)
    min_value -= padding
    max_value += padding

    def scale_x(index: int) -> float:
        if iterations <= 1:
            return margin_left
        return margin_left + (index / (iterations - 1)) * chart_width

    def scale_y(value: float) -> float:
        return height - margin_bottom - ((value - min_value) / (max_value - min_value)) * chart_height

    mean_points = " ".join(
        f"{scale_x(i):.2f},{scale_y(value):.2f}" for i, value in enumerate(mean_values)
    )

    final_mean_y = scale_y(final_mean)

    horizontal_grid_lines = []
    for i in range(6):
        y = margin_top + i * (chart_height / 5)
        value = max_value - i * ((max_value - min_value) / 5)
        horizontal_grid_lines.append(
            (
                f"  <line x1='{margin_left}' y1='{y:.2f}' x2='{width - margin_right}' y2='{y:.2f}' stroke='#d3d3d3' "
                "stroke-dasharray='4 4'/>",
                f"  <text x='{margin_left - 10}' y='{y + 4:.2f}' text-anchor='end'>{value:,.0f}</text>",
            )
        )

    vertical_ticks = []
    step = max(1, iterations // 10)
    for i in range(0, iterations, step):
        x = scale_x(i)
        label = i + 1
        vertical_ticks.append(
            (
                f"  <line x1='{x:.2f}' y1='{height - margin_bottom}' x2='{x:.2f}' y2='{height - margin_bottom + 8}' stroke='black'/>",
                f"  <text x='{x:.2f}' y='{height - margin_bottom + 28}' text-anchor='middle'>{label}</text>",
            )
        )
    if iterations > 1 and (iterations - 1) % step != 0:
        x = scale_x(iterations - 1)
        vertical_ticks.append(
            (
                f"  <line x1='{x:.2f}' y1='{height - margin_bottom}' x2='{x:.2f}' y2='{height - margin_bottom + 8}' stroke='black'/>",
                f"  <text x='{x:.2f}' y='{height - margin_bottom + 28}' text-anchor='middle'>{iterations}</text>",
            )
        )

    svg_lines = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "  <style>text { font-family: 'DejaVu Sans', Arial, sans-serif; }</style>",
        "  <rect width='100%' height='100%' fill='white'/>",
        f"  <text x='{width / 2}' y='{margin_top / 2}' text-anchor='middle' font-size='24' font-weight='bold'>SIMULACIÓN MONTECARLO</text>",
        "  <g>",
        f"    <text x='{width / 2}' y='{margin_top + 10}' text-anchor='middle' font-size='16'>Convergencia de la Utilidad Media en Simulaciones Monte Carlo</text>",
        "  </g>",
    ]

    for line, label in horizontal_grid_lines:
        svg_lines.append(line)
        svg_lines.append(label)

    svg_lines.append(
        f"  <line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' y2='{height - margin_bottom}' stroke='black' stroke-width='1.5'/>"
    )
    svg_lines.append(
        f"  <line x1='{margin_left}' y1='{height - margin_bottom}' x2='{width - margin_right}' y2='{height - margin_bottom}' stroke='black' stroke-width='1.5'/>"
    )

    svg_lines.append(
        f"  <polyline points='{mean_points}' fill='none' stroke='#1f77b4' stroke-width='2'/>"
    )

    svg_lines.append(
        f"  <line x1='{margin_left}' y1='{final_mean_y:.2f}' x2='{width - margin_right}' y2='{final_mean_y:.2f}' stroke='#d62728' stroke-width='2' stroke-dasharray='8 6'/>"
    )

    legend_x = margin_left + 40
    legend_y = margin_top + 20
    svg_lines.extend(
        [
            f"  <rect x='{legend_x - 20}' y='{legend_y - 18}' width='360' height='60' fill='white' stroke='#cccccc'/>",
            f"  <line x1='{legend_x}' y1='{legend_y}' x2='{legend_x + 40}' y2='{legend_y}' stroke='#1f77b4' stroke-width='2'/>",
            f"  <text x='{legend_x + 50}' y='{legend_y + 4}' font-size='14'>Convergencia de la Media</text>",
            f"  <line x1='{legend_x}' y1='{legend_y + 28}' x2='{legend_x + 40}' y2='{legend_y + 28}' stroke='#d62728' stroke-width='2' stroke-dasharray='8 6'/>",
            f"  <text x='{legend_x + 50}' y='{legend_y + 32}' font-size='14'>Media final: {final_mean:,.2f}</text>",
        ]
    )

    svg_lines.append(
        f"  <text x='{margin_left - 50}' y='{(margin_top + height - margin_bottom) / 2}' text-anchor='middle' transform='rotate(-90 {margin_left - 50} {(margin_top + height - margin_bottom) / 2})' font-size='14'>Utilidad Media</text>"
    )
    svg_lines.append(
        f"  <text x='{(margin_left + width - margin_right) / 2}' y='{height - margin_bottom + 50}' text-anchor='middle' font-size='14'>Número de Simulaciones</text>"
    )

    for tick_line, tick_label in vertical_ticks:
        svg_lines.append(tick_line)
        svg_lines.append(tick_label)

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
        f"  Coste de mano de obra: {parameters.labor_cost.describe()}",
        f"  Coste de componentes: {parameters.component_cost.describe()}",
        f"  Demanda anual: {parameters.demand.describe()}",
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

    chart_path = config.output_dir / config.chart_filename
    report_path = config.output_dir / config.report_filename

    generate_convergence_plot(results, chart_path)
    write_report(results, report_path, config, parameters)

    return results


if __name__ == "__main__":
    run_simulation()

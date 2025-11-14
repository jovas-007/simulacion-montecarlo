"""Simulación Monte Carlo utilizando una arquitectura productor-consumidor.

Este módulo ejecuta la simulación del ejemplo propuesto en las diapositivas
suministradas por el usuario. El productor genera combinaciones aleatorias de
costes de mano de obra, componentes y demanda. El consumidor calcula la utilidad
para cada combinación y acumula las estadísticas relevantes.
"""

from __future__ import annotations

import argparse
import math
import queue
import random
import threading
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Parameters:
    """Conjunto de parámetros estáticos del problema."""

    selling_price: float = 70_000  # PV
    admin_costs: float = 16_000_000  # CA
    marketing_costs: float = 8_000_000  # CB


@dataclass(frozen=True)
class Sample:
    """Representa una combinación de entrada generada por el productor."""

    labor_cost: float
    component_cost: float
    demand: int


class Producer(threading.Thread):
    """Genera muestras basadas en las distribuciones descritas."""

    def __init__(
        self,
        iterations: int,
        output_queue: queue.Queue[Optional[Sample]],
        *,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(name="Producer")
        self.iterations = iterations
        self.output_queue = output_queue
        self.random = random.Random(seed)

        self._labor_distribution: list[tuple[float, float]] = [
            (10_000, 0.10),
            (13_000, 0.30),
            (16_000, 0.30),
            (19_000, 0.20),
            (22_000, 0.10),
        ]

    def run(self) -> None:
        for _ in range(self.iterations):
            labor_cost = self._sample_labor_cost()
            component_cost = self.random.uniform(25_000, 35_000)
            demand = self._sample_demand()
            self.output_queue.put(Sample(labor_cost, component_cost, demand))

        # Señal de finalización
        self.output_queue.put(None)

    def _sample_labor_cost(self) -> float:
        threshold = self.random.random()
        cumulative = 0.0
        for value, probability in self._labor_distribution:
            cumulative += probability
            if threshold <= cumulative:
                return value
        # Debería retornar dentro del bucle, pero en caso de errores numéricos,
        # devolvemos el último valor.
        return self._labor_distribution[-1][0]

    def _sample_demand(self) -> int:
        # La demanda sigue una distribución normal. Aseguramos no obtener valores
        # negativos tomando el máximo con cero y redondeamos al entero más
        # cercano porque la demanda se mide en unidades.
        demand = self.random.gauss(14_500, 4_000)
        demand = max(0.0, demand)
        return int(round(demand))


class Consumer(threading.Thread):
    """Consume las muestras y calcula las estadísticas de utilidad."""

    def __init__(
        self,
        input_queue: queue.Queue[Optional[Sample]],
        parameters: Parameters,
    ) -> None:
        super().__init__(name="Consumer")
        self.input_queue = input_queue
        self.parameters = parameters

        self.min_profit: Optional[float] = None
        self.max_profit: Optional[float] = None
        self.total_profit: float = 0.0
        self.samples_processed: int = 0

    def run(self) -> None:
        while True:
            sample = self.input_queue.get()
            if sample is None:
                # Reenviamos la señal de finalización en caso de que existan más
                # consumidores.
                self.input_queue.put(None)
                self.input_queue.task_done()
                break

            profit = self._compute_profit(sample)
            self._update_statistics(profit)
            self.input_queue.task_done()

    def _compute_profit(self, sample: Sample) -> float:
        p = self.parameters
        unit_margin = p.selling_price - sample.labor_cost - sample.component_cost
        total = unit_margin * sample.demand - (p.admin_costs + p.marketing_costs)
        return total

    def _update_statistics(self, profit: float) -> None:
        self.samples_processed += 1
        self.total_profit += profit
        if self.min_profit is None or profit < self.min_profit:
            self.min_profit = profit
        if self.max_profit is None or profit > self.max_profit:
            self.max_profit = profit

    @property
    def average_profit(self) -> float:
        if self.samples_processed == 0:
            return math.nan
        return self.total_profit / self.samples_processed


def run_simulation(iterations: int, seed: Optional[int]) -> Consumer:
    samples_queue: queue.Queue[Optional[Sample]] = queue.Queue()
    parameters = Parameters()

    producer = Producer(iterations, samples_queue, seed=seed)
    consumer = Consumer(samples_queue, parameters)

    producer.start()
    consumer.start()

    producer.join()
    consumer.join()

    return consumer


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simula el potencial de utilidad de la impresora siguiendo el esquema "
            "productor/consumidor."
        )
    )
    parser.add_argument(
        "iterations",
        type=int,
        nargs="?",
        default=10_000,
        help="Número de escenarios a simular (por defecto: 10000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla para el generador de números aleatorios",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    consumer = run_simulation(args.iterations, args.seed)

    print(f"Simulaciones ejecutadas: {consumer.samples_processed}")
    print(f"Utilidad mínima: {consumer.min_profit:,.2f}")
    print(f"Utilidad máxima: {consumer.max_profit:,.2f}")
    print(f"Utilidad media esperada: {consumer.average_profit:,.2f}")


if __name__ == "__main__":
    main()

"""Monte Carlo simulation using a producer-consumer architecture.

This script implements a simple business case in which the utility (profit)
of selling a product is subject to uncertain demand, price, and costs.  The
producer thread generates random combinations of those variables and the
consumer thread processes them to obtain the minimum, maximum, and expected
utility.  A convergence plot of the running mean utility is displayed at the
end of the execution.
"""

from __future__ import annotations

import math
import queue
import random
import threading
from dataclasses import dataclass
from typing import Iterable, List

import matplotlib.pyplot as plt


@dataclass(frozen=True)
class Scenario:
    """Collection of the uncertain variables for a single simulation."""

    demand: float
    selling_price: float
    variable_cost: float
    fixed_cost: float


class ScenarioProducer(threading.Thread):
    """Producer that places randomly generated scenarios into a queue."""

    def __init__(self, scenarios: int, out_queue: "queue.Queue[Scenario | None]", seed: int = 4) -> None:
        super().__init__(daemon=True)
        self._scenarios = scenarios
        self._out_queue = out_queue
        self._rng = random.Random(seed)

    def _generate_demand(self) -> float:
        # Demand is assumed to be normally distributed with a mean of 5 000
        # units and a standard deviation of 600. The distribution is truncated
        # at zero to prevent negative demand.
        demand = self._rng.normalvariate(5_000.0, 600.0)
        return max(0.0, demand)

    def _generate_price(self) -> float:
        # Selling price is modelled with a triangular distribution. The most
        # likely price is 28 monetary units, but it can range from 24 to 33.
        return self._rng.triangular(24.0, 28.0, 33.0)

    def _generate_variable_cost(self) -> float:
        # Variable production cost is assumed to fluctuate uniformly between 16
        # and 22 monetary units.
        return self._rng.uniform(16.0, 22.0)

    def _generate_fixed_cost(self) -> float:
        # The fixed cost varies slightly around 50 000 monetary units. The
        # distribution is narrow to mimic overhead variations.
        fixed_cost = self._rng.normalvariate(50_000.0, 2_500.0)
        return max(0.0, fixed_cost)

    def run(self) -> None:  # pragma: no cover - thread loop
        for _ in range(self._scenarios):
            scenario = Scenario(
                demand=self._generate_demand(),
                selling_price=self._generate_price(),
                variable_cost=self._generate_variable_cost(),
                fixed_cost=self._generate_fixed_cost(),
            )
            self._out_queue.put(scenario)

        # Signal that no more scenarios will be produced.
        self._out_queue.put(None)


class ScenarioConsumer(threading.Thread):
    """Consumer that reads scenarios and calculates utilities."""

    def __init__(self, in_queue: "queue.Queue[Scenario | None]") -> None:
        super().__init__(daemon=True)
        self._in_queue = in_queue
        self.utilities: List[float] = []

    @staticmethod
    def _utility(scenario: Scenario) -> float:
        # Utility is the total contribution margin minus the fixed cost. The
        # contribution margin takes demand and the margin per unit into account.
        margin_per_unit = scenario.selling_price - scenario.variable_cost
        contribution_margin = scenario.demand * margin_per_unit
        return contribution_margin - scenario.fixed_cost

    def run(self) -> None:  # pragma: no cover - thread loop
        while True:
            scenario = self._in_queue.get()
            if scenario is None:
                break

            utility = self._utility(scenario)
            self.utilities.append(utility)


def running_mean(values: Iterable[float]) -> List[float]:
    """Return the running mean for the provided iterable of numbers."""

    total = 0.0
    means: List[float] = []
    for index, value in enumerate(values, start=1):
        total += value
        means.append(total / index)
    return means


def main(simulations: int = 10_000) -> None:
    scenario_queue: "queue.Queue[Scenario | None]" = queue.Queue(maxsize=simulations // 10 or 1)

    producer = ScenarioProducer(simulations, scenario_queue)
    consumer = ScenarioConsumer(scenario_queue)

    producer.start()
    consumer.start()

    producer.join()
    consumer.join()

    if not consumer.utilities:
        print("No utilities were produced. Reduce the number of simulations and try again.")
        return

    utilities = consumer.utilities
    mean_utilities = running_mean(utilities)

    minimum = min(utilities)
    maximum = max(utilities)
    expected = mean_utilities[-1]

    print(f"Simulaciones completadas: {len(utilities):,}")
    print(f"Utilidad mínima: {minimum:,.2f}")
    print(f"Utilidad máxima: {maximum:,.2f}")
    print(f"Utilidad media esperada: {expected:,.2f}")

    figure, axis = plt.subplots(figsize=(10, 6))
    axis.plot(range(1, len(mean_utilities) + 1), mean_utilities, label="Convergencia de la Media", color="royalblue")
    axis.axhline(expected, color="crimson", linestyle="--", linewidth=1.2, label=f"Media final: {expected:,.2f}")
    axis.set_title("Convergencia de la Utilidad Media en Simulaciones Monte Carlo")
    axis.set_xlabel("Número de Simulaciones")
    axis.set_ylabel("Utilidad Media")
    axis.legend()
    axis.grid(True, linestyle="--", alpha=0.3)
    figure.tight_layout()
    output_path = "montecarlo_convergencia.png"
    figure.savefig(output_path, dpi=120)
    plt.close(figure)
    print(f"Gráfica guardada en: {output_path}")


if __name__ == "__main__":
    main()

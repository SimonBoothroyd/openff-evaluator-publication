"""A script to plot the timing information output by the ``extract_timings`` script."""

import json
import os

import click
import pandas
import seaborn
from matplotlib import pyplot

seaborn.set(color_codes=True)
seaborn.set_style("white")

FORMAT = "pdf"


def plot_approach_timings(iteration_statistics, average, output_path):

    # Reshape the statistics into a pandas data frame.
    data_rows = []

    for iteration, statistics in enumerate(iteration_statistics):

        simulation_time = statistics["time_per_approach"]["SimulationLayer"]
        reweighting_time = statistics["time_per_approach"]["ReweightingLayer"]

        overhead_time = statistics["total_time"] - simulation_time - reweighting_time

        if average:

            simulation_count = statistics["approach_counts"]["SimulationLayer"]
            reweighting_count = statistics["approach_counts"]["ReweightingLayer"]

            simulation_time = simulation_time / max(simulation_count, 1)
            reweighting_time = reweighting_time / max(reweighting_count, 1)

            overhead_time = overhead_time / max(simulation_count, 1)

        data_row = {
            "Iteration": iteration,
            "Simulation": simulation_time / 60.0,
        }

        if reweighting_time > 0.0:
            data_row["Reweighting"] = reweighting_time / 60.0
            data_row["Overhead"] = overhead_time / 60.0

        data_rows.append(data_row)

    data_frame = pandas.DataFrame(data_rows)
    data_frame.set_index("Iteration").plot(
        kind="bar", stacked=True, width=1, figsize=(4.3, 4)
    )

    pyplot.legend(loc="best")
    pyplot.ylabel(("" if not average else "Average ") + "Time (m)")
    pyplot.tight_layout()
    pyplot.savefig(output_path)


def plot_approach_counts(iteration_statistics, output_path):

    # Reshape the statistics into a pandas data frame.
    data_rows = []

    for iteration, statistics in enumerate(iteration_statistics):

        simulation_counts = statistics["approach_counts_per_property"][
            "SimulationLayer"
        ]
        reweighting_counts = statistics["approach_counts_per_property"][
            "ReweightingLayer"
        ]

        for property_type in ["Density", "EnthalpyOfVaporization"]:

            if (
                property_type in reweighting_counts
                and reweighting_counts[property_type] > 0
            ):
                percentage_reweighted = (
                    reweighting_counts[property_type]
                    / (
                        simulation_counts[property_type]
                        + reweighting_counts[property_type]
                    )
                    * 100.0
                )
            else:
                percentage_reweighted = 0.0

            data_rows.append(
                {
                    "Iteration": iteration,
                    "Property Type": property_type,
                    "% Reweighted": percentage_reweighted,
                }
            )

    data_frame = pandas.DataFrame(data_rows)

    seaborn.catplot(
        x="Iteration",
        y="% Reweighted",
        hue="Property Type",
        kind="bar",
        data=data_frame,
        legend_out=False,
        height=4.0,
        aspect=1.0,
    )

    handles, labels = pyplot.gca().get_legend_handles_labels()
    pyplot.gca().legend(handles=handles[:], labels=labels[:])

    pyplot.ylim(0.0, 100.0)
    pyplot.savefig(output_path)


def plot_cumulative_time(optimization_statistics, output_path):

    data_rows = []

    total_simulated_time = 0.0
    total_reweighted_time = 0.0

    for iteration, (simulation_statistics, reweighting_statistics) in enumerate(
        zip(
            optimization_statistics["simulation-only"],
            optimization_statistics["simulation-reweighting"],
        )
    ):

        total_simulated_time += simulation_statistics["total_time"]
        total_reweighted_time += reweighting_statistics["total_time"]

        data_row = {
            "Iteration": str(iteration),
            "Simulation Only": total_simulated_time / 60.0,
            "Simulation + Reweighting": total_reweighted_time / 60.0,
        }

        data_rows.append(data_row)

    data_frame = pandas.DataFrame(data_rows)
    data_frame.set_index("Iteration").plot(figsize=(4.3, 4))

    pyplot.ylabel("Cumulative Time (m)")
    pyplot.tight_layout()
    pyplot.savefig(output_path)


@click.argument(
    "files",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "-o",
    "output_path",
    type=click.Path(exists=False, file_okay=False),
    help="The directory to save the outputs in.",
)
@click.command()
def main(files, output_path):

    optimization_statistics = {}

    for input_path in files:

        optimization = os.path.splitext(os.path.split(input_path)[-1])[0]

        with open(input_path) as file:

            iteration_statistics = json.load(file)
            optimization_statistics[optimization] = iteration_statistics

        os.makedirs(os.path.join(output_path, optimization), exist_ok=True)

        plot_approach_timings(
            iteration_statistics,
            False,
            os.path.join(output_path, optimization, f"approach_timings.{FORMAT}"),
        )
        plot_approach_timings(
            iteration_statistics,
            True,
            os.path.join(output_path, optimization, f"avg_approach_timings.{FORMAT}"),
        )

        plot_approach_counts(
            iteration_statistics,
            os.path.join(output_path, optimization, f"approach_counts.{FORMAT}"),
        )

    plot_cumulative_time(
        optimization_statistics, os.path.join(output_path, f"cumulative_time.{FORMAT}")
    )


if __name__ == "__main__":
    main()

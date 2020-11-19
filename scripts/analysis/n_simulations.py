"""A script which attempts to estimate how many simulations would be required to
estimate a particular data set of physical properties.
"""

import click
import pandas
from nonbonded.library.models.datasets import DataSet
from openff.evaluator.client import EvaluatorClient
from openff.evaluator.forcefield import SmirnoffForceFieldSource
from openff.evaluator.layers.simulation import SimulationLayer
from openff.evaluator.protocols.openmm import OpenMMSimulation
from openff.evaluator.workflow import ProtocolGroup


def find_simulation_protocols(protocols_to_search, found_protocols):

    for protocol in protocols_to_search:

        if isinstance(protocol, ProtocolGroup):
            find_simulation_protocols(protocol.protocols.values(), found_protocols)
            continue

        if not isinstance(protocol, OpenMMSimulation):
            continue

        if "production" not in protocol.id:
            continue

        found_protocols.append(protocol)


@click.argument(
    "data_set_paths",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False),
)
@click.command()
def main(data_set_paths):

    data_frames = []

    for data_set_path in data_set_paths:

        data_frame = DataSet.parse_file(data_set_path).to_pandas()
        data_frames.append(data_frame)

    data_frame = pandas.concat(data_frames, ignore_index=True, sort=False)
    data_set = DataSet.from_pandas(data_frame, "x", "y", [])

    for index, data_entry in enumerate(data_set.entries):
        data_entry.id = index

    evaluator_data_set = data_set.to_evaluator()
    force_field_source = SmirnoffForceFieldSource.from_path("openff-1.0.0.offxml")

    workflow_graph, _ = SimulationLayer._build_workflow_graph(
        "",
        storage_backend=None,
        properties=evaluator_data_set.properties,
        force_field_path="",
        parameter_gradient_keys=[],
        options=EvaluatorClient.default_request_options(
            evaluator_data_set, force_field_source
        ),
    )

    simulation_protocols = []

    find_simulation_protocols(workflow_graph.protocols.values(), simulation_protocols)

    print("Estimated simulations required: ", len({x.id for x in simulation_protocols}))


if __name__ == "__main__":
    main()

"""A script which will extracts and summarise how how long each calculation approach
took to estimate a training data set at each iteration of an optimization.
"""
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
from glob import glob

import click
from dateutil import parser
from nonbonded.library.utilities import temporary_cd
from openff.evaluator.client import RequestResult
from openff.evaluator.workflow import ProtocolSchema


def parse_batch_timing_information():

    output_file_paths = glob("*.o")
    assert len(output_file_paths) == 1

    output_file_path = output_file_paths[0]

    with open(output_file_path) as file:
        output_file_lines = file.read().split("\n")

    previous_line_time = None

    start_datetime = None
    current_iteration = -1

    batch_start_times = defaultdict(lambda: defaultdict(dict))
    batch_end_times = defaultdict(lambda: defaultdict(dict))

    for output_file_line in output_file_lines:

        # Determine which date the calculation begun on.
        started_at_match = re.match(r"Started at (.*)", output_file_line)

        if started_at_match is not None:
            start_datetime = parser.parse(started_at_match.group(1))

        # Extract any timing information for the line if available.
        line_time_match = re.match(r"(\d\d:\d\d:\d\d\.\d\d\d)\s", output_file_line)

        if not line_time_match:
            continue

        line_time = parser.parse(
            line_time_match.group(1),
            default=start_datetime if not previous_line_time else previous_line_time,
        )

        # Correct for dates not being logged.
        if previous_line_time and line_time - previous_line_time < timedelta(0):
            line_time += timedelta(days=1)

        previous_line_time = line_time

        # Determine if the log is now describing a new iteration.
        received_request_match = re.match(
            r"([\d:.]+)\sINFO\s+Received estimation request", output_file_line
        )

        if received_request_match:

            current_iteration += 1
            continue

        # Check for any information about batch start or end times
        start_time_match = re.match(
            r"([\d:.]+)\sINFO\s+Launching batch ([0-9a-z]+) using the ([a-zA-Z]+)\s",
            output_file_line,
        )
        end_time_match = re.match(
            r"([\d:.]+)\sINFO\s+Finished server request ([0-9a-z]+)$", output_file_line
        )

        # Check for batch start times
        if start_time_match:

            batch_id = start_time_match.group(2)
            layer_type = start_time_match.group(3)

            if any(
                batch_id in batch_start_times[current_iteration][x]
                for x in batch_start_times[current_iteration]
            ):

                # Record the end time of the previous layer.
                previous_layer_type = next(iter(batch_start_times[current_iteration]))
                batch_end_times[current_iteration][previous_layer_type][
                    batch_id
                ] = line_time

            batch_start_times[current_iteration][layer_type][batch_id] = line_time

        # Check for batch end times
        if end_time_match:

            batch_id = end_time_match.group(2)

            # Find the matching layer type
            layer_types = {
                layer_type
                for layer_type in batch_start_times[current_iteration]
                if (
                    batch_id in batch_start_times[current_iteration][layer_type]
                    and batch_id not in batch_end_times[current_iteration][layer_type]
                )
            }

            assert len(layer_types) > 0

            if len(layer_types) == 2:
                layer_type = "ReweightingLayer"
            else:
                layer_type = [*layer_types][0]

            batch_end_times[current_iteration][layer_type][batch_id] = line_time

    batch_timings = defaultdict(lambda: defaultdict(dict))

    # Validate and consolidate the timings.
    for current_iteration in batch_start_times:

        assert {*batch_start_times[current_iteration]} == {
            *batch_end_times[current_iteration]
        }

        for layer_type in batch_start_times[current_iteration]:

            assert {*batch_start_times[current_iteration][layer_type]} == {
                *batch_end_times[current_iteration][layer_type]
            }

            for batch_id in batch_start_times[current_iteration][layer_type]:

                batch_start_time = batch_start_times[current_iteration][layer_type][
                    batch_id
                ]
                batch_end_time = batch_end_times[current_iteration][layer_type][
                    batch_id
                ]

                assert batch_end_time > batch_start_time

                batch_timings[current_iteration][layer_type][batch_id] = (
                    batch_start_time + timedelta(seconds=-1),
                    batch_end_time + timedelta(seconds=1),
                )

    return batch_timings


def parse_protocol_timing_information():

    per_protocol_timings = defaultdict(list)

    for log_file in glob("worker-logs/*.log"):

        protocol_start_times = {}
        protocol_end_times = {}

        with open(log_file) as file:
            log_lines = file.read().split("\n")

        modified_time = datetime.fromtimestamp(os.path.getmtime(log_file))
        modified_time += timedelta(hours=2)

        initial_time = parser.parse(
            re.match(r"([\d\-]+\s\d\d:\d\d:\d\d\.\d\d\d)\s", log_lines[0]).group(1),
            default=modified_time,
        )

        if initial_time > modified_time and initial_time - modified_time > timedelta(
            seconds=2
        ):
            initial_time += timedelta(days=-1)

        worker_close_time = initial_time + timedelta(hours=5, minutes=59)

        protocol_started = None

        for log_line in log_lines:

            start_time_match = re.match(
                r"([\d\-]+\s[\d:.]+)\sINFO\s+Executing\s([0-9a-z|_]+)", log_line
            )
            end_time_match = re.match(
                r"^([\d\-]+\s[\d:.]+)\sINFO\s+([0-9a-z|_]+)\sfinished executing after "
                r"([\d.]+)\sms",
                log_line,
            )

            if not end_time_match:

                end_time_match = re.match(
                    r"^([\d\-]+\s[\d:.]+)\sINFO\s+Protocol failed to execute:\s([0-9a-z|_]+)$",
                    log_line,
                )

            if start_time_match:

                start_time = parser.parse(
                    start_time_match.group(1), default=initial_time
                )
                if start_time < initial_time:
                    start_time += timedelta(days=1)

                protocol_id = start_time_match.group(2)

                if protocol_started is not None:
                    continue

                protocol_started = protocol_id
                protocol_start_times[protocol_id] = start_time

            elif end_time_match:

                end_time = parser.parse(end_time_match.group(1), default=initial_time)
                if end_time < initial_time:
                    end_time += timedelta(days=1)

                protocol_id = end_time_match.group(2)

                if protocol_started is not None and protocol_id != protocol_started:
                    continue

                protocol_started = None
                protocol_end_times[protocol_id] = end_time

        for protocol_id in protocol_start_times:

            start_time = protocol_start_times[protocol_id]
            end_time = protocol_end_times.get(protocol_id, worker_close_time)

            per_protocol_timings[protocol_id].append((start_time, end_time))

    return per_protocol_timings


def extract_batch_id(fidelity, protocol_schemas):
    """Extracts the id of the batch which a physical property was computed as part of
    based on the protocols used to estimate it.
    """

    batch_id = None

    if fidelity == "ReweightingLayer":

        for protocol_schema in protocol_schemas:

            if "unpack_data" not in protocol_schema.id:
                continue

            simulation_data_path = protocol_schema.inputs[".simulation_data_path"][0]

            if isinstance(simulation_data_path, list):
                simulation_data_path = simulation_data_path[0]

            simulation_data_path_split = simulation_data_path.split("/")

            layer_id_index = simulation_data_path_split.index("ReweightingLayer")

            batch_id = simulation_data_path_split[layer_id_index + 1]

    else:

        batch_id = [
            protocol.inputs[".force_field_path"].split("/")[2]
            for protocol in protocol_schemas
            if "assign_parameters" in protocol.id
        ][0]

    assert batch_id is not None
    return batch_id


def parse_iteration_statistics(batch_timings, protocol_timings):

    n_iterations = len(batch_timings)

    all_statistics = []

    for iteration in range(n_iterations):

        folder_name = "iter_" + str(iteration).zfill(4)
        folder_path = os.path.join("optimize.tmp", "phys-prop", folder_name)

        results = RequestResult.from_json(os.path.join(folder_path, "results.json"))

        # Create an object to store the statistics for this iteration in.
        statistics = {
            "approach_counts": {"SimulationLayer": 0, "ReweightingLayer": 0},
            "approach_counts_per_property": {
                "SimulationLayer": defaultdict(int),
                "ReweightingLayer": defaultdict(int),
            },
            "time_per_approach": {"SimulationLayer": 0.0, "ReweightingLayer": 0.0},
        }

        # Extract timing and count information for each of the different
        # calculation layers. This loop does not include timing information
        # for protocols which were executed, but ultimately did not yield
        # a property estimate i.e reweighting protocols were executed,
        # but ultimately there was not enough effective samples to use the
        # reweighted value.
        batch_protocols = defaultdict(lambda: defaultdict(set))

        for physical_property in results.estimated_properties.properties:

            # Tally that this property was calculated at a specific fidelity.
            fidelity = physical_property.source.fidelity
            statistics["approach_counts"][fidelity] += 1
            statistics["approach_counts_per_property"][fidelity][
                physical_property.__class__.__name__
            ] += 1

            # Determine which batch this property was calculated as part of.
            provenance = json.loads(physical_property.source.provenance)

            protocol_schemas = [
                ProtocolSchema.parse_json(json.dumps(x))
                for x in provenance["protocol_schemas"]
            ]

            protocol_ids = [x.id for x in protocol_schemas]
            batch_id = extract_batch_id(fidelity, protocol_schemas)

            batch_protocols[fidelity][batch_id].update(protocol_ids)

        for fidelity in batch_protocols:
            for batch_id in batch_protocols[fidelity]:

                protocol_ids = batch_protocols[fidelity][batch_id]

                batch_start_time, batch_end_time = batch_timings[iteration][fidelity][
                    batch_id
                ]
                approach_time = 0.0

                for protocol_id in protocol_ids:

                    protocol_times = protocol_timings[protocol_id]
                    times_to_remove = []

                    for protocol_start_time, protocol_end_time in protocol_times:

                        if (
                            protocol_start_time < batch_start_time
                            or protocol_start_time > batch_end_time
                            or protocol_end_time < batch_start_time
                            or protocol_end_time > batch_end_time
                        ):
                            continue

                        approach_time += (
                            protocol_end_time - protocol_start_time
                        ).total_seconds()

                        times_to_remove.append((protocol_start_time, protocol_end_time))

                    for time_to_remove in times_to_remove:
                        protocol_times.remove(time_to_remove)

                statistics["time_per_approach"][fidelity] += approach_time

        all_statistics.append(statistics)

        # Tally up the total execution times of protocols which were executed,
        # but which did not ultimately lead to a property estimate.
        iteration_start_time = min(
            batch_timings[iteration][layer_type][batch_id][0]
            for layer_type in batch_timings[iteration]
            for batch_id in batch_timings[iteration][layer_type]
        )
        iteration_end_time = max(
            batch_timings[iteration][layer_type][batch_id][1]
            for layer_type in batch_timings[iteration]
            for batch_id in batch_timings[iteration][layer_type]
        )

        unused_protocol_time = 0.0

        for protocol_id in protocol_timings:

            if len(protocol_timings[protocol_id]) == 0:
                continue

            for protocol_start_time, protocol_end_time in protocol_timings[protocol_id]:

                if (
                    protocol_start_time < iteration_start_time
                    or protocol_start_time > iteration_end_time
                    or protocol_end_time < iteration_start_time
                    or protocol_end_time > iteration_end_time
                ):
                    continue

                elapsed_time = (protocol_end_time - protocol_start_time).total_seconds()
                unused_protocol_time += elapsed_time

        total_time = unused_protocol_time

        for fidelity in statistics["time_per_approach"]:
            total_time += statistics["time_per_approach"][fidelity]

        statistics["total_time"] = total_time

    return all_statistics


@click.argument(
    "input_directory",
    nargs=1,
    type=click.Path(exists=True, file_okay=False),
)
@click.option(
    "-o",
    "output_path",
    type=click.Path(exists=False, dir_okay=False),
    help="The path to save the output to.",
)
@click.command()
def main(input_directory: str, output_path: str):

    with temporary_cd(input_directory):

        batch_timings = parse_batch_timing_information()
        protocol_timings = parse_protocol_timing_information()

        iteration_statistics = parse_iteration_statistics(
            batch_timings, protocol_timings
        )

    with open(output_path, "w") as file:
        json.dump(iteration_statistics, file)


if __name__ == "__main__":
    main()

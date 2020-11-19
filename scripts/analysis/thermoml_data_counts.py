"""A script which attempt to provide estimates of the number of data points
for different physical properties in the ThermoML archive."""
import os

import click
import pandas
from openff.evaluator.datasets.curation.components import thermoml


@click.command()
def main():

    # Download and import all of the readable entries from ThermoML. A local
    # copy is cached to make re-running this script faster.
    if os.path.isfile("thermoml.csv"):
        thermoml_data_frame = pandas.read_csv("thermoml.csv")
    else:
        thermoml_data_frame = thermoml.ImportThermoMLData.apply(
            pandas.DataFrame(), thermoml.ImportThermoMLDataSchema(), 4
        )
        thermoml_data_frame.to_csv("thermoml.csv", index=False)

    # Count the number of each type of property which can currently be parsed by
    # evaluator.
    property_headers = [x for x in thermoml_data_frame if x.find(" Value ") >= 0]

    for property_header in property_headers:

        property_type = property_header.split(" ")[0]

        property_data = thermoml_data_frame[
            thermoml_data_frame[property_header].notna()
        ]

        counts = []

        for n_components in [1, 2, 3]:

            component_data = property_data[
                property_data["N Components"] == n_components
            ]
            counts.append(len(component_data))

        counts_string = " ".join(map(str, counts))
        print(f"{property_type} {counts_string}")


if __name__ == "__main__":
    main()

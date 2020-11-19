import os

import pandas
from nonbonded.library.models.authors import Author
from nonbonded.library.models.datasets import DataSet
from nonbonded.library.utilities.environments import ChemicalEnvironment
from openff.evaluator.datasets.curation.components import (
    conversion,
    filtering,
    selection,
    thermoml,
)
from openff.evaluator.datasets.curation.components.selection import State, TargetState
from openff.evaluator.datasets.curation.workflow import (
    CurationWorkflow,
    CurationWorkflowSchema,
)

AUTHORS = [
    Author(
        name="Simon Boothroyd",
        email="simon.boothroyd@colorado.edu",
        institute="University of Colorado Boulder",
    ),
]

N_PROCESSES = 4


def main():

    if os.path.isfile("thermoml.csv"):
        thermoml_data_frame = pandas.read_csv("thermoml.csv")
    else:
        thermoml_data_frame = thermoml.ImportThermoMLData.apply(
            pandas.DataFrame(), thermoml.ImportThermoMLDataSchema(), N_PROCESSES
        )
        thermoml_data_frame.to_csv("thermoml.csv", index=False)

    curation_schema = CurationWorkflowSchema(
        component_schemas=[
            # Filter out any measurements made for systems with more than
            # two components
            filtering.FilterByNComponentsSchema(n_components=[1, 2]),
            # Remove any duplicate data.
            filtering.FilterDuplicatesSchema(
                temperature_precision=1, pressure_precision=0
            ),
            # Filter out data points measured away from ambient conditions.
            filtering.FilterByTemperatureSchema(
                minimum_temperature=298.0, maximum_temperature=320.0
            ),
            filtering.FilterByPressureSchema(
                minimum_pressure=100.0, maximum_pressure=101.4
            ),
            # Retain only density and enthalpy of mixing data points which
            # have been measured for the same systems.
            filtering.FilterByPropertyTypesSchema(
                property_types=[
                    "Density",
                    "EnthalpyOfMixing",
                ],
                n_components={
                    "Density": [1, 2],
                    "EnthalpyOfMixing": [2],
                },
                strict=True,
            ),
            # Convert density data to excess molar volume where possible.
            conversion.ConvertExcessDensityDataSchema(),
            filtering.FilterDuplicatesSchema(),
            # Apply the property filter again to retain only those systems
            # which have data points for all the properties of interest.
            filtering.FilterByPropertyTypesSchema(
                property_types=[
                    "Density",
                    "EnthalpyOfMixing",
                    "ExcessMolarVolume",
                ],
                n_components={
                    "Density": [2],
                    "EnthalpyOfMixing": [2],
                    "ExcessMolarVolume": [2],
                },
                strict=True,
            ),
            # Remove any substances measured for systems with undefined
            # stereochemistry
            filtering.FilterByStereochemistrySchema(),
            # Remove any measurements made for systems where any of the components
            # are charged.
            filtering.FilterByChargedSchema(),
            # Remove measurements made for ionic liquids
            filtering.FilterByIonicLiquidSchema(),
            # Remove any molecules containing elements other than C, O, N and H
            filtering.FilterByElementsSchema(allowed_elements=["C", "O", "N", "H"]),
            # Retain only measurements made for substances which contain environments
            # of interest.
            filtering.FilterByEnvironmentsSchema(
                environments=[
                    ChemicalEnvironment.Alcohol,
                    ChemicalEnvironment.CarboxylicAcidEster,
                    ChemicalEnvironment.CarboxylicAcid,
                    ChemicalEnvironment.Amine,
                    ChemicalEnvironment.CarboxylicAcidAmide,
                    ChemicalEnvironment.Ether,
                    ChemicalEnvironment.Nitrile,
                    ChemicalEnvironment.Ketone,
                    ChemicalEnvironment.Aldehyde,
                ]
            ),
            # # Attempt to select a reasonable number of diverse substances
            selection.SelectSubstancesSchema(
                target_environments=[
                    ChemicalEnvironment.Alcohol,
                    ChemicalEnvironment.CarboxylicAcidEster,
                    ChemicalEnvironment.CarboxylicAcid,
                    ChemicalEnvironment.Amine,
                    ChemicalEnvironment.CarboxylicAcidAmide,
                    ChemicalEnvironment.Ether,
                    ChemicalEnvironment.Nitrile,
                    ChemicalEnvironment.Ketone,
                    ChemicalEnvironment.Aldehyde,
                ],
                n_per_environment=5,
                per_property=False,
            ),
            # Select the data points for different compositions.
            selection.SelectDataPointsSchema(
                target_states=[
                    TargetState(
                        property_types=[("Density", 1)],
                        states=[
                            State(
                                temperature=298.15,
                                pressure=101.325,
                                mole_fractions=(1.0,),
                            )
                        ],
                    ),
                    TargetState(
                        property_types=[
                            ("Density", 2),
                            ("EnthalpyOfMixing", 2),
                            ("ExcessMolarVolume", 2),
                        ],
                        states=[
                            State(
                                temperature=298.15,
                                pressure=101.325,
                                mole_fractions=(0.25, 0.75),
                            ),
                            State(
                                temperature=298.15,
                                pressure=101.325,
                                mole_fractions=(0.5, 0.5),
                            ),
                            State(
                                temperature=298.15,
                                pressure=101.325,
                                mole_fractions=(0.75, 0.25),
                            ),
                        ],
                    ),
                ]
            ),
        ]
    )
    # Apply the curation schema to yield the test set.
    test_set_frame = CurationWorkflow.apply(
        thermoml_data_frame, curation_schema, N_PROCESSES
    )

    test_set = DataSet.from_pandas(
        data_frame=test_set_frame,
        identifier="eval-bench-full",
        description="A data set composed of enthalpy of mixing, density, and "
        "excess molar volume data points designed with the aim of having a diverse "
        "data set which can be estimated using a minimum number of simulations."
        "\n\n"
        "In practice, this was attempted by selecting only data points for the "
        "same set of substance and measured at, where possible, the same set of "
        "state points. These factors combined should in principle lead to a data "
        "set where many of the contained data points can be estimated using the "
        "same simulation outputs."
        "\n\n"
        "Note in this data set, all temperatures (K) have been rounded to one "
        "decimal place, and all pressures (kPa) to zero decimal places."
        "\n\n"
        "This data set was originally curated as for the benchmarking component of "
        "the `openff-evaluator` project",
        authors=AUTHORS,
    )

    test_set = test_set.upload()

    os.makedirs("../../schemas/data-sets", exist_ok=True)

    test_set.to_pandas().to_csv(
        os.path.join("../../schemas/data-sets", f"{test_set.id}.csv"), index=False
    )
    test_set.to_file(
        os.path.join("../../schemas/data-sets", f"{test_set.id}.json")
    )


if __name__ == "__main__":
    main()

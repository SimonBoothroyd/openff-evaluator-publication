from typing import Any, Dict, Optional

from nonbonded.library.models.authors import Author
from nonbonded.library.models.engines import ForceBalance
from nonbonded.library.models.forcefield import ForceField, Parameter
from nonbonded.library.models.projects import Benchmark, Optimization, Project, Study
from nonbonded.library.models.targets import EvaluatorTarget
from openff.evaluator.forcefield import TLeapForceFieldSource
from openforcefield.typing.engines.smirnoff import ForceField as SMIRNOFFForceField


def common_optimization_options(
    n_molecules: int, allow_reweighting: bool, n_effective_samples: Optional[int] = None
) -> Dict[str, Any]:
    """Defines the common inputs to the optimizations"""

    return dict(
        force_field=ForceField.from_openff(SMIRNOFFForceField("openff-1.0.0.offxml")),
        parameters_to_train=[
            Parameter(handler_type="vdW", attribute_name=attribute_name, smirks=smirks)
            for attribute_name in ["epsilon", "rmin_half"]
            for smirks in [
                "[#1:1]-[#6X4]",
                "[#6:1]",
                "[#6X4:1]",
                "[#8:1]",
                "[#8X2H0+0:1]",
                "[#8X2H1+0:1]",
                "[#1:1]-[#8]",
                "[#1:1]-[#6X4]-[#7,#8,#9,#16,#17,#35]",
                "[#1:1]-[#6X3](~[#7,#8,#9,#16,#17,#35])~[#7,#8,#9,#16,#17,#35]",
            ]
        ],
        engine=ForceBalance(
            priors={"vdW/Atom/epsilon": 0.1, "vdW/Atom/rmin_half": 1.0}
        ),
        targets=[
            EvaluatorTarget(
                id="phys-prop",
                denominators={
                    "Density": "0.05 g / ml",
                    "EnthalpyOfVaporization": "25.5 kJ / mol",
                },
                data_set_ids=[
                    "bmfs-exp-train-rho",
                    "bmfs-exp-train-h-vap",
                    "bmfs-exp-test-rho",
                    "bmfs-exp-test-h-vap",
                ],
                allow_direct_simulation=True,
                n_molecules=n_molecules,
                allow_reweighting=allow_reweighting,
                n_effective_samples=n_effective_samples,
            )
        ],
        analysis_environments=[],
        max_iterations=12,
    )


def main():

    project = Project(
        id="openff-evaluator",
        name="OpenFF Evaluator Publication",
        description="This project contains all of the data which will go in to the "
        "initial OpenFF Evaluator publication."
        "\n\n"
        "In particular, this project contains to main studies: i) a showcase of the "
        "evaluators integration with ForceBalance and ii) to showcase the evaluators "
        "ability to easily benchmark common force fields against a test set of "
        "physical properties.",
        authors=[
            Author(
                name="Simon Boothroyd",
                email="simon.boothroyd@colorado.edu",
                institute="University of Colorado Boulder",
            )
        ],
        studies=[
            Study(
                id="optimization-showcase",
                project_id="openff-evaluator",
                name="Optimization Showcase",
                description="This study aims to showcase the integration between the "
                "OpenFF Evaluator framework and ForceBalance, showcasing advanced "
                "features such as the frameworks ability to employ reweighting of "
                "cached simulation data to potentially reduce the cost of an "
                "optimization.",
                optimizations=[
                    Optimization(
                        id="simulation-only",
                        study_id="optimization-showcase",
                        project_id="openff-evaluator",
                        name="Simulation Only",
                        description="An optimization against a simple set of pure "
                        "enthalpy of vaporization and density measurements, whereby "
                        "the training set may only be estimated using molecular "
                        "simulations (i.e. cached simulation data reweighting is "
                        "disabled).",
                        **common_optimization_options(
                            n_molecules=500,
                            allow_reweighting=False,
                        )
                    ),
                    Optimization(
                        id="simulation-reweighting",
                        study_id="optimization-showcase",
                        project_id="openff-evaluator",
                        name="Simulation + Reweighting",
                        description="An optimization against a simple set of pure "
                        "enthalpy of vaporization and density measurements, whereby "
                        "the training set may be estimated by reweighting cached "
                        "simulation data where available, or may otherwise fallback to "
                        "using molecular simulation.",
                        **common_optimization_options(
                            n_molecules=500,
                            allow_reweighting=True,
                            n_effective_samples=50,
                        )
                    ),
                ],
            ),
            Study(
                id="benchmark-showcase",
                project_id="openff-evaluator",
                name="Benchmark Showcase",
                description="This study aims to showcase the OpenFF Evaluator "
                "frameworks ability to readily, and performantly benchmark different "
                "force fields against data sets of physical properties."
                "\n\n"
                "The chosen force fields to benchmark are OpenFF 1.0.0 (codename "
                "parsley), GAFF, and GAFF 2.",
                benchmarks=[
                    Benchmark(
                        id="openff-1-0-0",
                        study_id="benchmark-showcase",
                        project_id="openff-evaluator",
                        name="OpenFF 1.0.0",
                        description="An benchmark against the OpenFF 1.0.0 (codename "
                        "parsley) force field.",
                        test_set_ids=["eval-bench-full"],
                        optimization_id=None,
                        force_field=ForceField.from_openff(
                            SMIRNOFFForceField("openff-1.0.0.offxml")
                        ),
                        analysis_environments=[],
                    ),
                    Benchmark(
                        id="gaff-1",
                        study_id="benchmark-showcase",
                        project_id="openff-evaluator",
                        name="Amber GAFF",
                        description="An benchmark against the Amber GAFF force field.",
                        test_set_ids=["eval-bench-full"],
                        optimization_id=None,
                        force_field=ForceField(
                            inner_content=TLeapForceFieldSource("leaprc.gaff").json()
                        ),
                        analysis_environments=[],
                    ),
                    Benchmark(
                        id="gaff-2",
                        study_id="benchmark-showcase",
                        project_id="openff-evaluator",
                        name="Amber GAFF 2",
                        description="An benchmark against the Amber GAFF 2 force "
                        "field.",
                        test_set_ids=["eval-bench-full"],
                        optimization_id=None,
                        force_field=ForceField(
                            inner_content=TLeapForceFieldSource("leaprc.gaff2").json()
                        ),
                        analysis_environments=[],
                    ),
                ],
            ),
        ],
    )

    project = project.upload()

    with open("../../schemas/project.json", "w") as file:
        file.write(project.json())


if __name__ == "__main__":
    main()

The Open Force Field Evaluator: An automated, efficient, and scalable framework for the estimation of physical properties from molecular simulation 
===================================================================================================================================================

This repository contains the scripts, inputs and the results generated as part of the *The Open Force Field Evaluator: 
An automated, efficient, and scalable framework for the estimation of physical properties from molecular simulation* 
publication.

#### Structure

This repository is structured into four main directories:

* `inputs-and-results` - contains the main input files required to reproduce this study. The project
  structure was for the most part generated automatically using the 
  [`nonbonded`](https://github.com/SimonBoothroyd/nonbonded) package.
  
* `schema` - contains the [`nonbonded`](https://github.com/SimonBoothroyd/nonbonded) schemas which define the entirety 
  of the project, including definitions of the
  which optimizations and benchmarks to be performed and their respective training and test data sets.
  
* `scripts` - contains the script used to curate the training and test data sets, generate the input 
  [`nonbonded`](https://github.com/SimonBoothroyd/nonbonded) schemas, and scripts which perform ancillary data analysis 
  such as estimating timing information. 

#### Experimental Data Sets

The experimental data sets used in this project were curated from the [NIST ThermoML](https://trc.nist.gov/ThermoML.html)
archive. The citations for the individual measurements can be found in `DATA_CITATIONS.bib` 

#### Reproduction

The exact outputs reported in the publication (including the conda environment used to generate them) have been included
as tagged releases to this repository. 

For those looking to reproduce the study, the required dependencies may be obtained directly using conda:

```
conda install --name openff-evaluator-publication \
              -c conda-forge \
              -c omnia \
              -c openeye \
              -c simonboothroyd \
              nonbonded \
              openeye-toolkits
```

In most cases the optimizations and benchmarks can be re-run using the following commands

```
### Run an optimization
cd inputs-and-results/openff-evaluator/studies/optimization-showcase/optimizations/.../
nonbonded optimization run
nonbonded optimization analyze

### Run a benchmark
cd inputs-and-results/openff-evaluator/studies/benchmark-showcase/benchmarks/.../
nonbonded benchmark run
nonbonded benchmark analyze
```

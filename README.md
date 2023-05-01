# tbiExtractor

My local version of the original tbiExtractor, updated with newer versions of `networkx` and some accomoodations for deprecated features in `pandas`.

tbiExtractor, extends pyConTextNLP, a regular expression algorithm using negation detection and contextual features, to create a framework for extracting TBI common data elements from radiology reports. The algorithm inputs a radiology report and outputs a structured summary containing 27 clinical findings with their respective annotations.

Default lexical targets: aneurysm, anoxic, atrophy, cistern, contusion, diffuse_axonal, epidural_hemorrhage, facial_fracture, fluid, gray_white_differentiation, hemorrhage, herniation, hydrocephalus, hyperdensities, hypodensities, intracranial_pathology, intraparenchymal_hemorrage, intraventricular_hemorrhage, ischemia, mass_effect, microhemorrhage, midline_shift, pneumocephalus, skull_fracture, subarachnoid_hemorrhage, subdural_hemorrhage, swelling.

Default annotations: PRESENT, SUSPECTED, INDETERMINATE, ABSENT, ABNORMAL, NORMAL.

Citation: Mahan M, Rafter D, Casey H, Engelking M, Abdallah T, Truwit C, et al. (2020) tbiExtractor: A framework for extracting traumatic brain injury common data elements from radiology reports. PLoS ONE 15(7): e0214775. [https://doi.org/10.1371/journal.pone.0214775](https://doi.org/10.1371/journal.pone.0214775)

## Input

**report_file (str)**: Path to the .txt file containing the radiology report.

**save_target_phrases (bool)**:  If True, save the lexical target phrases identified in the report for the resulting annotation.

**save_modifier_phrases (bool)**: If True, save the lexical modifier phrases identified in the report for the resulting annotation.

*>>>>> Can only set to include or exclude lexical target options to limit the search. Defaults to standard target list.*

**include_targets (list)**: A subset of the available lexical targets options to include. Default: None, resulting in standard target list output.

**exclude_targets (list)**: A subset of the available lexical targets options to exclude. Default: None, resulting in standard target list output.


## Process

1. Parse inputs to set configuration for tbiExtractor algorithm.

2. Annotation of sentences constituting the report.
	- Sentence markup followed by span, modifier, and distance pruning

3. Annotation of the report.
	- Report markup with revisions for omitted, duplicate, and derived targets.


## Output

The output is a Pandas DataFrame:

Rows: each row contains one annotation for each of the twenty-seven common data elements (or an input configured subset).

Columns:

target phrase: the target literal extracted from the radiology report document (if input configured).

target group: one of the twenty-seven common data elements generated via the target phrase.

modifier phrase: a comma separated list of the modifier literals extracted from the radiology report document (if input configured).

modifier group: the annotation for the target group based on the modifier phrase.

	OPTIONS: PRESENT, ABSENT, INDETERMINATE, NOT SPECIFIED, ABNORMAL, NORMAL.

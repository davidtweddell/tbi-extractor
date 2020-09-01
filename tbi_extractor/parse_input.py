"""Parse inputs to set configuration for tbiExtractor algorithm."""

import logging
import os
import pkg_resources

import spacy
import pyConTextNLP.itemData as itemData


log = logging.getLogger(__name__)


targets_file = pkg_resources.resource_filename(__name__, "data/lexical_targets.tsv")
modifiers_file = pkg_resources.resource_filename(__name__, "data/lexical_modifiers.tsv")


def run(
    report_file,
    TARGETS,
    include_targets=None,
    exclude_targets=None,
):
    """Run the parsing of inputs to set the objects required for tbiExtractor.

    Args:
        report_file (pathlib.PosixPath): Path to the .txt file
            containing the radiology report.

        TARGETS (list): Default list of lexical targets.

        >>>>> Can only set to include or exclude lexical target options to limit
                the search. Defaults to standard target list.

        include_targets (list): A subset of the available lexical targets options to
            include. Default: None, resulting in standard target list output.

        exclude_targets (list): A subset of the available lexical targets options to
            exclude. Default: None, resulting in standard target list output.

    Returns:
        targets (pyConTextNLP.itemData.itemData): itemData stores a literal,
            category, regular expression, and rule of the targets extracted
            from the targets_file input.

        modifiers (pyConTextNLP.itemData.itemData): itemData stores a literal,
            category, regular expression, and rule of the modifiers extracted
            from the modifiers_file input.

        doc (spacy.tokens.doc.Doc): spaCy Document containing the radiology
            report.

    """
    # Load lexical targets and lexical modifiers as itemData
    targets = itemData.instantiateFromCSVtoitemData(f"file:{targets_file}")
    modifiers = itemData.instantiateFromCSVtoitemData(f"file:{modifiers_file}")

    # From include and exclude lists, determine algorithm targets
    specified_targets = alter_default_input(
        TARGETS, include=include_targets, exclude=exclude_targets
    )

    # Remove lexical targets from investigation set
    targets = [x for x in targets if x.categoryString() in specified_targets]

    # Load spacy model
    nlp = download_spacy_model()

    # Load the radiology report from file
    if report_file.is_file():

        with open(report_file, "r") as report_obj:
            report = report_obj.read().replace("\n", "")

    else:
        log.error("Unable to establish pathway to report file.")
        os.sys.exit(1)

    # Convert report to spacy container
    doc = nlp(report)

    return list(specified_targets), targets, modifiers, doc


def alter_default_input(DEFAULT, include=None, exclude=None):
    """Alter a default list of items according to a include or exclude list.
    Can only set to include or exclude, not both.
    Defaults to set of the DEFAULT input list.

    """
    if isinstance(include, list) and exclude is None:

        to_include = set(include)
        default_standard = set(DEFAULT)
        output = set.intersection(to_include, default_standard)

        if to_include != output:
            ignored = set.difference(to_include, output)
            log.info(
                f"Expects a list of a subset of the available options to include: {DEFAULT}."
            )
            log.info(f"The following include items were not considered: {ignored}.")

    elif isinstance(exclude, list) and include is None:

        to_exclude = set(exclude)
        default_standard = set(DEFAULT)
        output = set.difference(default_standard, to_exclude)

        if to_exclude != set.difference(default_standard, output):
            ignored = set.difference(
                to_exclude, set.difference(default_standard, output)
            )
            log.info(
                f"Expects a list of a subset of the available options to exclude: {DEFAULT}."
            )
            log.info(f"The following exclude items were not considered: {ignored}.")

    elif include is None and exclude is None:

        output = set(DEFAULT)

    else:
        log.critical("You can only provide a list to include or exclude.")
        os.sys.exit(1)

    if len(output) < 1:
        log.critical(
            "You can only include or exclude a subset of the available "
            "options in the default list. Please read the documentation "
            "for details."
        )
        os.sys.exit(1)

    return output


def download_spacy_model():
    """If the spaCy model doesn't exist, download.
    Typically achieved via: python -m spacy download en"""

    try:
        nlp = spacy.load("en")
    except OSError:
        log.info("Downloading language model spaCy.")
        spacy.cli.download("en")
        nlp = spacy.load("en")
        log.info("Download completed.")

    return nlp

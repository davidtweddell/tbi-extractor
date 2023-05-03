#!/usr/bin/env python3
"""Main script for tbiExtractor."""

import argparse
import logging
import os
from pathlib import Path

import parse_input
import annotate_sentences
import annotate_report


FORMAT = "[%(asctime)s - %(levelname)s - %(name)s:%(lineno)d] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT, datefmt="%Y-%m-%d")
log = logging.getLogger()

TARGETS = [
    # "aneurysm",
    "anoxic",
    # "atrophy",
    # "cistern",
    "contusion",
    "diffuse_axonal",
    "edema",
    "edh",
    # "facial_fracture",
    # "fluid",
    # "gray_white_differentiation",
    # "hemorrhage",
    "herniation",
    # "hydrocephalus",
    # "hyperdensities",
    # "hypodensities",
    # "intracranial_pathology",
    "iph",
    "ivh",
    "ischemia",
    # "mass_effect",
    # "microhemorrhage",
    "midline_shift",
    # "pneumocephalus",
    "skull_fracture",
    "sah",
    "sdh",
]


def run(
    report_file,
    save_target_phrases=False,
    save_modifier_phrases=False,
    include_targets=None,
    exclude_targets=None,
):
    """Orchestrate tbiExtractor.

    Args:
        report_file (str): Path to the .txt file containing the radiology report.

        save_target_phrases (bool):  If True, save the lexical target phrases
            identified in the report for the resulting annotation.

        save_modifier_phrases (bool): If True, save the lexical modifier phrases
            identified in the report for the resulting annotation.

        >>>>> Can only set to include or exclude lexical target options to limit
                the search. Defaults to standard target list.

        include_targets (list): A subset of the available lexical targets options to
            include. Default: None, resulting in standard target list output.

        exclude_targets (list): A subset of the available lexical targets options to
            exclude. Default: None, resulting in standard target list output.

    Returns:
        df (pandas.core.frame.DataFrame): dataframe containing each identified
            target phrase with its associated modifer phrase, if indicated in arguments;
            default includes the target group and modifier group.

    """
    # Set input for tbiExtractor algorithm
    specified_targets, targets, modifiers, doc = parse_input.run(
        Path(report_file),
        TARGETS,
        include_targets,
        exclude_targets,
    )
    print(f'>>> Parsed input')

    # Annotate sentences
    df = annotate_sentences.run(targets, modifiers, doc)
    print(f'>>> annotated sentences')

    # Annotate report
    df = annotate_report.run(df, specified_targets)
    print(f'>>> annotated report')

    # Polish output
    if not save_target_phrases:
        df.drop(columns="target_phrase", inplace=True)
    if not save_modifier_phrases:
        df.drop(columns="modifier_phrase", inplace=True)

    df.sort_values("target_group", axis=0, inplace=True)
    df.reset_index(inplace=True, drop="index")

    # Output annotated report as dataframe
    return df


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run tbiExtractor")

    parser.add_argument(
        "--report_file",
        required=True,
        help="The path to the .txt file containing the radiology report.",
    )
    parser.add_argument(
        "--save_target_phrases",
        action="store_true",
        default=False,
        help="Set to save the lexical target phrases identified in the report for the resulting annotation.",
    )
    parser.add_argument(
        "--save_modifier_phrases",
        action="store_true",
        default=False,
        help="Set to save the lexical modifier phrases identified in the report for the resulting annotation.",
    )

    # Can either set targets to include or exclude to limit the number of lexical targets used;
    # otherwise, all 27 lexical targets are annotated
    group_targets = parser.add_mutually_exclusive_group()

    group_targets.add_argument(
        "--include_targets",
        nargs="+",
        default=TARGETS,
        help=f"To limit the lexical targets, list a subset of the available options to include: {TARGETS}.",
    )

    group_targets.add_argument(
        "--exclude_targets",
        nargs="+",
        default=None,
        help=f"To limit the lexical targets, list a subset of the available options to exclude: {TARGETS}.",
    )

    args = parser.parse_args()

    # If the report is not a file, then exit
    report = Path(args.report_file)
    if not report.is_file():
        print("Unable to establish pathway to report file.")
        os.sys.exit(1)

    run(
        report_file=args.report_file,
        save_target_phrases=args.save_target_phrases,
        save_modifier_phrases=args.save_modifier_phrases,
        include_targets=args.include_targets,
        exclude_targets=args.exclude_targets,
    )
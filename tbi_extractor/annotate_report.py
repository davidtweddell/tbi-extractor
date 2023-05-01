"""Report markup with revisions for omitted, duplicate, and derived targets."""
import logging

import pandas as pd


log = logging.getLogger(__name__)


def run(df, target_list):
    """Orchestrate report annotation.

    Args:
        df (pandas.core.frame.DataFrame): dataframe containing each identified
            target phrase with its associated modifer phrase; the target group
            and modifier group are also returned.

        target_list (list): unique list of target phrases used for annotation.

    Returns:
        df (pandas.core.frame.DataFrame): dataframe containing each identified
            target phrase with its associated modifer phrase; the target group
            and modifier group are also returned.

    """
    # Ommitted targets: add targets that are missing from output based on
    # unique target list; default to absent or normal, depending upon target
    df.reset_index(inplace=True, drop="index")
    df = ommitted_targets(df, target_list)

    # Duplicate targets: if duplicate lexical targets are identified,
    # the majority vote is selected
    df.reset_index(inplace=True, drop="index")
    df = duplicate_targets(df)

    # Change modifier group to match those given to physicians
    df.reset_index(inplace=True, drop="index")
    df = modifier_type_physician_match(df, target_list)

    # Derived targets:
    # Change hemorrhage NOS annotation to absent, if specific hemorrhages exist
    df.reset_index(inplace=True, drop="index")
    df = is_specific_hemorrhage(df)

    # Change extraaxial fluid collection annotation to present/suspected,
    # if specific hemorrhages present/suspected
    df.reset_index(inplace=True, drop="index")
    df = is_extraaxial_fluid_collection(df)

    # Change intracranial pathology annotation to present, if pathology exists
    df.reset_index(inplace=True, drop="index")
    df = is_intracranial_pathology(df)

    return df


def ommitted_targets(df, target_list):
    """Add in lexical targets with default lexical modifiers for those not
        found in the report.

     Args:
        df (pandas.core.frame.DataFrame): dataframe containing each identified
            target phrase with its associated modifer phrase; the target group
            and modifier group are also returned.

        target_list (list): unique list of target phrases used for annotation.

    Returns:
        df (pandas.core.frame.DataFrame): dataframe containing each identified
            target phrase with its associated modifer phrase; the target group
            and modifier group are also returned.

    """
    targets_in_report = set(df["target_group"])
    targets_not_in_report = list(set(target_list) - targets_in_report)

    output_columns = [
        "target_phrase",
        "target_group",
        "modifier_phrase",
        "modifier_group",
    ]

    for target in targets_not_in_report:

        if target == "cistern" or target == "gray_white_differentiation":
            df_default = pd.DataFrame(
                [[target, target, "default", "normal"]], columns=output_columns
            )
            df = pd.concat([df, df_default], sort=False)
            # df = df.append(df_default, sort=False)

        else:
            df_default = pd.DataFrame(
                [[target, target, "default", "absent"]], columns=output_columns
            )
            df = pd.concat([df, df_default], sort=False)
            # df = df.append(df_default, sort=False)
            # df = df.append(df_default, sort=False)

    return df


def duplicate_targets(df):
    """Remove duplicate lexical targets based on majority vote. If two or more
        lexical targets are tied, and the majority, both remain in the output.

        For example, if a lexical target appears in the radiology report three
        times and the lexical modifiers for two occurrences have an annotation
        of ABSENT and the other has an annotation of PRESENT, tbiExtractor will
        choose ABSENT. Similarly, if there are two lexical modifiers with an
        annotation of PRESENT, two with ABSENT, and one with SUSPECTED,
        tbiExtractor removes SUSPECTED based on the majority vote.

    Args:
        df (pandas.core.frame.DataFrame): dataframe containing each identified
            target phrase with its associated modifer phrase; the target group
            and modifier group are also returned.

        target_list (list): unique list of target phrases used for annotation.

    Returns:
        df (pandas.core.frame.DataFrame): dataframe containing each identified
            target phrase with its associated modifer phrase; the target group
            and modifier group are also returned.

    """
    # Find duplicate target_groups
    duplicate_groups = df[df.duplicated(subset="target_group", keep=False)]
    unique_target_groups = set(duplicate_groups["target_group"].tolist())

    # Check modifier type for duplicate groups and replace with
    # maximum vote or ordering if equal number of annotations
    for target_group in unique_target_groups:

        modifier_types = duplicate_groups.loc[
            duplicate_groups["target_group"] == target_group, "modifier_group"
        ]
        counts = modifier_types.value_counts()
        who_is_max = counts[counts == counts.max()]

        if len(who_is_max) > 0:
            df = combine_duplicate_targets_modifiers(
                df, target_group, pd.Series(who_is_max.index)
            )

        # Check for duplicate targets with the same modifier type,
        # then combine them to one row and continue
        df = combine_matching_targets_modifiers(df, target_group)

    return df


def combine_duplicate_targets_modifiers(df, target_group, modifier_group):
    """Combine duplicates of lexical target to lexical modifier group"""

    if target_group in ["fluid", "hemorrhage", "intracranial_pathology"]:
        modifiers = [
            "absent",
            "indeterminate",
            "suspected",
            "present",
            "normal",
            "abnormal",
        ]
    else:
        modifiers = [
            "present",
            "suspected",
            "indeterminate",
            "absent",
            "abnormal",
            "normal",
        ]

    # In order of list of modifiers, go through and drop all that are not that modifier
    for modifier in modifiers:

        if modifier in modifier_group.tolist():

            drop_index = df.loc[
                (
                    (df["target_group"] == target_group)
                    & (df["modifier_group"] != modifier)
                )
            ].index

            df.drop(index=drop_index, axis=1, inplace=True)

            # If drop occured, then break loop as we are done removing
            break

    return df


def combine_matching_targets_modifiers(df, target_group):
    """Concatenate modifier phrase targets for matching target group and
    modifier group."""

    # If modifier groups are equivalent for the target group,
    # only one will be retained; modifier phrases concatenated
    concat_modifiers = (
        df.loc[(df["target_group"] == target_group), "modifier_phrase"]
        .drop_duplicates(keep="first")
        .str.cat(sep=", ")
    )

    # Replace modifiers for all items in the target group
    df.loc[(df["target_group"] == target_group), "modifier_phrase"] = concat_modifiers

    # The target phrases are concatenated
    concat_targets = (
        df.loc[(df["target_group"] == target_group), "target_phrase"]
        .drop_duplicates(keep="first")
        .str.cat(sep=", ")
    )

    # Replace targets for all items in target group
    df.loc[(df["target_group"] == target_group), "target_phrase"] = concat_targets

    # Rows will now be duplicates for target groups with same modifier group
    df.drop_duplicates(
        subset=["target_group", "modifier_group"], keep="first", inplace=True
    )

    return df


def modifier_type_physician_match(df, target_list):
    """Change modifier groups to match those given to physicians; these are
    also stored in the lexical targets tsv."""

    # Change modifier group for abnormal/normal annotations
    for item in ["cistern", "gray_white_differentiation"]:

        # Find where item is not default modified
        modifiers = df.loc[
            ((df["modifier_phrase"] != "default") & (df["target_group"] == item)),
            "modifier_phrase",
        ].str.cat(sep=", ")

        if modifiers != "":
            modifier_groups = df.loc[df["target_group"] == item, "modifier_group"]

            # Lexical targets in abnormal list can either be normal or abnormal
            normals = ["normal", "absent"]
            normal_modifier_group = [
                "normal" for item in list(modifier_groups) if item in normals
            ]
            abnormals = ["abnormal", "present", "suspected", "indeterminate"]
            abnormal_modifier_group = [
                "abnormal" for item in list(modifier_groups) if item in abnormals
            ]

            if len(abnormal_modifier_group) == 0 and len(normal_modifier_group) > 0:

                # If "abnormal" not present and "normal" present, then mark item as "normal" in df
                df.loc[(df["target_group"] == item), "modifier_group"] = "normal"
                df.loc[(df["target_group"] == item), "modifier_phrase"] = modifiers

            elif len(abnormal_modifier_group) > 0:

                # If "abnormal" present, then mark item as "abnormal" in df
                df.loc[(df["target_group"] == item), "modifier_group"] = "abnormal"
                df.loc[(df["target_group"] == item), "modifier_phrase"] = modifiers

    # Change modifier group for present/suspected/indeterminate/absent annotations
    for item in [
        item
        for item in target_list
        if item not in ["cistern", "gray_white_differentiation"]
    ]:

        # Find where item is not default modified
        modifiers = df.loc[
            ((df["modifier_phrase"] != "default") & (df["target_group"] == item)),
            "modifier_phrase",
        ].str.cat(sep=", ")

        if modifiers != "":
            modifier_group = df.loc[df["target_group"] == item, "modifier_group"]

            if "abnormal" in list(modifier_group):

                # If 'abnormal' in modifier types, change to 'present'
                df.loc[
                    (
                        (df["target_group"] == item)
                        & (df["modifier_group"] == "abnormal")
                    ),
                    "modifier_group",
                ] = "present"

                df.loc[
                    (
                        (df["target_group"] == item)
                        & (df["modifier_group"] == "abnormal")
                    ),
                    "modifier_phrase",
                ] = modifiers

            if "normal" in list(modifier_group):

                # If 'normal' in modifier types, change to 'absent'
                df.loc[
                    ((df["target_group"] == item) & (df["modifier_group"] == "normal")),
                    "modifier_group",
                ] = "absent"

                df.loc[
                    (
                        (df["target_group"] == item)
                        & (df["modifier_group"] == "abnormal")
                    ),
                    "modifier_phrase",
                ] = modifiers

    return df


def is_specific_hemorrhage(df):
    """If a specific hemorrhage present or suspected,
    then hemorrhage NOS changed to absent."""

    hemorrhages = [
        "epidural_hemorrhage",
        "subarachnoid_hemorrhage",
        "subdural_hemorrhage",
    ]
    present = ["present", "suspected"]

    specific_hemorrhage = len(
        df.loc[
            (
                (df["target_group"].isin(hemorrhages))
                & (df["modifier_group"].isin(present))
            )
        ]
    )

    modifiers = df.loc[
        ((df["target_group"] == "hemorrhage")), "modifier_phrase"
    ].str.cat(sep=", ")

    if (specific_hemorrhage > 0) and (len(df["target_group"].isin(["hemorrhage"])) > 0):

        df.loc[(df["target_group"] == "hemorrhage"), "modifier_group"] = "absent"
        df.loc[(df["target_group"] == "hemorrhage"), "modifier_phrase"] = (
            modifiers + ", is_specific_hemorrhage"
        )

    return df


def is_extraaxial_fluid_collection(df):
    """If hemorrhage present, fluid present; if hemorrhage suspected,
    fluid suspected if previously default."""

    hemorrhages = [
        "epidural_hemorrhage",
        "subarachnoid_hemorrhage",
        "subdural_hemorrhage",
    ]

    specific_hemorrhage = df.loc[(df["target_group"].isin(hemorrhages))]
    modifiers = df.loc[(df["target_group"] == "fluid"), "modifier_phrase"].str.cat(
        sep=", "
    )

    if "present" in specific_hemorrhage["modifier_group"].tolist():

        # If any hemorrhage "present", then fluid is "present"
        df.loc[(df["target_group"] == "fluid"), "modifier_group"] = "present"
        df.loc[(df["target_group"] == "fluid"), "modifier_phrase"] = (
            modifiers + ", is_extraaxial_fluid_collection"
        )

    elif ("suspected" in specific_hemorrhage["modifier_group"].tolist()) and (
        "present" not in specific_hemorrhage["modifier_group"].tolist()
    ):

        # If any hemorrhage "suspected" and not "present", then fluid "suspected", if fluid "default"
        is_default = df.loc[
            ((df["modifier_phrase"] == "default") & (df["target_group"] == "fluid"))
        ]

        if len(is_default) > 0:

            df.loc[(df["target_group"] == "fluid"), "modifier_group"] = "suspected"
            df.loc[(df["target_group"] == "fluid"), "modifier_phrase"] = (
                modifiers + ", is_extraaxial_fluid_collection"
            )

    # Otherwise, fluid is left as original target/modifier pair from algorithm

    return df


def is_intracranial_pathology(df):
    """If specific pathology present, change modifier group to present
    for intracranial pathology target."""

    pathology = [
        "gray_white_differentiation",
        "cistern",
        "hydrocephalus",
        "pneumocephalus",
        "midline_shift",
        "mass_effect",
        "diffuse_axonal",
        "anoxic",
        "herniation",
        "aneurysm",
        "contusion",
        "fluid",
        "swelling",
        "ischemia",
        "hemorrhage",
        "intraventricular_hemorrhage",
        "intraparenchymal_hemorrage",
    ]

    present = ["present", "suspected", "abnormal"]

    modifiers = df.loc[
        (df["target_group"] == "intracranial_pathology"), "modifier_phrase"
    ].str.cat(sep=", ")

    specific_pathology = df.loc[
        ((df["target_group"].isin(pathology)) & (df["modifier_group"].isin(present)))
    ]

    path_modifier = df.loc[
        (df["target_group"] == "intracranial_pathology"), "modifier_phrase"
    ].tolist()

    if (len(specific_pathology) > 0) and ("no" not in str(path_modifier)):

        df.loc[
            (df["target_group"] == "intracranial_pathology"), "modifier_group"
        ] = "present"
        df.loc[(df["target_group"] == "intracranial_pathology"), "modifier_phrase"] = (
            modifiers + ", is_intracranial_pathology"
        )

    return df

"""Sentence markup followed by span, modifier, and distance pruning."""
import logging

import numpy as np
import pandas as pd
import pyConTextNLP.pyConTextGraph as pyConText


log = logging.getLogger(__name__)


def run(targets, modifiers, doc):
    """Orchestrate sentence annotation.

    Args:
        targets (pyConTextNLP.itemData.itemData): itemData stores a literal,
            category, regular expression, and rule of the targets extracted
            from the targets_file input.

        modifiers (pyConTextNLP.itemData.itemData): itemData stores a literal,
            category, regular expression, and rule of the modifiers extracted
            from the modifiers_file input.

        doc (spacy.tokens.doc.Doc): spaCy Document containing the radiology
            report.

    Returns:
        df (pandas.core.frame.DataFrame): dataframe containing each identified
            target phrase with its associated modifer phrase; the target group
            and modifier group are also returned.

    """
    # Annotate radiology report by applying lexical targets and lexical modifiers
    # with span and modifier pruning
    context = annotate_sentence(targets, modifiers, doc)

    # Apply distance pruning and return dataframe containing sentence markups across the report
    df = distance_pruning(context)

    return df


def annotate_sentence(targets, modifiers, doc):
    """Annotate a spaCy Document for lexical targets and lexical modifiers.

    pyConTextNLP uses NetworkX directional graphs to represent the markup;
    nodes in the graph will be the concepts that are identified in the sentence
    and edges in the graph will be the relationships between those concepts.

    Args:
        targets (pyConTextNLP.itemData.itemData): itemData stores a literal,
            category, regular expression, and rule of the targets extracted
            from the targets_file input.

        modifiers (pyConTextNLP.itemData.itemData): itemData stores a literal,
            category, regular expression, and rule of the modifiers extracted
            from the modifiers_file input.

        doc (spacy.tokens.doc.Doc): spaCy Document containing the radiology
            report.

    Returns:
        context (pyConTextNLP.pyConTextGraph.ConTextDocument): object containing
            sentence markups across the report understood as a digraph of the
            relationships between lexical targets and lexical modifiers.

    """
    # Create the pyConText instance for the report
    context = pyConText.ConTextDocument()

    # Split the report into individual sentences
    sentences = [sent.string.strip() for sent in doc.sents]

    # For the report, markup sentences, with span and modifier pruning, and add markup to context
    for s in sentences:
        markup = markup_sentence(targets, modifiers, s.lower())
        context.addMarkup(markup)

    return context


def markup_sentence(targets, modifiers, sentence):
    """Markup sentence with lexical targets and lexical modifiers.

    Args:
        targets (pyConTextNLP.itemData.itemData): itemData stores a literal,
            category, regular expression, and rule of the targets extracted
            from the targets_file input.

        modifiers (pyConTextNLP.itemData.itemData): itemData stores a literal,
            category, regular expression, and rule of the modifiers extracted
            from the modifiers_file input.

        sentence (str): a string representing one sentence of a report.

    Returns:
        markup (pyConTextNLP.pyConTextGraph.ConTextMarkup): object containing
            sentence markups across the sentence understood as a digraph  of the
            relationships between lexical targets and lexical modifiers.

    """
    # Create the pyConText instance for the sentence
    markup = pyConText.ConTextMarkup()

    # Clean up and mark with modifiers and targets
    markup.setRawText(sentence)

    # Strip non alphanumeric and clean whitespace
    markup.cleanText()

    # Markup text
    markup.markItems(modifiers, mode="modifier")
    markup.markItems(targets, mode="target")

    # Span pruning: prune concepts that are a subset of another identified
    # concept (modifiers and targets are treated separately); in other words,
    # delete any objects that lie within the span of another object
    markup.pruneMarks()

    # Loop through the marked targets and for each target apply the modifiers
    markup.applyModifiers()

    # Modifier pruning: drop any modifiers that didn't get hooked up with a target
    markup.dropInactiveModifiers()

    return markup


def distance_pruning(context):
    """Prune sentence annotations based on nearest character distance of a
        lexical modifer to lexical target, resulting in one modifier per target.

    Args:
        context (pyConTextNLP.pyConTextGraph.ConTextDocument): object containing
            sentence markups across the report understood as a digraph of the
            relationships between lexical targets and lexical modifiers.

    Returns:
        df (pandas.core.frame.DataFrame): dataframe containing each identified
            target phrase with its associated modifer phrase; the target group
            and modifier group are also returned.

    """
    # Setup dataframe to store results
    output_columns = [
        "target_phrase",
        "target_group",
        "modifier_phrase",
        "modifier_group",
    ]
    df = pd.DataFrame(columns=output_columns)

    # Get graph of document with markups
    g = context.getDocumentGraph()

    for idx, node in enumerate(g.nodes()):

        target_phrase = node.getPhrase()
        target_group = node.categoryString()
        is_type = node.getConTextCategory()  # is target or is modifier

        # Sanity check: only targets should have predecessors; modifiers can
        # be modified and therefore have both predecessors and successors
        if (is_type == "target") and (len(g.successors(node)) > 0):
            log.critical("Lexical target has successors.")

        # Skip modifier type nodes; focused on pruning in relation to targets
        if is_type == "modifier":
            continue

        # find nearest modifier for target with multiple modifiers in one sentence
        try:
            if len(g.predecessors(node)) > 1:
                target_span = node.getSpan()
                distance_columns = output_columns + ["left_diff", "right_diff"]
                modifier_distances = pd.DataFrame(columns=distance_columns)

                for i in range(len(g.predecessors(node))):
                    modifier_dist = pd.DataFrame(columns=distance_columns)
                    modifier_span = g.predecessors(node)[i].getSpan()
                    left_diff = target_span[0] - modifier_span[1]
                    right_diff = modifier_span[0] - target_span[1]

                    # if left or right difference negative, then the modifier is not on that side
                    if left_diff < 0:
                        left_diff = np.nan

                    if right_diff < 0:
                        right_diff = np.nan

                    modifier_phrase = g.predecessors(node)[i].getLiteral()
                    modifier_group = g.predecessors(node)[i].categoryString()

                    data = [
                        [
                            target_phrase,
                            target_group,
                            modifier_phrase,
                            modifier_group,
                            left_diff,
                            right_diff,
                        ]
                    ]
                    modifier_dist = pd.DataFrame(data, columns=distance_columns)
                    modifier_distances = modifier_distances.append(modifier_dist)

                if modifier_distances[["left_diff", "right_diff"]].isna().all().all():
                    # Unable to establish distance, keep all modifiers identified
                    nearest_modifier = modifier_distances[output_columns]
                else:
                    min_diff = np.nanmin(
                        [
                            modifier_distances["left_diff"].min(),
                            modifier_distances["right_diff"].min(),
                        ]
                    )
                    nearest_modifier = modifier_distances.loc[
                        (
                            (modifier_distances["left_diff"] == min_diff)
                            | (modifier_distances["right_diff"] == min_diff)
                        )
                    ]
                    nearest_modifier = nearest_modifier[output_columns]

            else:
                modifier_phrase = g.predecessors(node)[0].getLiteral()
                modifier_group = g.predecessors(node)[0].categoryString()
                data = [[target_phrase, target_group, modifier_phrase, modifier_group]]
                nearest_modifier = pd.DataFrame(data, columns=output_columns)

        except IndexError:
            # A lexical target was found with no available lexical modifiers in the sentence
            continue

        # add target and modifier, and their respective group, to dataframe
        df = df.append(nearest_modifier, ignore_index=True)

    # drop duplicate rows
    df.drop_duplicates(keep="first", inplace=True)

    return df

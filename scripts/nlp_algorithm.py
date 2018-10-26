# -*- coding: utf-8 -*-
"""
Created on Fri Aug 10 11:16:28 2018

@author: Margaret Mahan

Package versions:
    Python           3.6.6
    Pandas           0.23.4
    spaCy            2.0.12
    pyConTextNLP     0.6.2.0 (dependency: NetworkX 1.11)
    NumPy            1.15.0
"""

# imports
import pandas as pd
import spacy
import pyConTextNLP.pyConTextGraph as pyConText
import pyConTextNLP.itemData as itemData
import numpy as np
import datetime
import os


def main_nlp(df, filepart, data_path):
    
    ''' 
        input:
            df: Pandas dataframe, with one CT report per row, containing the following columns:
                PatientNum - patient identfication code
                CT_report - clean CT report, beginning with Findings section
                CT_report_id - unique numerical identifier for each CT report
            
            filepart: string part for output file, for example: "classify_tbi_project"
            
            data_path: string to data directory where lexical_targets.tsv and lexical_modifiers.tsv are stored
            
        output:
            df: Pandas dataframe, with one target-modifier pair per row, contianing the following columns:
                CT_report_id - unique numerical identifier for each CT report
                target - phrase of target as found in the CT report, for example: "extra-axial fluid collection"
                target_group - target type from lexical_targets.tsv, for example: "fluid"
                modifier - phrase for modifier associated with target, for example: "no evidence of"
                modifier_type - modifier type from lexical_modifiers.tsv, for example: "absent"
            
            the aforementioned df is also written to datapath as nlp_algorithm_output_*.csv
    '''
            
    # setup output file
    get_today = datetime.date.today()
    outfile = data_path + '/nlp_algorithm_output_' + filepart + '_' + str(get_today) + '.csv'
    
    # itemData contains a literal, category, regular expression, and rule
    # load targets and modifiers as itemData
    os.chdir(data_path)
    modifiers = itemData.instantiateFromCSVtoitemData("file:lexical_modifiers.tsv")
    targets = itemData.instantiateFromCSVtoitemData("file:lexical_targets.tsv")
    
    # load spacy model
    nlp = spacy.load('en')
    
    # empty dataframe to store results
    out_columns = ['CT_report_id', 'target', 'target_group', 'modifier', 'modifier_type']
    df_output = pd.DataFrame(columns=out_columns)

    # for each CT report, send to NLP algorithm
    for index, row in df.iterrows():
       
        doc = nlp(row['CT_report'])
        
        # pyConTextNLP uses NetworkX directional graphs to represent the markup: 
        # nodes in the graph will be the concepts that are identified in the sentence 
        # and edges in the graph will be the relationships between those concepts
        # send to analyzer to apply targets and modifiers
        context = analyzeReport(doc, targets, modifiers)
        
        # get graph of document with markups
        g = context.getDocumentGraph()
        
        for idx, node in enumerate(g.nodes()):
            
            target = node.getPhrase()               # target
            target_group = node.categoryString()    # target type
            is_type = node.getConTextCategory()     # is target or is modifier
            
            # sanity check; only targets should have predecessors
            # modifiers can be modified and therefore have both predecessors and successors
            if (is_type == 'target') and (len(g.successors(node)) > 0):
                print('ERROR: target has successors')
    
            # if node is a modifier, skip as we will focus on gathering targets with modifiers into dataframe
            if is_type == 'modifier':
                continue
      
            # find nearest modifier for target with multiple modifiers in one sentence
            try:
                
                target_span = node.getSpan()
                diff_columns = ['CT_report_id', 'target', 'target_group', 'modifier', 
                                'modifier_type', 'left_diff', 'right_diff']
                nearest_modifier = pd.DataFrame(columns=diff_columns)

                if len(g.predecessors(node)) > 1:
                
                    for i in range(len(g.predecessors(node))):
                        
                        modifier_span = g.predecessors(node)[i].getSpan()
                        left_diff = target_span[0] - modifier_span[1]
                        right_diff = modifier_span[0] - target_span[1]
                        
                        # if left or right difference negative, then the modifier is not on that side
                        if left_diff < 0: left_diff = np.nan
    
                        if right_diff < 0: right_diff = np.nan
    
                        modifier_type = g.predecessors(node)[i].categoryString()
                        modifier = g.predecessors(node)[i].getLiteral()
                        
                        data = [[row['CT_report_id'], target, target_group, modifier, modifier_type, left_diff, right_diff]]
                        modifier_span_df = pd.DataFrame(data, columns=diff_columns)
                        nearest_modifier = nearest_modifier.append(modifier_span_df)
                                            
                    min_diff = min([nearest_modifier['left_diff'].min(), nearest_modifier['right_diff'].min()])
                    modifier_df = nearest_modifier.loc[(
                                                        (nearest_modifier['left_diff'] == min_diff) | 
                                                        (nearest_modifier['right_diff'] == min_diff)
                                                       )]
                
                else:
                    modifier_type = g.predecessors(node)[0].categoryString()
                    modifier = g.predecessors(node)[0].getLiteral()
                    data = [[row['CT_report_id'], target, target_group, modifier, modifier_type]]
                    modifier_df = pd.DataFrame(data, columns=out_columns)
            
            except IndexError:
                continue
            
            # add target and modifier, and their respective group, to dataframe
            df_output = df_output.append(modifier_df[out_columns])
            
        # drop duplicate rows
        df_output.drop_duplicates(keep='first', inplace=True)
        
    # write results to file
    df_output.to_csv(outfile, index=False)          

    return df_output


def analyzeReport(doc, targets, modifiers):
    
    """given an individual radiology report, markup the report based on targets and modifiers"""

    # create the pyConText instance for the report
    context = pyConText.ConTextDocument()

    # split the report into individual sentences
    sentences = [sent.string.strip() for sent in doc.sents]
    
    # for the report, markup sentences and add markup to context
    for s in sentences:
        markup_sentence = markup_sentences(s.lower(), targets, modifiers)
        context.addMarkup(markup_sentence)

    return context


def markup_sentences(sentence, targets, modifiers):

    # create the pyConText instance for the sentence
    markup = pyConText.ConTextMarkup()

    # clean up and mark with modifiers and targets
    markup.setRawText(sentence)
    
    # strip non alphanumeric and clean whitespace
    markup.cleanText()
    
    # markup text
    markup.markItems(modifiers, mode="modifier")
    markup.markItems(targets, mode="target")

    # prune concepts that are a subset of another identified concept: delete any objects that 
    # lie within the span of another object; modifiers and targets are treated separately
    markup.pruneMarks()

    # loop through the marked targets and for each target apply the modifiers
    markup.applyModifiers()

    # drop any modifiers that didn't get hooked up with a target
    markup.dropInactiveModifiers()

    return markup


# eof
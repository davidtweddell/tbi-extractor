# -*- coding: utf-8 -*-
"""
Created on Sun Aug 12 14:32:15 2018

@author: Margaret Mahan

Package versions:
    Python            3.6.6
    pandas            0.23.4          
"""

# imports
import pandas as pd


# summarize ct_report
def ct_summary_report(df, ct_report, target_list):
        
    # for one ct report, gather all targets and modifiers
    df, report_targets = reset(df, ct_report)
          
    # add targets that are missing from algorithm output and default to absent or normal, depending upon target
    df = default_targets(df, ct_report, report_targets, target_list)
    df, report_targets = reset(df, ct_report)
    
    # combine duplicates
    df = combine_duplicates(df, ct_report, report_targets)
    df, report_targets = reset(df, ct_report)
    
    # change modifier types to match those given to physicians
    df = modifier_type_physician_match(df, ct_report, report_targets, target_list)
    df, report_targets = reset(df, ct_report)
    
    # change hemorrhage to absent, if specific hemorrhages exist
    df = is_specific_hemorrhage(df, ct_report, report_targets)
    df, report_targets = reset(df, ct_report)
        
    # updated extraaxial fluid collection and reload ct report targets
    df = is_extraaxial_fluid_collection(df, ct_report, report_targets)
    df, report_targets = reset(df, ct_report)
    
    # updated intracranial pathology
    df = is_intracranial_pathology(df, ct_report, report_targets)

    return df


def reset(df, ct_report):
    
    # reset df index and reload ct report targets
    
    df = df.reset_index()
    df.drop(columns='index', inplace=True)
    report_targets = df.loc[df['CT_report_id'] == ct_report]
    
    return df, report_targets


def default_targets(df, ct_report, report_targets, target_list):
    
    # add in targets with default modifiers for those not in df
    
    targets_in_report = set(report_targets['target_group'])
    targets_not_in_report = list(set(target_list) - targets_in_report)
    
    columns = ['CT_report_id', 'target', 'target_group', 'modifier', 'modifier_type']
    for target in targets_not_in_report:
        
        if target == 'cistern' or target == 'gray_white_differentiation':
            
            df2 = pd.DataFrame([[ct_report, target, target, 'default', 'normal']], columns=columns)
            df = df.append(df2, sort=False)

        else:
            
            df2 = pd.DataFrame([[ct_report, target, target, 'default', 'absent']], columns=columns)
            df = df.append(df2, sort=False)
            
    return df
            
    
def combine_duplicates(df, ct_report, report_targets):
        
    # combine duplicate target groups and modifier types
    
    # find duplicate target_groups
    duplicate_groups = report_targets[report_targets.duplicated(subset='target_group', keep=False)]
    unique_target_groups = set(duplicate_groups['target_group'].tolist())
        
    # check modifier type for duplicate groups and replace with maximum vote or ordering if equal numbers
    for group in unique_target_groups:
        
        modifier_types = duplicate_groups.loc[duplicate_groups['target_group'] == group, 'modifier_type']
        counts = modifier_types.value_counts()
        who_is_max = counts[counts == counts.max()]
        
        if len(who_is_max) > 0:
            
            df = combine_duplicate_targets_modifiers(df, ct_report, report_targets, group, pd.Series(who_is_max.index))

        # check for duplicate targets with the same modifier type, then combine them to one row and continue
        df = combine_matching_targets_modifiers(df, ct_report, group)
    
    return df


def combine_duplicate_targets_modifiers(df, ct_report, report_targets, group, modifier_types):
    
    if group in ['fluid', 'hemorrhage', 'intracranial_pathology']:
        modifiers = ['absent', 'indeterminate', 'suspected', 'present', 'normal', 'abnormal']
    else:
        modifiers = ['present', 'suspected', 'indeterminate', 'absent', 'abnormal', 'normal']
    
    # in order of list of modifiers, go through and drop all that are not that modifier
    for modifier in modifiers:
        
        if modifier in modifier_types.tolist():
            
            drop_index = report_targets.loc[(
                                                (report_targets['target_group'] == group) & 
                                                (report_targets['modifier_type'] != modifier)
                                               )].index
            df.drop(index=drop_index, axis=1, inplace=True)
            
            # if drop occured, then break loop as we are done removing
            break
        
    return df


def combine_matching_targets_modifiers(df, ct_report, group):
    
    # if modifier types are equivalent for the target group, only one will be retained; modifiers concatenated
    concat_modifiers = df.loc[(
                               (df['CT_report_id'] == ct_report) & 
                               (df['target_group'] == group)
                              ), 'modifier'].drop_duplicates(keep='first').str.cat(sep=', ')
    
    # replace modifiers for all items in group
    df.loc[(
            (df['CT_report_id'] == ct_report) & 
            (df['target_group'] == group)
           ), 'modifier'] = concat_modifiers
    
    # the targets will be combined
    concat_targets = df.loc[(
                             (df['CT_report_id'] == ct_report) & 
                             (df['target_group'] == group)
                            ), 'target'].drop_duplicates(keep='first').str.cat(sep=', ')
    
    # replace targets for all items in group
    df.loc[(
            (df['CT_report_id'] == ct_report) & 
            (df['target_group'] == group)
           ), 'target'] = concat_targets
    
    # rows will now be duplicates for target groups with same modifier group
    df.drop_duplicates(subset=['CT_report_id', 'target_group', 'modifier_type'], keep='first', inplace=True)
    
    return df


def modifier_type_physician_match(df, ct_report, report_targets, target_list):
   
    # change modifier types to match those given to physicians
    for item in ['cistern', 'gray_white_differentiation']:
                
        # find where item is not default modified
        modifiers = report_targets.loc[(
                                        (report_targets['modifier'] != 'default') & 
                                        (report_targets['target_group'] == item)
                                       ), 'modifier'].str.cat(sep=', ')
        
        if modifiers != '':
            
            modifier_types = report_targets.loc[report_targets['target_group'] == item, 'modifier_type']
            
            # targets in abnormal list can either be normal or abnormal
            normals = ['normal', 'absent']
            normal_modifier_type = ['normal' for item in list(modifier_types) if item in normals]
            abnormals = ['abnormal', 'present', 'suspected', 'indeterminate']
            abnormal_modifier_type = ['abnormal' for item in list(modifier_types) if item in abnormals]
                
            if len(abnormal_modifier_type) == 0 and len(normal_modifier_type) > 0:
                
                # if "abnormal" not present and "normal" present, then mark item as "normal" in df
                df.loc[(
                        (df['CT_report_id'] == ct_report) & 
                        (df['target_group'] == item)
                       ), 'modifier_type'] = 'normal'
 
                df.loc[(
                        (df['CT_report_id'] == ct_report) & 
                        (df['target_group'] == item)
                       ), 'modifier'] = modifiers + ', modifier_type_physician_match'
                
            elif len(abnormal_modifier_type) > 0:

                # if "abnormal" present, then mark item as "abnormal" in df
                df.loc[(
                        (df['CT_report_id'] == ct_report) & 
                        (df['target_group'] == item)
                       ), 'modifier_type'] = 'abnormal'
    
                df.loc[(
                        (df['CT_report_id'] == ct_report) & 
                        (df['target_group'] == item)
                       ), 'modifier'] = modifiers + ', modifier_type_physician_match'
        
    # change modifier types to match those given to physicians
    for item in [item for item in target_list if item not in ['cistern', 'gray_white_differentiation']]:
        
        # find where item is not default modified
        modifiers = report_targets.loc[(
                                       (report_targets['modifier'] != 'default') & 
                                       (report_targets['target_group'] == item)
                                      ), 'modifier'].str.cat(sep=', ')
        
        if modifiers != '':
            
            modifier_types = report_targets.loc[report_targets['target_group'] == item, 'modifier_type']
            
            if 'abnormal' in list(modifier_types):
                
                # if 'abnormal' in modifier types, change to 'present'
                df.loc[(
                        (df['CT_report_id'] == ct_report) & 
                        (df['target_group'] == item) &
                        (df['modifier_type'] == 'abnormal')
                       ), 'modifier_type'] = 'present'
    
                df.loc[(
                        (df['CT_report_id'] == ct_report) & 
                        (df['target_group'] == item) &
                        (df['modifier_type'] == 'abnormal')
                       ), 'modifier'] = modifiers + ', modifier_type_physician_match'
            
            if 'normal' in list(modifier_types):
                
                # if 'normal' in modifier types, change to 'absent'
                df.loc[(
                        (df['CT_report_id'] == ct_report) & 
                        (df['target_group'] == item) &
                        (df['modifier_type'] == 'normal')
                       ), 'modifier_type'] = 'absent'
    
                df.loc[(
                        (df['CT_report_id'] == ct_report) & 
                        (df['target_group'] == item) &
                        (df['modifier_type'] == 'abnormal')
                       ), 'modifier'] = modifiers + ', modifier_type_physician_match'
        
    return df


def is_specific_hemorrhage(df, ct_report, report_targets):
    
    # if a specific hemorrhage present or suspected, then hemorrhage NOS changed to absent
    hemorrhages = ['epidural_hemorrhage', 'subarachnoid_hemorrhage', 'subdural_hemorrhage']
    present = ['present', 'suspected']
    specific_hemorrhage = len(report_targets.loc[(
                                                  (report_targets['target_group'].isin(hemorrhages)) & 
                                                  (report_targets['modifier_type'].isin(present))
                                                 )])
    
    modifiers = report_targets.loc[(
                                    (report_targets['target_group'] == 'hemorrhage')
                                   ), 'modifier'].str.cat(sep=', ')
        
    if ((specific_hemorrhage > 0) and (len(report_targets['target_group'].isin(['hemorrhage'])) > 0)):
        
        df.loc[(
                (df['CT_report_id'] == ct_report) & 
                (df['target_group'] == 'hemorrhage')
               ), 'modifier_type'] = 'absent'
    
        df.loc[(
                (df['CT_report_id'] == ct_report) & 
                (df['target_group'] == 'hemorrhage')
               ), 'modifier'] = modifiers + ', is_specific_hemorrhage'
                              
    return df



def is_extraaxial_fluid_collection(df, ct_report, report_targets):
    
    hemorrhage = ['epidural_hemorrhage', 'subarachnoid_hemorrhage', 'subdural_hemorrhage']
    specific_hemorrhage = report_targets.loc[(report_targets['target_group'].isin(hemorrhage))]

    modifiers = report_targets.loc[(
                                    (report_targets['target_group'] == 'fluid')
                                   ), 'modifier'].str.cat(sep=', ')
                
    if 'present' in specific_hemorrhage['modifier_type'].tolist():
        
        # if any hemorrhage "present", then fluid is "present"
        df.loc[(
                (df['CT_report_id'] == ct_report) & 
                (df['target_group'] == 'fluid')
               ), 'modifier_type'] = 'present'
    
        df.loc[(
                (df['CT_report_id'] == ct_report) & 
                (df['target_group'] == 'fluid')
               ), 'modifier'] = modifiers + ', is_extraaxial_fluid_collection'
        
    elif (
            ('suspected' in specific_hemorrhage['modifier_type'].tolist()) and 
            ('present' not in specific_hemorrhage['modifier_type'].tolist())
         ):
        
        # if any hemorrhage "suspected" and not "present", then fluid "suspected", if fluid "default"
        is_default = report_targets.loc[(
                                         (report_targets['modifier'] == 'default') & 
                                         (report_targets['target_group'] == 'fluid')
                                        )]
        
        if len(is_default) > 0:
            
            df.loc[(
                    (df['CT_report_id'] == ct_report) & 
                    (df['target_group'] == 'fluid')
                   ), 'modifier_type'] = 'suspected'
    
            df.loc[(
                    (df['CT_report_id'] == ct_report) & 
                    (df['target_group'] == 'fluid')
                   ), 'modifier'] = modifiers + ', is_extraaxial_fluid_collection'
    
    # else fluid is left as original target/modifier pair from algorithm

    return df


def is_intracranial_pathology(df, ct_report, report_targets):
    
    pathology = ['gray_white_differentiation', 'cistern', 'hydrocephalus',
                 'pneumocephalus', 'midline_shift', 'mass_effect', 
                 'diffuse_axonal', 'anoxic', 'herniation', 'aneurysm', 
                 'contusion', 'fluid', 'swelling', 'ischemia', 
                 'hemorrhage', 'intraventricular_hemorrhage', 
                 'intraparenchymal_hemorrage']
    
    present = ['present', 'suspected', 'abnormal']
    
    modifiers = report_targets.loc[(
                                    (report_targets['target_group'] == 'intracranial_pathology')
                                   ), 'modifier'].str.cat(sep=', ')
                
    specific_pathology = report_targets.loc[(
                                             (report_targets['target_group'].isin(pathology)) & 
                                             (report_targets['modifier_type'].isin(present))
                                            )]
    
    path_modifier = report_targets.loc[(report_targets['target_group'] == 'intracranial_pathology'), 'modifier'].tolist()
       
    if (len(specific_pathology) > 0) and ('no acute' not in path_modifier):
        
        df.loc[(
                (df['CT_report_id'] == ct_report) & 
                (df['target_group'] == 'intracranial_pathology')
               ), 'modifier_type'] = 'present'
        
        df.loc[(
                (df['CT_report_id'] == ct_report) & 
                (df['target_group'] == 'intracranial_pathology')
               ), 'modifier'] = modifiers + ', is_intracranial_pathology'

    return df


# eof
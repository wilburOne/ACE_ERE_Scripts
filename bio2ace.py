import argparse
import os
import csv
import xml.etree.ElementTree as ET


# word, offset, nertag, relation, trigger, argument
def write_ann(bio_file, ann_file, ace_file):
    csv_file = open(ace_file, 'w')
    fields = ['token', 'offset', 'ner_offset', 'ner_type', 'ner_nam_nom', 'ner_cluster',
              'timex2_offset', 'timex2_cluster',
              'value_offset', 'value_type', 'value_cluster',
              'relations_belong_to',
              'trigger_offset', 'trigger_type', 'trigger_cluster', 'trigger_arguments']
    writer = csv.DictWriter(csv_file, fieldnames=fields)

    entity_mentions_mentionid2dict, timex2_mentions_mentionid2dict, value_mentions_mentionid2dict, \
    relation_mentions_id2dict, event_mentions_id2dict = parse_ann(ann_file)

    with open(bio_file, 'r') as f:
        for line in f:
            line = line.strip()
            if len(line) > 0:
                parts = line.strip().split(' ')
                token = parts[0]
                offset = parts[1]

                token_dict = {'token': token, 'offset': offset}

                d_id, o = offset.split(':')
                start, end = o.split('-')
                start = int(start)
                end = int(end)

                entity_mention_ids = search_offset_id(start, end, entity_mentions_mentionid2dict, 'offset')
                timex2_mention_ids = search_offset_id(start, end, timex2_mentions_mentionid2dict, 'offset')
                value_mention_ids = search_offset_id(start, end, value_mentions_mentionid2dict, 'offset')
                relation_mention_ids = search_relation_id(start, end, relation_mentions_id2dict)
                event_mention_ids = search_offset_id(start, end, event_mentions_id2dict, 'anchor_offset')

                if len(entity_mention_ids) == 0:
                    token_dict['ner_offset'] = 'O'
                    token_dict['ner_type'] = 'O'
                    token_dict['ner_nam_nom'] = 'O'
                    token_dict['ner_cluster'] = 'O'
                else:
                    ner_offsets = []
                    ner_types = []
                    ner_nam_noms = []
                    ner_clusters = []

                    for id in entity_mention_ids:
                        ner_offsets.append(entity_mentions_mentionid2dict[id]['offset'])
                        ner_types.append(entity_mentions_mentionid2dict[id]['type'] + ':' + \
                                             entity_mentions_mentionid2dict[id]['subtype'])
                        ner_nam_noms.append(entity_mentions_mentionid2dict[id]['mention_type'])
                        ner_clusters.append(entity_mentions_mentionid2dict[id]['entity_id'])
                    token_dict['ner_offset'] = '#@#'.join(ner_offsets)
                    token_dict['ner_type'] = '#@#'.join(ner_types)
                    token_dict['ner_nam_nom'] = '#@#'.join(ner_nam_noms)
                    token_dict['ner_cluster'] = '#@#'.join(ner_clusters)

                if len(timex2_mention_ids) == 0:
                    token_dict['timex2_offset'] = 'O'
                    token_dict['timex2_cluster'] = 'O'
                else:
                    timex2_offsets = []
                    timex2_clusters = []
                    for id in timex2_mention_ids:
                        timex2_offsets.append(timex2_mentions_mentionid2dict[id]['offset'])
                        timex2_clusters.append(timex2_mentions_mentionid2dict[id]['timex2_id'])
                    token_dict['timex2_offset'] = '#@#'.join(timex2_offsets)
                    token_dict['timex2_cluster'] = '#@#'.join(timex2_clusters)

                if len(value_mention_ids) == 0:
                    token_dict['value_offset'] = 'O'
                    token_dict['value_type'] = 'O'
                    token_dict['value_cluster'] = 'O'
                else:
                    value_offsets = []
                    value_types = []
                    value_clusters = []

                    for id in value_mention_ids:
                        value_offsets.append(value_mentions_mentionid2dict[id]['offset'])
                        value_types.append(value_mentions_mentionid2dict[id]['type'] + ':' +
                                           value_mentions_mentionid2dict[id]['subtype'])
                        value_clusters.append(value_mentions_mentionid2dict[id]['value_id'])
                    token_dict['value_offset'] = '#@#'.join(value_offsets)
                    token_dict['value_type'] = '#@#'.join(value_types)
                    token_dict['value_cluster'] = '#@#'.join(value_clusters)

                if len(relation_mention_ids) == 0:
                    token_dict['relations_belong_to'] = 'O'
                else:
                    relation_mentions = []
                    for id in relation_mention_ids:
                        relation_mention_dict = relation_mentions_id2dict[id]
                        relation_id = relation_mention_dict['relation_id']
                        relation_type = relation_mention_dict['relation_type'] + ':' + \
                                        relation_mention_dict['relation_subtype']
                        arg0 = relation_mention_dict['mention_argument0_offset']
                        arg1 = relation_mention_dict['mention_argument1_offset']

                        mention = relation_id + ':' + arg0 + ':' + relation_type + ':' + arg1
                        relation_mentions.append(mention)
                    mention_str = ' '.join(relation_mentions)
                    token_dict['relations_belong_to'] = mention_str

                if len(event_mention_ids) == 0:
                    token_dict['trigger_offset'] = 'O'
                    token_dict['trigger_type'] = 'O'
                    token_dict['trigger_cluster'] = 'O'
                    token_dict['trigger_arguments'] = 'O'
                else:
                    trigger_offsets = []
                    trigger_types = []
                    trigger_clusters = []
                    trigger_arguments_set = []
                    for id in event_mention_ids:
                        trigger_offsets.append(event_mentions_id2dict[id]['anchor_offset'])
                        trigger_types.append(event_mentions_id2dict[id]['type'] + ':' +
                                             event_mentions_id2dict[id]['subtype'])
                        trigger_clusters.append(event_mentions_id2dict[id]['event_id'])
                        all_event_mention_arguments = event_mentions_id2dict[id]['argument']
                        arguments = []
                        for arg in all_event_mention_arguments:
                            arg_str = arg['mention_argument_refid'] + ':' + arg['mention_argument_role'] + ':' + \
                                      arg['mention_argument_offset']
                            arguments.append(arg_str)
                        arguments_str = ' '.join(arguments)
                        trigger_arguments_set.append(arguments_str)

                    token_dict['trigger_offset'] = '#@#'.join(trigger_offsets)
                    token_dict['trigger_type'] = '#@#'.join(trigger_types)
                    token_dict['trigger_cluster'] = '#@#'.join(trigger_clusters)
                    token_dict['trigger_arguments'] = '#@#'.join(trigger_arguments_set)

                writer.writerow(token_dict)
            else:
                token_dict = {'token':'----sentence_delimiter----'}
                writer.writerow(token_dict)

    csv_file.close()


# applicable to entity, timex2, event mentions
def search_offset_id(token_start, token_end, entity_mentions_mentionid2dict, offset_key):
    searched_ids = []
    for id in entity_mentions_mentionid2dict:
        can_dict = entity_mentions_mentionid2dict[id]
        mention_offset_parts = can_dict[offset_key].split(':')
        can_start = int(mention_offset_parts[0])
        can_end = int(mention_offset_parts[1])
        if (can_start <= token_start <= can_end) or (can_start <= token_end <= can_end):
            searched_ids.append(id)
    return searched_ids


def search_relation_id(token_start, token_end, relation_mentions_id2dict):
    searched_ids = []
    for id in relation_mentions_id2dict:
        can_dict = relation_mentions_id2dict[id]
        argument0_offset_parts = can_dict['mention_argument0_offset'].split(':')
        argument1_offset_parts = can_dict['mention_argument1_offset'].split(':')
        arg0_start = int(argument0_offset_parts[0])
        arg0_end = int(argument0_offset_parts[1])
        arg1_start = int(argument1_offset_parts[0])
        arg1_end = int(argument1_offset_parts[1])
        if (arg0_start <= token_start <= arg0_end) or (arg0_start <= token_end <= arg0_end) or \
                (arg1_start <= token_start <= arg1_end) or (arg1_start <= token_end <= arg1_end):
            searched_ids.append(id)
    return searched_ids


def parse_ann(ann_file):
    tree = ET.parse(ann_file)
    root = tree.getroot()
    doc_elem = root[0] # entity, timex2, relation, event

    all_entity_elems = doc_elem.findall('entity')
    all_timex2_elems = doc_elem.findall('timex2')
    all_value_elems = doc_elem.findall('value')
    all_relaton_elems = doc_elem.findall('relation')
    all_event_elems = doc_elem.findall('event')

    # parse all entities and mentions
    entity_mentions_offset2dict = {}
    entity_mentions_mentionid2dict = {}
    for entity_elem in all_entity_elems:
        entity_attribs = entity_elem.attrib
        entity_id = entity_attribs["ID"]      # CNN_CF_20030303.1900.00-E1
        entity_type = entity_attribs["TYPE"]  # PER
        entity_subtype = entity_attribs["SUBTYPE"] # Individual
        entity_class = entity_attribs["CLASS"] # SPC

        all_entity_mention_elems = entity_elem.findall("entity_mention")
        for entity_mention_elem in all_entity_mention_elems:
            entity_mention_attribs = entity_mention_elem.attrib
            entity_mention_id = entity_mention_attribs["ID"] # CNN_CF_20030303.1900.00-E1-2
            entity_mention_type = entity_mention_attribs["TYPE"] # NOM
            entity_mention_ldctype = entity_mention_attribs["LDCTYPE"] # NOMPRE

            entity_mention_extent_elem = entity_mention_elem.findall("extent")[0].findall("charseq")[0]
            entity_mention_head_elem = entity_mention_elem.findall("head")[0].findall("charseq")[0]

            entity_mention_head_start = entity_mention_head_elem.attrib["START"] # 490
            entity_mention_head_end = entity_mention_head_elem.attrib["END"] # 498
            entity_mention_head_text = entity_mention_head_elem.text # Secretary

            mention_offset = entity_mention_head_start + ":" + entity_mention_head_end
            mention_dict = {"type": entity_type, "subtype": entity_subtype, "entity_id": entity_id,
                            "entity_class": entity_class, "mention_id": entity_mention_id,
                            "mention_type": entity_mention_type, "mention_ldctype": entity_mention_ldctype,
                            "text": entity_mention_head_text, "offset": mention_offset}
            entity_mentions_offset2dict[mention_offset] = mention_dict
            entity_mentions_mentionid2dict[entity_mention_id] = mention_dict

    # parse all timex2
    timex2_mentions_offset2dict = {}
    timex2_mentions_mentionid2dict = {}
    for timex2_elem in all_timex2_elems:
        timex2_id = timex2_elem.attrib["ID"]
        all_timex2_mention_elems = timex2_elem.findall("timex2_mention")
        for timex2_mention_elem in all_timex2_mention_elems:
            timex2_mention_id = timex2_mention_elem.attrib["ID"]
            timex2_mention_elem_extend = timex2_mention_elem.findall("extent")[0].findall("charseq")[0]
            timex2_mention_start = timex2_mention_elem_extend.attrib["START"]
            timex2_mention_end = timex2_mention_elem_extend.attrib["END"]
            timex2_mention_text = timex2_mention_elem_extend.text

            mention_offset = timex2_mention_start + ":" + timex2_mention_end
            mention_dict = {"timex2_id": timex2_id, "mention_id": timex2_mention_id, "text": timex2_mention_text,
                            "offset": mention_offset}
            timex2_mentions_offset2dict[mention_offset] = mention_dict
            timex2_mentions_mentionid2dict[timex2_mention_id] = mention_dict

    # parse all values
    value_mentions_offset2dict = {}
    value_mentions_mentionid2dict = {}
    for value_elem in all_value_elems:
        value_id = value_elem.attrib["ID"]
        value_type = value_elem.attrib['TYPE']
        value_subtype = "O"
        if "SUBTYPE" in value_elem.attrib:
            value_subtype = value_elem.attrib['SUBTYPE']

        all_value_mention_elems = value_elem.findall("value_mention")
        for value_mention_elem in all_value_mention_elems:
            value_mention_id = value_mention_elem.attrib["ID"]
            value_mention_elem_extend = value_mention_elem.findall("extent")[0].findall("charseq")[0]
            value_mention_start = value_mention_elem_extend.attrib["START"]
            value_mention_end = value_mention_elem_extend.attrib["END"]
            value_mention_text = value_mention_elem_extend.text

            mention_offset = value_mention_start + ":" + value_mention_end
            mention_dict = {"value_id": value_id, "type":value_type, 'subtype':value_subtype,
                            "mention_id": value_mention_id, "text": value_mention_text,
                            "offset": mention_offset}
            value_mentions_offset2dict[mention_offset] = mention_dict
            value_mentions_mentionid2dict[value_mention_id] = mention_dict

    # parse all relations
    relation_mentions_id2dict = {}
    relation_mentions_men2men2dict = {}
    for relation_elem in all_relaton_elems:
        relation_elem_attribs = relation_elem.attrib
        relation_id = relation_elem_attribs["ID"]             # CNN_CF_20030303.1900.00-R2
        relation_type = relation_elem_attribs["TYPE"]         # PART-WHOLE
        relation_subtype = "O"
        if "SUBTYPE" in relation_elem_attribs:
            relation_subtype = relation_elem_attribs["SUBTYPE"]   # Geographical
        relation_tense = "O"
        if "TENSE" in relation_elem_attribs:
            relation_tense = relation_elem_attribs["TENSE"]       # Unspecified
        relation_modality = "O"
        if "MODALITY" in relation_elem_attribs:
            relation_modality = relation_elem_attribs["MODALITY"]       # Unspecified
        relation_argument_elems = relation_elem.findall("relation_argument")
        relation_argument0 = relation_argument_elems[0]
        relation_argument1 = relation_argument_elems[1]
        relation_argument0_refid = relation_argument0.attrib["REFID"]
        relation_argument0_role = relation_argument0.attrib["ROLE"]
        relation_argument1_refid = relation_argument1.attrib["REFID"]
        relation_argument1_role = relation_argument1.attrib["ROLE"]

        all_relation_mention_elems = relation_elem.findall("relation_mention")
        for relation_mention_elem in all_relation_mention_elems:
            relation_mention_id = relation_mention_elem.attrib["ID"]
            relation_mention_lexical_condition = relation_mention_elem.attrib["LEXICALCONDITION"]
            relation_mention_extent = relation_mention_elem.findall("extent")[0].findall("charseq")[0]
            relation_mention_extent_start = relation_mention_extent.attrib["START"]
            relation_mention_extent_end = relation_mention_extent.attrib["END"]
            relation_mention_extent_text = relation_mention_extent.text
            relation_mention_extend_offset = relation_mention_extent_start + ":" + relation_mention_extent_end

            relation_mention_argument_elems = relation_mention_elem.findall("relation_mention_argument")
            relation_mention_argument0 = relation_mention_argument_elems[0]
            relation_mention_argument1 = relation_mention_argument_elems[1]
            relation_mention_argument0_refid = relation_mention_argument0.attrib["REFID"]
            relation_mention_argument0_role = relation_mention_argument0.attrib["ROLE"]
            relation_mention_argument1_refid = relation_mention_argument1.attrib["REFID"]
            relation_mention_argument1_role = relation_mention_argument1.attrib["ROLE"]

            # replace extend to the corresponding head
            # arg0
            if relation_mention_argument0_refid in entity_mentions_mentionid2dict:
                relation_mention_argument0_extend_offset = \
                    entity_mentions_mentionid2dict[relation_mention_argument0_refid]["offset"]
                relation_mention_argument0_extend_text = \
                    entity_mentions_mentionid2dict[relation_mention_argument0_refid]["text"]
            elif relation_mention_argument0_refid in timex2_mentions_mentionid2dict:
                relation_mention_argument0_extend_offset = \
                    timex2_mentions_mentionid2dict[relation_mention_argument0_refid]["offset"]
                relation_mention_argument0_extend_text = \
                    timex2_mentions_mentionid2dict[relation_mention_argument0_refid]["text"]
            elif relation_mention_argument0_refid in value_mentions_mentionid2dict:
                relation_mention_argument0_extend_offset = \
                    value_mentions_mentionid2dict[relation_mention_argument0_refid]["offset"]
                relation_mention_argument0_extend_text = \
                    value_mentions_mentionid2dict[relation_mention_argument0_refid]["text"]

            # time mention
            if relation_mention_argument1_refid in entity_mentions_mentionid2dict:
                relation_mention_argument1_extend_offset = \
                    entity_mentions_mentionid2dict[relation_mention_argument1_refid]["offset"]
                relation_mention_argument1_extend_text = \
                    entity_mentions_mentionid2dict[relation_mention_argument1_refid]["text"]
            elif relation_mention_argument1_refid in timex2_mentions_mentionid2dict:
                relation_mention_argument1_extend_offset = \
                    timex2_mentions_mentionid2dict[relation_mention_argument1_refid]["offset"]
                relation_mention_argument1_extend_text = \
                    timex2_mentions_mentionid2dict[relation_mention_argument1_refid]["text"]
            elif relation_mention_argument1_refid in value_mentions_mentionid2dict:
                relation_mention_argument1_extend_offset = \
                    value_mentions_mentionid2dict[relation_mention_argument1_refid]["offset"]
                relation_mention_argument1_extend_text = \
                    value_mentions_mentionid2dict[relation_mention_argument1_refid]["text"]

            mention_dict = {"relation_id": relation_id, "relation_type": relation_type,
                            "relation_subtype": relation_subtype, "relation_tense": relation_tense,
                            "relation_modality": relation_modality, "relation_argument0_refid": relation_argument0_refid,
                            "relation_argument0_role": relation_argument0_role,
                            "relation_argument1_refid": relation_argument1_refid,
                            "relation_argument1_role": relation_argument1_role, "mention_id": relation_mention_id,
                            "mention_offset": relation_mention_extend_offset,
                            "mention_text": relation_mention_extent_text,
                            "mention_argument0_refid": relation_mention_argument0_refid,
                            "mention_argument0_role": relation_mention_argument0_role,
                            "mention_argument1_refid": relation_mention_argument1_refid,
                            "mention_argument1_role": relation_mention_argument1_role,
                            "mention_argument0_offset": relation_mention_argument0_extend_offset,
                            "mention_argument0_text": relation_mention_argument0_extend_text,
                            "mention_argument1_offset": relation_mention_argument1_extend_offset,
                            "mention_argument1_text": relation_mention_argument1_extend_text
                            }
            relation_mentions_id2dict[relation_mention_id] = mention_dict
            if relation_mention_argument0_refid in relation_mentions_men2men2dict:
                relation_mentions_men2dict = relation_mentions_men2men2dict[relation_mention_argument0_refid]
                relation_mentions_men2dict[relation_mention_argument1_refid] = mention_dict
                relation_mentions_men2men2dict[relation_mention_argument0_refid] = relation_mentions_men2dict
            else:
                relation_mentions_men2dict = {relation_mention_argument1_refid: mention_dict}
                relation_mentions_men2men2dict[relation_mention_argument0_refid] = relation_mentions_men2dict

    # parse all events
    event_mentions_id2dict = {}
    for event_elem in all_event_elems:
        event_id = event_elem.attrib["ID"]
        event_type = event_elem.attrib["TYPE"]
        event_subtype = event_elem.attrib["SUBTYPE"]
        event_modality = event_elem.attrib["MODALITY"]
        event_polarity = event_elem.attrib["POLARITY"]
        event_genericity = event_elem.attrib["GENERICITY"]
        event_tense = event_elem.attrib["TENSE"]

        all_event_argument_elems = event_elem.findall("event_argument")
        event_argument_list = []
        for event_argument_elem in all_event_argument_elems:
            event_argument_refid = event_argument_elem.attrib["REFID"]
            event_argument_role = event_argument_elem.attrib["ROLE"]
            event_argument_dict = {"argument_refid": event_argument_refid, "argument_role": event_argument_role}
            event_argument_list.append(event_argument_dict)

        all_event_mention_elems = event_elem.findall("event_mention")
        for event_mention_elem in all_event_mention_elems:
            event_mention_id = event_mention_elem.attrib["ID"]
            event_mention_extent = event_mention_elem.findall("extent")[0].findall("charseq")[0]
            event_mention_extent_start = event_mention_extent.attrib["START"]
            event_mention_extent_end = event_mention_extent.attrib["END"]
            event_mention_extent_text = event_mention_extent.text

            event_mention_anchor = event_mention_elem.findall("anchor")[0].findall("charseq")[0]  # trigger
            event_mention_anchor_start = event_mention_anchor.attrib["START"]
            event_mention_anchor_end = event_mention_anchor.attrib["END"]
            event_mention_anchor_offset = event_mention_anchor_start + ":" + event_mention_anchor_end
            event_mention_anchor_text = event_mention_anchor.text

            all_event_mention_argument_elems = event_mention_elem.findall("event_mention_argument")
            all_event_mention_arguments = []
            for event_mention_argument_elem in all_event_mention_argument_elems:
                event_mention_argument_refid = event_mention_argument_elem.attrib["REFID"]
                event_mention_argument_role = event_mention_argument_elem.attrib["ROLE"]

                # replace extend to head
                # entity mentions
                if event_mention_argument_refid in entity_mentions_mentionid2dict:
                    event_mention_argument_offset = \
                        entity_mentions_mentionid2dict[event_mention_argument_refid]["offset"]
                    event_mention_argument_text = entity_mentions_mentionid2dict[event_mention_argument_refid]["text"]
                elif event_mention_argument_refid in timex2_mentions_mentionid2dict:
                    event_mention_argument_offset = \
                        timex2_mentions_mentionid2dict[event_mention_argument_refid]["offset"]
                    event_mention_argument_text = timex2_mentions_mentionid2dict[event_mention_argument_refid]["text"]
                elif event_mention_argument_refid in value_mentions_mentionid2dict:
                    event_mention_argument_offset = \
                        value_mentions_mentionid2dict[event_mention_argument_refid]["offset"]
                    event_mention_argument_text = value_mentions_mentionid2dict[event_mention_argument_refid]["text"]

                event_mention_argument_dict = {"mention_argument_refid": event_mention_argument_refid,
                                               "mention_argument_role": event_mention_argument_role,
                                               "mention_argument_offset": event_mention_argument_offset,
                                               "mention_argument_text": event_mention_argument_text}
                all_event_mention_arguments.append(event_mention_argument_dict)

            mention_dict = {"event_id": event_id, "type": event_type, "subtype": event_subtype,
                            "modality": event_modality, "polarity": event_polarity,
                            "genericity": event_genericity, "tense": event_tense,
                            "mention_id": event_mention_id, "anchor_offset": event_mention_anchor_offset,
                            "anchor_text": event_mention_anchor_text, "argument": all_event_mention_arguments}

            event_mentions_id2dict[event_mention_id] = mention_dict

    return entity_mentions_mentionid2dict, timex2_mentions_mentionid2dict, value_mentions_mentionid2dict, \
           relation_mentions_id2dict, event_mentions_id2dict


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--bio', type=str,
                        help='bio input path')
    parser.add_argument('--ann', type=str,
                        help='ace annotation input path')
    parser.add_argument('--ace', type=str,
                        help='output ace annotation path')
    parser.add_argument('--filelist', type=str,
                        help='filelist path')

    args = parser.parse_args()

    bio_path = args.bio
    ann_path = args.ann
    ace_path = args.ace

    if not os.path.exists(ace_path):
        os.makedirs(ace_path)

    file_names = []
    if os.path.isdir(bio_path):
        file_names = [item[:-4]
                  for item in os.listdir(bio_path)
                  if item.endswith(".bio")]
    else:
        file_names = [bio_path]

    for f in file_names:
        print(f)
        bio_file= os.path.join(bio_path, f+".bio")
        ann_file = os.path.join(ann_path, f+".apf.xml")
        ace_file = os.path.join(ace_path, f+".csv")

        if os.path.exists(bio_file) and os.path.exists(ann_file):
            write_ann(bio_file, ann_file, ace_file)


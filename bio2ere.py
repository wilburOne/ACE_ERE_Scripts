import argparse
import os
import csv
import xml.etree.ElementTree as ET


# word, offset, nertag, relation, trigger, argument
def write_ann(bio_file, ann_file, ace_file):
    csv_file = open(ace_file, 'w')
    fields = ['token', 'offset', 'ner_offset', 'ner_type', 'ner_nam_nom', 'ner_cluster',
              'filler_offset', 'filler_type',
              'relations_belong_to',
              'trigger_offset', 'trigger_type', 'trigger_cluster', 'trigger_arguments']
    writer = csv.DictWriter(csv_file, fieldnames=fields)

    entity_mentions_mentionid2dict, filler_mentions_mentionid2dict, relation_mentions_id2dict, \
    event_mentions_id2dict = parse_ann(ann_file)

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
                filler_mention_ids = search_offset_id(start, end, filler_mentions_mentionid2dict, 'offset')
                relation_mention_ids = search_relation_id(start, end, relation_mentions_id2dict)
                event_mention_ids = search_offset_id(start, end, event_mentions_id2dict, 'trigger_offset')

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
                        if str(start)+":"+str(end) == entity_mentions_mentionid2dict[id]['offset']:
                            assert token == entity_mentions_mentionid2dict[id]['text']
                        ner_types.append(entity_mentions_mentionid2dict[id]['type'] + ':' + \
                                             entity_mentions_mentionid2dict[id]['subtype'])
                        ner_nam_noms.append(entity_mentions_mentionid2dict[id]['mention_type'])
                        ner_clusters.append(entity_mentions_mentionid2dict[id]['entity_id'])
                    token_dict['ner_offset'] = '#@#'.join(ner_offsets)
                    token_dict['ner_type'] = '#@#'.join(ner_types)
                    token_dict['ner_nam_nom'] = '#@#'.join(ner_nam_noms)
                    token_dict['ner_cluster'] = '#@#'.join(ner_clusters)

                if len(filler_mention_ids) == 0:
                    token_dict['filler_offset'] = 'O'
                    token_dict['filler_type'] = 'O'
                else:
                    filler_offsets = []
                    filler_types = []
                    for id in filler_mention_ids:
                        filler_offsets.append(filler_mentions_mentionid2dict[id]['offset'])
                        filler_types.append(filler_mentions_mentionid2dict[id]['type'])
                    token_dict['filler_offset'] = '#@#'.join(filler_offsets)
                    token_dict['filler_type'] = '#@#'.join(filler_types)

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
                        trigger_offsets.append(event_mentions_id2dict[id]['trigger_offset'])
                        if str(start)+":"+str(end) == event_mentions_id2dict[id]['trigger_offset']:
                            assert token == event_mentions_id2dict[id]['trigger_text']
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
    doc_elem = root[0] # entities, fillers, relations, hoppers

    all_entity_elems = []
    all_filler_elems = []
    all_relation_elems = []
    all_hopper_elems = []
    if len(doc_elem.findall('entities')) > 0:
        entities_elem = doc_elem.findall('entities')[0]
        all_entity_elems = entities_elem.findall('entity')
    if len(doc_elem.findall('fillers')) > 0:
        fillers_elem = doc_elem.findall('fillers')[0]
        all_filler_elems = fillers_elem.findall('filler')
    if len(doc_elem.findall('relations')) > 0:
        relations_elem = doc_elem.findall('relations')[0]
        all_relation_elems = relations_elem.findall('relation')
    if len(doc_elem.findall('hoppers')) > 0:
        hoppers_elem = doc_elem.findall('hoppers')[0]
        all_hopper_elems = hoppers_elem.findall('hopper')

    # parse all entities and mentions
    entity_mentions_offset2dict = {}
    entity_mentions_mentionid2dict = {}
    for entity_elem in all_entity_elems:
        entity_attribs = entity_elem.attrib
        entity_id = entity_attribs["id"]      # CNN_CF_20030303.1900.00-E1
        entity_type = entity_attribs["type"]  # PER
        entity_specificity = entity_attribs["specificity"] #

        all_entity_mention_elems = entity_elem.findall("entity_mention")
        for entity_mention_elem in all_entity_mention_elems:
            entity_mention_attribs = entity_mention_elem.attrib
            entity_mention_id = entity_mention_attribs["id"] # CNN_CF_20030303.1900.00-E1-2
            entity_mention_noun_type = entity_mention_attribs["noun_type"] # NOM

            entity_mention_start = entity_mention_attribs["offset"]
            entity_mention_end = int(entity_mention_start) + int(entity_mention_attribs["length"]) - 1
            entity_mention_text = entity_mention_elem.findall('mention_text')[0].text
            mention_offset = entity_mention_start + ":" + str(entity_mention_end)

            nom_head_elems = entity_mention_elem.findall("nom_head")
            if len(nom_head_elems) > 0:
                if len(nom_head_elems) > 1:
                    print("Error: multiple nom heads~")
                nom_head_elem = nom_head_elems[0]
                entity_mention_head_start = nom_head_elem.attrib["offset"]
                entity_mention_head_end = int(entity_mention_head_start) + int(nom_head_elem.attrib["length"]) - 1
                mention_offset = entity_mention_head_start + ":" + str(entity_mention_head_end)
                entity_mention_text = nom_head_elem.text

            mention_dict = {"type": entity_type, "specificity": entity_specificity, "entity_id": entity_id,
                            "mention_id": entity_mention_id, "mention_type": entity_mention_noun_type,
                            "text": entity_mention_text, "offset": mention_offset}
            entity_mentions_offset2dict[mention_offset] = mention_dict
            entity_mentions_mentionid2dict[entity_mention_id] = mention_dict

    # parse all filler
    filler_mentions_offset2dict = {}
    filler_mentions_mentionid2dict = {}
    for filler_elem in all_filler_elems:
        filler_id = filler_elem.attrib["id"]
        filler_start = filler_elem.attrib["offset"]
        filler_end = int(filler_start) + int(filler_elem.attrib["length"]) - 1
        filler_type = filler_elem.attrib["type"]
        filler_text = filler_elem.text
        mention_offset = filler_start + ":" + str(filler_end)
        mention_dict = {"filler_id": filler_id, "type": filler_type, "text": filler_text,
                        "offset": mention_offset}
        filler_mentions_offset2dict[mention_offset] = mention_dict
        filler_mentions_mentionid2dict[filler_id] = mention_dict

    # parse all relations
    relation_mentions_id2dict = {}
    relation_mentions_men2men2dict = {}
    for relation_elem in all_relation_elems:
        relation_elem_attribs = relation_elem.attrib
        relation_id = relation_elem_attribs["id"]             # CNN_CF_20030303.1900.00-R2
        relation_type = relation_elem_attribs["type"]         # PART-WHOLE
        relation_subtype = relation_elem_attribs["subtype"]  # PART-WHOLE

        all_relation_mention_elems = relation_elem.findall("relation_mention")
        for relation_mention_elem in all_relation_mention_elems:
            relation_mention_id = relation_mention_elem.attrib["id"]
            relation_mention_realis = relation_mention_elem.attrib["realis"]

            relation_mention_argument0_elem = relation_mention_elem.findall("rel_arg1")[0]
            relation_mention_argument1_elem = relation_mention_elem.findall("rel_arg2")[0]
            if "entity_id" in relation_mention_argument0_elem.attrib:
                relation_mention_argument0_refid = relation_mention_argument0_elem.attrib["entity_mention_id"]
                relation_mention_argument0_role = relation_mention_argument0_elem.attrib["role"]
                relation_mention_argument0_extend_offset = \
                    entity_mentions_mentionid2dict[relation_mention_argument0_refid]["offset"]
                relation_mention_argument0_extend_text = \
                    entity_mentions_mentionid2dict[relation_mention_argument0_refid]["text"]
            elif "filler_id" in relation_mention_argument0_elem.attrib:
                relation_mention_argument0_refid = relation_mention_argument0_elem.attrib["filler_id"]
                relation_mention_argument0_role = relation_mention_argument0_elem.attrib["role"]
                relation_mention_argument0_extend_offset = \
                    filler_mentions_mentionid2dict[relation_mention_argument0_refid]["offset"]
                relation_mention_argument0_extend_text = \
                    filler_mentions_mentionid2dict[relation_mention_argument0_refid]["text"]
            if "entity_id" in relation_mention_argument1_elem.attrib:
                relation_mention_argument1_refid = relation_mention_argument1_elem.attrib["entity_mention_id"]
                relation_mention_argument1_role = relation_mention_argument1_elem.attrib["role"]
                relation_mention_argument1_extend_offset = \
                    entity_mentions_mentionid2dict[relation_mention_argument1_refid]["offset"]
                relation_mention_argument1_extend_text = \
                    entity_mentions_mentionid2dict[relation_mention_argument1_refid]["text"]
            elif "filler_id" in relation_mention_argument1_elem.attrib:
                relation_mention_argument1_refid = relation_mention_argument1_elem.attrib["filler_id"]
                relation_mention_argument1_role = relation_mention_argument1_elem.attrib["role"]
                relation_mention_argument1_extend_offset = \
                    filler_mentions_mentionid2dict[relation_mention_argument1_refid]["offset"]
                relation_mention_argument1_extend_text = \
                    filler_mentions_mentionid2dict[relation_mention_argument1_refid]["text"]

            relation_mention_trigger_elems = relation_mention_elem.findall("trigger")
            relation_mention_trigger_offset = "O"
            relation_mention_trigger_text = "O"
            if len(relation_mention_trigger_elems) > 0:
                relation_mention_trigger_start = relation_mention_trigger_elems[0].attrib["offset"]
                relation_mention_trigger_end = int(relation_mention_trigger_start) + \
                                               int(relation_mention_trigger_elems[0].attrib["length"]) - 1
                relation_mention_trigger_offset = relation_mention_trigger_start + ":" + \
                                                  str(relation_mention_trigger_end)
                relation_mention_trigger_text = relation_mention_trigger_elems[0].text

            mention_dict = {"relation_id": relation_id, "relation_type": relation_type,
                            "relation_subtype": relation_subtype,
                            "mention_id": relation_mention_id, "mention_realis": relation_mention_realis,
                            "mention_argument0_refid": relation_mention_argument0_refid,
                            "mention_argument0_role": relation_mention_argument0_role,
                            "mention_argument1_refid": relation_mention_argument1_refid,
                            "mention_argument1_role": relation_mention_argument1_role,
                            "mention_argument0_offset": relation_mention_argument0_extend_offset,
                            "mention_argument0_text": relation_mention_argument0_extend_text,
                            "mention_argument1_offset": relation_mention_argument1_extend_offset,
                            "mention_argument1_text": relation_mention_argument1_extend_text,
                            "mention_trigger_offset": relation_mention_trigger_offset,
                            "mention_trigger_text": relation_mention_trigger_text
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
    for event_elem in all_hopper_elems:
        event_id = event_elem.attrib["id"]

        all_event_mention_elems = event_elem.findall("event_mention")
        for event_mention_elem in all_event_mention_elems:
            event_mention_id = event_mention_elem.attrib["id"]
            event_mention_type = event_mention_elem.attrib["type"]
            event_mention_subtype = event_mention_elem.attrib["subtype"]
            event_mention_realis = event_mention_elem.attrib["realis"]

            event_mention_trigger_elem = event_mention_elem.findall("trigger")[0]
            event_mention_trigger_start = event_mention_trigger_elem.attrib["offset"]
            event_mention_trigger_end = int(event_mention_trigger_start) + \
                                        int(event_mention_trigger_elem.attrib["length"]) - 1
            event_mention_trigger_text = event_mention_trigger_elem.text
            event_mention_trigger_offset = event_mention_trigger_start + ":" + \
                                           str(event_mention_trigger_end)

            all_event_mention_argument_elems = event_mention_elem.findall("em_arg")
            all_event_mention_arguments = []
            for event_mention_argument_elem in all_event_mention_argument_elems:
                if "entity_id" in event_mention_argument_elem.attrib:
                    event_mention_argument_refid = event_mention_argument_elem.attrib["entity_mention_id"]
                    event_mention_argument_offset = entity_mentions_mentionid2dict[event_mention_argument_refid][
                        "offset"]
                    event_mention_argument_text = entity_mentions_mentionid2dict[event_mention_argument_refid][
                        "text"]
                elif "filler_id" in event_mention_argument_elem.attrib:
                    event_mention_argument_refid = event_mention_argument_elem.attrib["filler_id"]
                    event_mention_argument_offset = filler_mentions_mentionid2dict[event_mention_argument_refid][
                        "offset"]
                    event_mention_argument_text = filler_mentions_mentionid2dict[event_mention_argument_refid][
                        "text"]
                event_mention_argument_role = event_mention_argument_elem.attrib["role"]
                event_mention_argument_realis = event_mention_argument_elem.attrib["realis"]

                event_mention_argument_dict = {"mention_argument_refid": event_mention_argument_refid,
                                               "mention_argument_role": event_mention_argument_role,
                                               "mention_argument_realis": event_mention_argument_realis,
                                               "mention_argument_offset": event_mention_argument_offset,
                                               "mention_argument_text": event_mention_argument_text}
                all_event_mention_arguments.append(event_mention_argument_dict)

            mention_dict = {"event_id": event_id, "type": event_mention_type, "subtype": event_mention_subtype,
                            "realis": event_mention_realis,  "mention_id": event_mention_id,
                            "trigger_offset": event_mention_trigger_offset, "trigger_text": event_mention_trigger_text,
                            "argument": all_event_mention_arguments}

            event_mentions_id2dict[event_mention_id] = mention_dict

    return entity_mentions_mentionid2dict, filler_mentions_mentionid2dict, \
           relation_mentions_id2dict, event_mentions_id2dict


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--bio', type=str,
                        help='bio input path')
    parser.add_argument('--ann', type=str,
                        help='ace annotation input path')
    parser.add_argument('--ere', type=str,
                        help='output ace annotation path')
    parser.add_argument('--filelist', type=str,
                        help='filelist path')

    args = parser.parse_args()

    bio_path = args.bio
    ann_path = args.ann
    ere_path = args.ere

    if not os.path.exists(ere_path):
        os.makedirs(ere_path)

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
        ann_file = os.path.join(ann_path, f+".rich_ere.xml")
        ace_file = os.path.join(ere_path, f+".csv")

        if os.path.exists(bio_file) and os.path.exists(ann_file):
            write_ann(bio_file, ann_file, ace_file)


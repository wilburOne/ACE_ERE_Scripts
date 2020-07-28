import argparse
import os
import csv

import spacy
from spacy.tokens import Doc


class WhitespaceTokenizer(object):
    def __init__(self, vocab):
        self.vocab = vocab

    def __call__(self, text):
        words = text.split(' ')
        # All tokens 'own' a subsequent space character in this tokenizer
        spaces = [True] * len(words)
        return Doc(self.vocab, words=words, spaces=spaces)


def write_event(ace_file, trigger_file, arg_file, dep, nlp):
    all_sents = []
    sent = []
    with open(ace_file, 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            token = row["token"]
            if token == "----sentence_delimiter----":
                all_sents.append(sent)
                sent = []
            else:
                token_offset_parts = row["offset"].split(':')
                offset_parts = token_offset_parts[1].split('-')
                token_start = int(offset_parts[0])
                token_end = int(offset_parts[1])

                ner_tag = "O"
                if row["ner_type"] != "O":
                    ner_offset = row["ner_offset"].split(":")
                    ner_start = int(ner_offset[0])
                    if "#@#" in ner_offset[1]:
                        ner_offset_parts = ner_offset[1].split("#@#")
                        ner_end = int(ner_offset_parts[0])
                    else:
                        ner_end = int(ner_offset[1])
                    ner_type_parts = row["ner_type"].split(":")
                    ner_tag = ner_type_parts[0] + "-" + determine_tag(token_start, token_end, ner_start, ner_end)
                if row["trigger_type"] == "O":
                    sent.append(row["token"] + "\t" + row["offset"] + "\t" + row["trigger_type"] + "\t" +
                                row["trigger_arguments"] + "\t" + ner_tag)
                else:
                    event_offset_parts = row["trigger_offset"].split(':')
                    event_start = int(event_offset_parts[0])
                    event_end = int(event_offset_parts[1])
                    event_type_parts = row["trigger_type"].split(":")
                    tag = event_type_parts[1] + "-" + determine_tag(token_start, token_end, event_start, event_end)
                    sent.append(row["token"] + "\t" + row["offset"] + "\t" + tag + "\t" + row["trigger_arguments"]
                                + "\t" + ner_tag)
    if len(sent) > 0:
        all_sents.append(sent)
        sent = []

    vtag_all_sents = validate_tags(all_sents)          # check if a mention starts with "I" without "B"
    vseg_all_sents = validate_sent_seg(vtag_all_sents) # check if an event mention occurs in separate sents

    # write trigger and argument file
    out_trigger = open(trigger_file, 'w')
    out_arg = open(arg_file, 'w')

    for i in range(len(vseg_all_sents)):
        sent_id = i
        current_sent = vseg_all_sents[i]

        tok_idx2token = {}
        tok_idx2offset = {}
        tok_idx2label = {}
        tok_idx2ner = {}
        trigger_b2i = {}
        # write triggers
        pre_b_idx = -1
        for t in range(len(current_sent)):
            parts = current_sent[t].strip().split('\t')
            out_trigger.write(str(sent_id) + '\t' + str(t) + '\t' + parts[0] + '\t' + parts[1] + '\t' + parts[2] + "\n")
            tok_idx2offset[t] = parts[1]
            tok_idx2token[t] = parts[0]
            tok_idx2label[t] = parts[2]
            tok_idx2ner[t] = parts[-1]
            if parts[2].endswith('B'):
                pre_b_idx = t
                trigger_b2i[t] = [t]
            elif parts[2].endswith('O'):
                pre_b_idx = -1
            elif parts[2].endswith('I'):
                tmp = trigger_b2i[pre_b_idx]
                tmp.append(t)
                trigger_b2i[pre_b_idx] = tmp
        out_trigger.write('\n')

        # write arguments
        trigger2arg2role_idx = {}
        for t in range(len(current_sent)):
            parts = current_sent[t].strip().split('\t')
            if parts[2].endswith("B"):
                e1_idx = t
                arg_str = parts[3]
                if arg_str != 'O':
                    args = arg_str.split(' ')
                    for arg in args:
                        arg_parts = arg.split(':')
                        start = int(arg_parts[2])
                        end = int(arg_parts[3])
                        role = arg_parts[1]
                        e2_idx_set = search_e2(tok_idx2offset, start, end)
                        e1_idx_set = trigger_b2i[e1_idx]
                        e2_idx = e2_idx_set[0]
                        if e1_idx in trigger2arg2role_idx:
                            arg2role = trigger2arg2role_idx[e1_idx]
                            arg2role[e2_idx] = role + "-B"
                            trigger2arg2role_idx[e1_idx] = arg2role
                        else:
                            arg2role = {e2_idx: role + "-B"}
                            trigger2arg2role_idx[e1_idx] = arg2role

                        for e2_idx_tmp in e2_idx_set[1:]:
                            if e1_idx in trigger2arg2role_idx:
                                arg2role = trigger2arg2role_idx[e1_idx]
                                arg2role[e2_idx_tmp] = role + "-I"
                                trigger2arg2role_idx[e1_idx] = arg2role
                            else:
                                arg2role = {e2_idx_tmp: role + "-I"}
                                trigger2arg2role_idx[e1_idx] = arg2role

                        for e1_idx_tmp in e1_idx_set[1:]:
                            for e2_idx_tmp in e2_idx_set:
                                if e1_idx_tmp in trigger2arg2role_idx:
                                    arg2role = trigger2arg2role_idx[e1_idx_tmp]
                                    arg2role[e2_idx_tmp] = role + "-I"
                                    trigger2arg2role_idx[e1_idx_tmp] = arg2role
                                else:
                                    arg2role = {e2_idx_tmp: role + "-I"}
                                    trigger2arg2role_idx[e1_idx_tmp] = arg2role

        mod2head2dep = {}
        if dep:
            sent = ' '.join([t.split('\t')[0] for t in current_sent])
            doc_sent = nlp(sent)

            for i in range(len(doc_sent)):
                mod2head2dep[i] = {doc_sent[i].head.i:doc_sent[i].dep_}
            assert len(doc_sent) == len(current_sent)

        for t1 in range(len(current_sent)):
            e1_idx = t1
            e1_token = tok_idx2token[t1]
            e1_offset = tok_idx2offset[t1]
            e1_label = tok_idx2label[t1]
            for t2 in range(len(current_sent)):
                e2_idx = t2
                e2_token = tok_idx2token[t2]
                e2_offset = tok_idx2offset[t2]
                e2_label = tok_idx2label[t2]
                e2_ner = tok_idx2ner[t2]

                role = "O"
                if t1 in trigger2arg2role_idx and t2 in trigger2arg2role_idx[t1]:
                    role = trigger2arg2role_idx[t1][t2]

                if dep == "bi":
                    if e1_idx in mod2head2dep and e2_idx in mod2head2dep[e1_idx]:
                        out_arg.write(
                            str(sent_id) + '\t' + str(e1_idx) + '\t' + e1_token + '\t' + e1_offset + '\t' +
                            e1_label + '\t' + str(e2_idx) + '\t' + e2_token + '\t' + e2_offset + '\t' +
                            e2_label + '\t' + role + '\t' + mod2head2dep[e1_idx][e2_idx] + "\t" + e2_ner + '\n')
                    elif e2_idx in mod2head2dep and e1_idx in mod2head2dep[e2_idx]:
                        out_arg.write(
                            str(sent_id) + '\t' + str(e1_idx) + '\t' + e1_token + '\t' + e1_offset + '\t' +
                            e1_label + '\t' + str(e2_idx) + '\t' + e2_token + '\t' + e2_offset + '\t' +
                            e2_label + '\t' + role + '\t' + mod2head2dep[e2_idx][e1_idx] + "\t" + e2_ner + '\n')
                    else:
                        out_arg.write(
                            str(sent_id) + '\t' + str(e1_idx) + '\t' + e1_token + '\t' + e1_offset + '\t' +
                            e1_label + '\t' + str(e2_idx) + '\t' + e2_token + '\t' + e2_offset + '\t' +
                            e2_label + '\t' + role + '\t' + "NA" + "\t" + e2_ner + '\n')
                elif dep == "un":
                    if e1_idx in mod2head2dep and e2_idx in mod2head2dep[e1_idx]:
                        out_arg.write(
                            str(sent_id) + '\t' + str(e1_idx) + '\t' + e1_token + '\t' + e1_offset + '\t' +
                            e1_label + '\t' + str(e2_idx) + '\t' + e2_token + '\t' + e2_offset + '\t' +
                            e2_label + '\t' + role + '\t' + mod2head2dep[e1_idx][e2_idx] + "\t" + e2_ner + '\n')
                    else:
                        out_arg.write(
                            str(sent_id) + '\t' + str(e1_idx) + '\t' + e1_token + '\t' + e1_offset + '\t' +
                            e1_label + '\t' + str(e2_idx) + '\t' + e2_token + '\t' + e2_offset + '\t' +
                            e2_label + '\t' + role + '\t' + "NA" + "\t" + e2_ner + '\n')
                else:
                    out_arg.write(str(sent_id) + '\t' + str(e1_idx) + '\t' + e1_token + '\t' + e1_offset + '\t' +
                                  e1_label + '\t' + str(e2_idx) + '\t' + e2_token + '\t' + e2_offset + '\t' +
                                  e2_label + '\t' + role + '\t' + 'NA' + "\t" + e2_ner + '\n')
        out_arg.write("\n")

    out_trigger.close()
    out_arg.close()


def search_e2(tok_idx2offset, start, end):
    e2_idx = []
    for i in range(len(tok_idx2offset)):
        offset_parts = tok_idx2offset[i].split(':')[1].split('-')
        c_start = int(offset_parts[0])
        c_end = int(offset_parts[1])
        if start <= c_end <= end or start <= c_start <= end:
            e2_idx.append(i)
    return e2_idx


def validate_sent_seg(all_sents):
    cluster_idx = 0
    sent2cluster = {}
    merge_pre = False
    current_merge_next = False
    pre_merge_next = False
    current_single = False
    for i in range(len(all_sents)):
        current_sent = all_sents[i]
        sent_min, sent_max, ann_min, ann_max = get_offset_limit(current_sent)

        if sent_min <= ann_min and sent_max >= ann_max:
            current_single = True
        if sent_min > ann_min:
            merge_pre = True
        if sent_max < ann_max:
            current_merge_next = True

        if merge_pre:
            sent2cluster[i] = cluster_idx
        if not merge_pre and not current_merge_next and not pre_merge_next and current_single:
            sent2cluster[i] = cluster_idx+1
            cluster_idx += 1
        if pre_merge_next:
            sent2cluster[i] = cluster_idx
        if current_merge_next and not pre_merge_next:
            sent2cluster[i] = cluster_idx+1
            cluster_idx += 1

        merge_pre = False
        current_single = False
        pre_merge_next = current_merge_next
        current_merge_next = False

    cluster2sent = {}
    cluster_list = []
    for i in range(len(all_sents)):
        c = sent2cluster[i]
        if c not in cluster2sent:
            tmp = [i]
            cluster2sent[c] = tmp
            cluster_list.append(c)
        else:
            tmp = cluster2sent[c]
            tmp.append(i)

    new_all_sents = []
    for c in cluster_list:
        sids = cluster2sent[c]
        if len(sids) > 1:
            print(cluster2sent)
        newsents = []
        for s in sids:
            newsents += all_sents[s]
        new_all_sents.append(newsents)
    return new_all_sents


def get_offset_limit(current_sent):
    first_tok_offset = current_sent[0].split('\t')[1].split(':')[1].split('-')
    sent_min = int(first_tok_offset[0])
    last_tok_offset = current_sent[-1].split('\t')[1].split(':')[1].split('-')
    sent_max = int(last_tok_offset[1])

    ann_min = 100000
    ann_max = 0
    for line in current_sent:
        arg_str = line.strip().split('\t')[3]
        if arg_str != "O":
            arg_parts = arg_str.split(' ')
            for arg in arg_parts:
                parts = arg.split(':')
                s = int(parts[2])
                e = int(parts[3])
                if s < ann_min:
                    ann_min = s
                if e > ann_max:
                    ann_max = e
    if ann_min == 100000 and ann_max == 0:
        ann_min = sent_min
        ann_max = sent_max
    return sent_min, sent_max, ann_min, ann_max


def validate_tags(all_sents):
    new_all_sents = []
    pre_tag = ""
    for sents in all_sents:
        new_sents = []
        for i in range(len(sents)):
            current_line = sents[i].strip('\n')
            if len(current_line) == 0:
                new_sents.append(current_line + "\n")
            else:
                parts = current_line.split('\t')
                tag = parts[2]
                if tag.endswith("I") and not (pre_tag.endswith("B") or pre_tag.endswith("I")):
                    print("Error " + current_line)
                    new_line = sents[i].strip()[:-1] + "B"
                    new_sents.append(new_line + "\n")
                else:
                    new_sents.append(sents[i].strip() + "\n")
                pre_tag = tag
        new_all_sents.append(new_sents)
    return new_all_sents


def determine_tag(token_start, token_end, ner_start, ner_end):
    tag = "B"
    if token_start <= ner_start <= token_end:
        tag = "B"
    elif ner_start < token_start <= ner_end:
        tag = "I"
    return tag


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--ace', type=str,
                        help='ace input path')
    parser.add_argument('--event', type=str,
                        help='event path')
    parser.add_argument('--dep', type=str, default=None,
                        help='apply dependency parser or not')

    args = parser.parse_args()

    ace_path = args.ace
    event_path = args.event
    dep = args.dep

    nlp = None
    if dep:
        # import en_core_web_sm
        # nlp = en_core_web_sm.load()
        nlp = spacy.load("en_core_web_sm")# , disable=["tagger", "ner", "textcat"]
        nlp.tokenizer = WhitespaceTokenizer(nlp.vocab)

    if not os.path.exists(event_path):
        os.makedirs(event_path)

    file_names = []
    if os.path.isdir(ace_path):
        file_names = [item[:-4]
                  for item in os.listdir(ace_path)
                  if item.endswith(".csv")]
    else:
        file_names = [ace_path]

    for f in file_names:
        print(f)
        ace_file= os.path.join(ace_path, f+".csv")
        trigger_file = os.path.join(event_path, f+".trigger")
        arg_file = os.path.join(event_path, f + ".arg")

        if os.path.exists(ace_file):
            write_event(ace_file, trigger_file, arg_file, dep, nlp)

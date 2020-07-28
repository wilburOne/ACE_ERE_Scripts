import argparse
import os
import csv


def write_ner(ace_file, ner_file):
    all_lines = []
    with open(ace_file, 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            token = row["token"]
            if token == "----sentence_delimiter----":
                all_lines.append("\n")
            else:
                token_offset_parts = row["offset"].split(':')
                offset_parts = token_offset_parts[1].split('-')
                token_start = int(offset_parts[0])
                token_end = int(offset_parts[1])
                if row["ner_type"] == "O":
                    all_lines.append(row["token"] + " " + row["offset"] + " " + row["ner_type"] + "\n")
                else:
                    ner_nam_nom = row["ner_nam_nom"]
                    if ner_nam_nom == "NAM":
                        ner_offset_parts = row["ner_offset"].split(':')
                        ner_start = int(ner_offset_parts[0])
                        ner_end = int(ner_offset_parts[1])
                        ner_type_parts = row["ner_type"].split(":")
                        tag = ner_type_parts[0] + "-" + determine_tag(token_start, token_end, ner_start, ner_end)
                        all_lines.append(row["token"] + " " + row["offset"] + " " + tag + "\n")
                    else:
                        all_lines.append(row["token"] + " " + row["offset"] + " " + "O" + "\n")
    new_all_lines = validate_lines(all_lines)
    out = open(ner_file, 'w')
    for l in new_all_lines:
        out.write(l)
    out.close()


def validate_lines(all_lines):
    new_all_lines = []
    pre_tag = ""
    for i in range(len(all_lines)):
        current_line = all_lines[i].strip()
        if len(current_line) == 0:
            new_all_lines.append(current_line + "\n")
        else:
            parts = current_line.split(' ')
            tag = parts[2]
            if tag.endswith("I") and not (pre_tag.endswith("B") or pre_tag.endswith("I")):
                print("Error " + current_line)
                new_line = all_lines[i].strip()[:-1] + "B"
                new_all_lines.append(new_line + "\n")
            else:
                new_all_lines.append(all_lines[i].strip() + "\n")
            pre_tag = tag
    return new_all_lines


def determine_tag(token_start, token_end, ner_start, ner_end):
    tag = "B"
    if token_start <= ner_start <= token_end:
        tag = "B"
    elif ner_start < token_start < ner_end:
        tag = "I"
    return tag


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--ace', type=str,
                        help='ace input path')
    parser.add_argument('--ner', type=str,
                        help='ner bio path')

    args = parser.parse_args()

    ace_path = args.ace
    ner_path = args.ner

    if not os.path.exists(ner_path):
        os.makedirs(ner_path)

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
        ner_file = os.path.join(ner_path, f+".ner")

        if os.path.exists(ace_file):
            write_ner(ace_file, ner_file)
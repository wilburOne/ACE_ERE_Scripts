import argparse
import os

html_entities = []

python_path = os.path.abspath(__file__).replace("source2rsd.py", "")
with open(os.path.join(python_path, "html_entities"), 'r') as f:
    for line in f:
        parts = line.strip().split('\t')
        html_entities.append(parts[1])


def remove_xml_tag(source_file, rsd_file, data):
    out = open(rsd_file, 'w')
    signal = 0 # 0 before read <TEXT>, 1 after
    lines = []
    with open(source_file, 'r') as f:
        for line in f:
            line = line.strip('\n')
            if line == "<TEXT>":
                signal = 1
            if signal == 0:
                new_line = remove_tag(line, data, signal)
                out.write(new_line + " ")
            elif signal == 1:
                lines.append(line)
    con_line = ' '.join(lines)
    new_line = remove_tag(con_line, data, signal)
    out.write(new_line + " ")
    out.close()


def remove_tag(sent, data, signal):
    newsent = sent
    if data == 'ace' or data.lower() == 'ace':
        # keep text only after <TEXT>

        if (newsent.startswith("<DOCID>") or newsent.startswith("<DOCTYPE") or newsent.startswith("<DATETIME>")
                or newsent.startswith("<POSTER>") or newsent.startswith("<POSTDATE>")):
            while "<" in newsent and ">" in newsent and newsent.index("<") < newsent.index(">"):
                index1 = newsent.index("<")
                index2 = newsent.index(">")
                str1 = newsent[0:index1]
                str2 = newsent[index2+1:]
                newsent = str1+str2
        else:
            while "<" in newsent and ">" in newsent and newsent.index("<") < newsent.index(">"):
                index1 = newsent.index("<")
                index2 = newsent.index(">")
                str1 = newsent[0:index1]
                str2 = newsent[index2+1:]
                newsent = str1+str2

        if signal == 0:
            newsent = ''.join(len(newsent) * [' '])

    elif data == 'ere' or data.lower() == 'ere':
        # replace html entities
        for ent in html_entities:
            space_str = ''.join(len(ent)*[' '])
            newsent = newsent.replace(ent, space_str)
        tags = ["<post", "<quote"]
        for tag in tags:
            if tag in newsent:
                newsent = newsent.replace(tag, ''.join([' ']*len(tag)))
                newsent = newsent.replace(">", " ")
                newsent = newsent.replace("=", " ")
                newsent = newsent.replace("\"", " ")

        tags1 = ["<img", "<a", "</", "<"]
        for tag in tags1:
            while tag in newsent and ">" in newsent and newsent.index(tag)<newsent.index(">"):
                idx1 = newsent.index(tag)
                idx2 = newsent.index(">")
                subsent1 = newsent[0:idx1]
                subsent2 = newsent[idx2+1:]
                subsent3 = newsent[idx1:idx2+1]
                spaces_str = ''.join(len(subsent3) * [' '])
                newsent = subsent1 + spaces_str + subsent2
    return newsent


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=str,
                        help='input path')
    parser.add_argument('--rsd', type=str,
                        help='rsd path')
    parser.add_argument('--data', type=str,
                        help='ace or ere')
    parser.add_argument('--extension', type=str, default=".sgm",
                        help='')

    args = parser.parse_args()

    source_path = args.source
    rsd_path = args.rsd
    data = args.data
    suffix = args.extension

    if not os.path.exists(rsd_path):
        os.makedirs(rsd_path)

    file_names = []
    if os.path.isdir(source_path):
        file_names = [item for item in os.listdir(source_path) if item.endswith(suffix)]
    else:
        file_names = [source_path]

    for f in file_names:
        source_file= os.path.join(source_path, f)
        rsd_file = os.path.join(rsd_path, f)

        if os.path.exists(source_file):
            remove_xml_tag(source_file, rsd_file, data)
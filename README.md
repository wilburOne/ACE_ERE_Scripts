# ACE and ERE Preprocessing

This repository includes the preprocessing scripts for ACE and ERE datasets, including name tagging, entity coreference, relation extraction, event extraction and event coreference tasks. (verified on ACE_2005 and Rich_ERE corpus)

## Requirements

Python 3.6, jieba, NLTK

## Usage

### Step 1
Preprocess Data: remove XML tags from ACE/ERE articles, sentence merging.

```
python source2rsd.py --source [source_path] --rsd [rsd_path] --data [ace or ere] --extension [ending_of_source_files]
```

 > [source_path]: the path for input files (all .sgm files from ACE source corpus)
 
 > [rsd_path]: output path
 
### Step 2
Sentence segmentation, tokenization with offset retrieval

```
python rsd2ltf.py --rsd [rsd_path] --ltf [ltf_path] --extension [ending_of_rsd_files]
```

 > [rsd_path]: the path for rsd files from step 1
 
 > [ltf_path]: output path
 
### Step 3
Convert ltf files to sentences of tokens as the bio format in name tagging tasks

```
python ltf2bio.py --ltf [ltf_path] --bio [bio_path]
```

 > [ltf_path]: the path for input files
 
 > [bio_path]: output path
 
 ### Step 4
Add annotations to bio files

```
python bio2ace.py --bio [bio_path] --ann [ann_path] --ace [ace_path]
```

 > [bio_path]: the path for input files
 
 > [ann_path]: the path for all annotation files from ACE
 
 > [ace_path]: output path
 
Similarly, for ERE corpus,

```
python bio2ere.py --bio [bio_path] --ann [ann_path] --ere [ace_path]
``` 

## Citation
[1] Lifu Huang, Taylor Cassidy, Xiaocheng Feng, Heng Ji, Clare R Voss, Jiawei Han, Avirup Sil. Liberal Event Extraction and Event Schema Induction. Proc. ACL'2016

[2] Lifu Huang, Avirup Sil, Heng Ji, Radu Florian. Improving slot filling performance with attentive neural networks on dependency structures. Proc. EMNLP'2017

[3] Lifu Huang, Heng Ji, Kyunghyun Cho, Clare R Voss. Zero-shot transfer learning for event extraction, Proc. ACL, 2018

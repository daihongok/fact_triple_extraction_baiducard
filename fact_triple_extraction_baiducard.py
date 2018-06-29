#!/usr/bin/env python
# coding=utf-8
"""
文本中事实三元组抽取
python *.py input.txt output.txt begin_line end_line
"""

__author__ = "tianwen jiang"

# Set your own model path
#MODELDIR = "/data/ltp/ltp-models/3.3.0/ltp_data"
MODELDIR = "D:/Workspace/KG/ltp_data_v3.4.0"

import sys,re
import os
#import synonyms
import difflib


from pyltp import Segmentor, Postagger, Parser, NamedEntityRecognizer,SentenceSplitter

print "正在加载LTP模型... ..."

segmentor = Segmentor()
segmentor.load(os.path.join(MODELDIR, "cws.model"))

postagger = Postagger()
postagger.load(os.path.join(MODELDIR, "pos.model"))

parser = Parser()
parser.load(os.path.join(MODELDIR, "parser.model"))

#初始化实例
recognizer = NamedEntityRecognizer()
recognizer.load(os.path.join(MODELDIR, "ner.model"))

# labeller = SementicRoleLabeller()
# labeller.load(os.path.join(MODELDIR, "srl/"))

print "加载模型完毕。"

in_file_name = "D:\\Workspace\\KG\\baike_triples.txt"
out_file_name = "output.txt"
begin_line = 9
end_line = 0

if len(sys.argv) > 1:
    in_file_name = sys.argv[1]

if len(sys.argv) > 2:
    out_file_name = sys.argv[2]

if len(sys.argv) > 3:
    begin_line = int(sys.argv[3])

if len(sys.argv) > 4:
    end_line = int(sys.argv[4])


def extraction_start(in_file_name, out_file_name, begin_line, end_line):
    """
    事实三元组抽取的总控程序
    Args:
        in_file_name: 输入文件的名称
        #out_file_name: 输出文件的名称
        begin_line: 读文件的起始行
        end_line: 读文件的结束行
    """
    in_file = open(in_file_name, 'r')
    out_file = open(out_file_name, 'a')

    line_index = 1
    sentence_number = 0
    text_line = in_file.readline()
    while text_line:
        if line_index < begin_line:
            text_line = in_file.readline()
            line_index += 1
            continue
        if end_line != 0 and line_index > end_line:
            break
        sentence = text_line.strip()
        if sentence == "":
            text_line = in_file.readline()
            line_index += 1
            continue
        wordlist = re.split(r'[\t]', sentence)
        if(wordlist[1] != "BaiduCARD"):
            text_line = in_file.readline()
            line_index += 1
            continue
        try:
            extract_one_card(wordlist[2], wordlist[0], out_file)
            out_file.flush()
        except:
            pass
        sentence_number += 1
        if sentence_number % 50 == 0:
            print
            "%d done" % (sentence_number)
        text_line = in_file.readline()
        line_index += 1
    in_file.close()
    out_file.close()


def extract_one_card(paragraph, keyword, out_file):
    """
    给定一个card，分句子，并求三元组
    """
    sents = SentenceSplitter.split(paragraph)
    sentslist = list(sents)
    similarThreshold = 0.85 ;
    for sentence in sentslist:
        try:
            fact_triple_extract(sentence, keyword, similarThreshold, out_file)
            out_file.flush()
        except:
            pass

def is_keyword_similar(keyWord1, keyWord2, similarThreshold):
    value = difflib.SequenceMatcher(a=keyWord1, b=keyWord2).ratio()
    # try:
    #     value = synonyms.compare(keyWord1, keyWord2, seg=False)
    # except:
    if value >=similarThreshold:
        return True
    else:
        return False



def fact_triple_extract(sentence, keyword, similarThreshold, out_file):
    """
    对于给定的句子进行事实三元组抽取
    Args:
        sentence: 要处理的语句
    """
    # print sentence
    words = segmentor.segment(sentence)
    #list_words = list(words)
    # print "\t".join(words)
    postags = postagger.postag(words)
    #list_postags = list(postags)
    netags = recognizer.recognize(words, postags)
    #list_netags = list(netags)
    arcs = parser.parse(words, postags)
    #list_arcs = list([arcs.head,arcs.relation])
    #print "\t".join("%d:%s" % (arc.head, arc.relation) for arc in arcs)

    child_dict_list = build_parse_child_dict(words, postags, arcs)
    for index in range(len(postags)):
        # 抽取以谓词为中心的事实三元组
        if postags[index] == 'v':
            child_dict = child_dict_list[index]
            # 主谓宾
            if child_dict.has_key('SBV') and child_dict.has_key('VOB'):
                e1 = complete_e(words, postags, child_dict_list, child_dict['SBV'][0])
                if is_keyword_similar(e1,keyword,similarThreshold):
                   r = words[index]
                   e2 = complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
                   out_file.write("%s\t%s\t%s\n" % (keyword, r, e2))
                   out_file.flush()
            # 定语后置，动宾关系
            if arcs[index].relation == 'ATT':
                if child_dict.has_key('VOB'):
                    e1 = complete_e(words, postags, child_dict_list, arcs[index].head - 1)
                    r = words[index]
                    e2 = complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
                    temp_string = r + e2
                    if temp_string == e1[:len(temp_string)]:
                        e1 = e1[len(temp_string):]
                    if temp_string not in e1 and is_keyword_similar(e1,keyword,similarThreshold):
                        out_file.write("%s\t%s\t%s\n" % (keyword, r, e2))
                        out_file.flush()
            # 含有介宾关系的主谓动补关系
            if child_dict.has_key('SBV') and child_dict.has_key('CMP'):
                # e1 = words[child_dict['SBV'][0]]
                e1 = complete_e(words, postags, child_dict_list, child_dict['SBV'][0])
                if is_keyword_similar(e1,keyword,similarThreshold):
                    cmp_index = child_dict['CMP'][0]
                    r = words[index] + words[cmp_index]
                    if child_dict_list[cmp_index].has_key('POB'):
                        e2 = complete_e(words, postags, child_dict_list, child_dict_list[cmp_index]['POB'][0])
                        out_file.write("%s\t%s\t%s\n" % (keyword, r, e2))
                        out_file.flush()

        # 尝试抽取命名实体有关的三元组
        if netags[index][0] == 'S' or netags[index][0] == 'B':
            ni = index
            if netags[ni][0] == 'B':
                while netags[ni][0] != 'E':
                    ni += 1
                e1 = ''.join(words[index:ni + 1])
            else:
                e1 = words[ni]
            if is_keyword_similar(e1,keyword,similarThreshold):
                if arcs[ni].relation == 'ATT' and postags[arcs[ni].head - 1] == 'n' and netags[arcs[ni].head - 1] == 'O':
                    r = complete_e(words, postags, child_dict_list, arcs[ni].head - 1)
                    if e1 in r:
                        r = r[(r.index(e1) + len(e1)):]
                    if arcs[arcs[ni].head - 1].relation == 'ATT' and netags[arcs[arcs[ni].head - 1].head - 1] != 'O':
                        e2 = complete_e(words, postags, child_dict_list, arcs[arcs[ni].head - 1].head - 1)
                        mi = arcs[arcs[ni].head - 1].head - 1
                        li = mi
                        if netags[mi][0] == 'B':
                            while netags[mi][0] != 'E':
                                mi += 1
                            e = ''.join(words[li + 1:mi + 1])
                            e2 += e
                        if r in e2:
                            e2 = e2[(e2.index(r) + len(r)):]
                        if r + e2 in sentence:
                            out_file.write("%s\t%s\t%s\n" % (keyword, r, e2))
                            out_file.flush()


def build_parse_child_dict(words, postags, arcs):
    """
    为句子中的每个词语维护一个保存句法依存儿子节点的字典
    Args:
        words: 分词列表
        postags: 词性列表
        arcs: 句法依存列表
    """
    child_dict_list = []
    #print "\t".join("%d:%s" % (arc.head, arc.relation) for arc in arcs)
    for index in range(len(words)):
        child_dict = dict()
        for arc_index in range(len(arcs)):
            if arcs[arc_index].head == index + 1:
                if child_dict.has_key(arcs[arc_index].relation):
                    child_dict[arcs[arc_index].relation].append(arc_index)
                else:
                    child_dict[arcs[arc_index].relation] = []
                    child_dict[arcs[arc_index].relation].append(arc_index)
        # if child_dict.has_key('SBV'):
        #    print words[index],child_dict['SBV']
        child_dict_list.append(child_dict)
    return child_dict_list


def complete_e(words, postags, child_dict_list, word_index):
    """
    完善识别的部分实体
    """
    child_dict = child_dict_list[word_index]
    prefix = ''
    if child_dict.has_key('ATT'):
        for i in range(len(child_dict['ATT'])):
            prefix += complete_e(words, postags, child_dict_list, child_dict['ATT'][i])

    postfix = ''
    if postags[word_index] == 'v':
        if child_dict.has_key('VOB'):
            postfix += complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
        if child_dict.has_key('SBV'):
            prefix = complete_e(words, postags, child_dict_list, child_dict['SBV'][0]) + prefix

    return prefix + words[word_index] + postfix


if __name__ == "__main__":
    # extraction_start(in_file_name, out_file_name, begin_line, end_line)
    extraction_start(in_file_name, out_file_name, begin_line, end_line)

from hanziconv import HanziConv
import jieba
import jieba.posseg as pseg


def convert2simplified(text):
    try:
        return HanziConv.toSimplified(text)
    except:
        return text


def jieba_seg(text, mode):
    if mode == 'complete':
        seg_res = jieba.cut(text, cut_all=True)
        return [x for x in seg_res]
    elif mode == 'accurate':
        seg_res = jieba.cut(text, cut_all=False)
        return [x for x in seg_res]
    elif mode == 'search':
        seg_res = jieba.cut_for_search(text)
        return [x for x in seg_res]
    elif mode == 'accurate2gram':
        seg_res = jieba.cut(text, cut_all=False)
        seg_res1 = [x for x in seg_res]
        seg_res2 = [seg_res1[i] + seg_res1[i + 1] for i in range(len(seg_res1) - 1)]
        return seg_res1 + seg_res2
    elif mode == 'accurate3gram':
        seg_res = jieba.cut(text, cut_all=False)
        seg_res1 = [x for x in seg_res]
        seg_res2 = [seg_res1[i] + seg_res1[i + 1] for i in range(len(seg_res1) - 1)]
        seg_res3 = [seg_res1[i] + seg_res1[i + 1] + seg_res1[i + 2] for i in range(len(seg_res1) - 2)]
        return seg_res1 + seg_res2 + seg_res3
    else:
        return []


def pseg_2gram(text):
    seg_res = pseg.cut(text)
    seg_res1 = [x for x in seg_res]
    seg_res2 = [a for a, b in seg_res1]
    seg_res3 = []
    for i in range(len(seg_res2) - 1):
        seg_res3.append(seg_res2[i])
        seg_res3.append(seg_res2[i] + seg_res2[i + 1])
    seg_res3.append(seg_res2[i + 1])
    return {'words_sense': seg_res1, 'words': seg_res3}

# from nltk.tokenize.stanford_segmenter import StanfordSegmenter
# from nltk.tag import StanfordNERTagger, StanfordPOSTagger

# os.environ['JAVAHOME'] = 'C:/Program Files/Java/jre1.8.0_101/bin'
# os.chdir('C:/Users/u6062374/Downloads/Chinese Company Tagging/')

# def stanford_seg(article_id,mode):
#     segmenter = StanfordSegmenter(
#         path_to_jar="C:/Users/u6062374/Downloads/stanford-segmenter-2017-06-09/stanford-segmenter-3.8.0.jar",
#         path_to_slf4j="C:/Users/u6062374/Downloads/stanford-parser-full-2017-06-09/slf4j-api.jar",
#         path_to_sihan_corpora_dict="C:/Users/u6062374/Downloads/stanford-segmenter-2017-06-09/data/",
#         path_to_model="C:/Users/u6062374/Downloads/stanford-segmenter-2017-06-09/data/pku.gz",
#         path_to_dict="C:/Users/u6062374/Downloads/stanford-segmenter-2017-06-09/data/dict-chris6.ser.gz"
#     )
#     if mode=='1gram':
#         seg_res_1gram = segmenter.segment(convert2simplified(' '.join(in_articles[article_id]['text'])))
#         return seg_res_1gram
#     elif mode=='2gram':
#         seg_res_1gram = segmenter.segment(convert2simplified(' '.join(in_articles[article_id]['text'])))
#         seg_res1 = seg_res_1gram.split(' ')
#         seg_res2 = [seg_res1[i]+seg_res1[i+1] for i in range(len(seg_res1)-1)]
#         return seg_res_1gram + ' ' + ' '.join(seg_res2)
#     elif mode=='3gram':
#         seg_res_1gram = segmenter.segment(convert2simplified(' '.join(in_articles[article_id]['text'])))
#         seg_res1 = seg_res_1gram.split(' ')
#         seg_res2 = [seg_res1[i]+seg_res1[i+1] for i in range(len(seg_res1)-1)]
#         seg_res3 = [seg_res1[i]+seg_res1[i+1]+seg_res1[i+2] for i in range(len(seg_res1)-2)]
#         return seg_res_1gram + ' ' + ' '.join(seg_res2) + ' ' + ' '.join(seg_res3)
#     else:
#         return ''

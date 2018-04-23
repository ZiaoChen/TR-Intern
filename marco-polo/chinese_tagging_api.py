import sys, os

sys.path.append(os.path.abspath('..'))
import chinese_nlp
import openpyxl as px
import pandas as pd
import glob
from collections import Counter
import re
from googletrans import Translator

def get_company_name(row):
    if row[5]:
        name = row[5]
    elif row[4]:
        name = row[4]
    elif row[6]:
        name = row[6]
    else:
        name = row[2]
    return name

def load_company_names(file, sheet, exclude_alias):
    workbook = px.load_workbook(file)
    sheet = workbook.get_sheet_by_name(name=sheet)
    with open(exclude_alias, encoding="utf-8") as f:
        exclude = set([chinese_nlp.convert2simplified(l.split()[0]) for l in iter(f)])
    companies = []
    for row in sheet.iter_rows():
        row1 = []
        for cell in row:
            row1.append(cell.internal_value)
        # row2 = [x for x in row1 if not pd.isnull(x)]
        row2 = row1
        companies.append(row2)
    companies = companies[1:]
    companies1 = {}
    for company in companies:
        key = str(company[0])
        companies1[key] = {}
        companies1[key]['PermID'] = company[0]
        companies1[key]['RIC'] = company[1]
        companies1[key]['Name'] = get_company_name(company)
        if company[3]:
            companies1[key]['Name_EN'] = company[3]
        else:
            companies1[key]['Name_EN'] = company[2]

        companies1[key]['lexicon'] = set(company[2:])
        companies1[key]['lexicon_simp'] = set(
            [chinese_nlp.convert2simplified(x) for x in companies1[key]['lexicon']]) - exclude
    return companies1


def matching(text, companies):
    input_text = dict()
    input_text['text'] = text
    input_text['text_simp'] = chinese_nlp.convert2simplified(input_text['text'])
    matched = []
    w = chinese_nlp.pseg_2gram(input_text['text_simp'])
    words = set(w['words'])
    # words1 = Counter(w['words'])
    for k in companies:
        matched1 = words & companies[k]['lexicon_simp']
        if len(matched1) > 0:
            # companies[k]["Matched"] = ",".join(matched1)
            companies[k]["Matched"] = matched1
            matched.append(companies[k])
    # matched_occur = {}
    # for id in matched:
    #     matched_occur[id] = []
    #     for word in matched[id]:
    #         matched_occur[id] += [(x.start(), x.end()) for x in re.finditer(word, input_text['text_simp'])]
    # input_text['matched'] = matched
    # input_text['matched_occur'] = matched_occur
    return matched


def format_tagged_text(tagged):
    permid = []
    start = []
    end = []
    english_word_list = []
    translator = Translator()
    for id in tagged['matched_occur']:
        for x in tagged['matched_occur'][id]:
            permid.append(id)
            start.append(x[0])
            end.append(x[1])
    pos = pd.DataFrame({'permid': permid, 'start': start, 'end': end}).sort_values(['start', 'end'])
    pos['remove'] = 0
    for i in range(1, len(pos)):
        previous = pos.iloc[:i]
        previous = previous[previous['remove'] == 0]
        if pos['start'].iloc[i] < previous['end'].iloc[-1]:
            pos['remove'].iloc[i] = 1
    pos1 = pos[pos['remove'] == 0]
    text_format = ''
    current_pos = 0
    for i in range(len(pos1)):
        start_pos = pos1['start'].iloc[i]
        end_pos = pos1['end'].iloc[i]
        current_permid = 'https://permid.org/1-' + pos1['permid'].iloc[i]
        text_format += tagged['text'][current_pos:start_pos] + '<a href="' + current_permid + '" target="_blank">' + \
                       tagged['text'][start_pos:end_pos] + '</a>'
        current_pos = end_pos

    text_format += tagged['text'][current_pos:]
    tagged['text_format'] = text_format
    english_text = translator.translate(tagged['text_simp'].replace("<br>", "\n")).text
    tagged['english_format'] = ""

    current_pos = 0
    for i in range(len(pos1)):
        start_pos = pos1['start'].iloc[i]
        end_pos = pos1['end'].iloc[i]
        current_permid = 'https://permid.org/1-' + pos1['permid'].iloc[i]
        english_word = translator.translate(tagged['text'][start_pos:end_pos]).text
        print(tagged['text'][start_pos:end_pos])
        print(english_word)
        pos2 = [(x.start(), x.end()) for x in re.finditer(english_word, english_text)]
        if pos2 and len(pos2) > english_word_list.count(english_word):

            pos2 = pos2[english_word_list.count(english_word)]
            if pos2[0] > current_pos:
                tagged['english_format'] += english_text[current_pos
                                                         :pos2[
                                                             0]] + '<a href="' + current_permid + '" target="_blank">' + \
                                            english_text[pos2[0]:pos2[1]] + '</a>'
                print(current_pos)
                current_pos = pos2[1]
                english_word_list.append(english_word)

    tagged['english_format'] += english_text[current_pos:]
    tagged['english_format'] = tagged['english_format'].replace("\n", "<br>")
    return tagged

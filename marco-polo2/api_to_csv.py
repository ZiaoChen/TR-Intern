import pandas as pd
import os
import chinese_tagging_api
from googletrans import Translator
import chinese_nlp
import html2text
import csv
import re
from datetime import datetime

directory = 'live_news'
companies = chinese_tagging_api.load_company_names('Data/2000_Chinese_Companies.xlsx', 'Chinese Lexicon',
                                                   'Data/exclude_alias.txt')
global counter
counter = 1
translator = Translator()
text_maker = html2text.HTML2Text()
text_maker.ignore_links = True
text_maker.bypass_tables = False

tag_file = open('Data/Articles_Tags.csv', 'w', encoding='utf-8-sig')
writer1 = csv.writer(tag_file)
writer1.writerow(['Article_ID', 'PermID', 'RIC', 'Matched_Word', 'Relevance', 'Name', "Name_EN"])
content_file = open('Data/Articles_Content.csv', 'w', encoding='utf-8-sig')
writer2 = csv.writer(content_file)
writer2.writerow(["Article_ID", "Content", 'Content_EN', 'Title', 'Source', 'Time', 'Link'])


def convertToCSV(article):
    print(article["Title"])
    article_cn = text_maker.handle(article["Content"])
    if len(article_cn) > 1500:
        article_raw = chinese_nlp.convert2simplified(article_cn)
        matched_words = chinese_tagging_api.matching(article["Content"], companies)
        article_en = article_raw
        for word in matched_words:
            for tag in word['Matched']:
                article_en = article_en.replace(tag, " " + word["Name_EN"] + " ")

        try:
            article_en = translator.translate(article_en).text
        except:
            article_en = ""
            print("Article cannot be translated!")

        if article_en:
            article_en = article_en.replace("., ", ".,")
            for word in matched_words:
                word['Name_EN'] = word['Name_EN'].replace('., ', '.,')
                for tag in word['Matched']:
                    if word['Name_EN'] in article_en:
                        score = sum(1 for _ in
                                    re.finditer(chinese_nlp.convert2simplified(tag), article_raw)) / float(
                            len(article))
                        writer1.writerow(
                            [article["Article_ID"].replace(":",""), word['PermID'], word['RIC'], tag, score, word['Name'],
                             word['Name_EN']])
                    else:
                        print("Translation Error!")

            writer2.writerow([article["Article_ID"].replace(":",""), article_cn, article_en, article["Title"], article["Source"],
                              datetime.strptime(article["Time"], "%Y-%m-%dT%H:%M:%S").strftime('%d %b %Y %I:%M%p'), "https://www.thomsonreuters.com/en.html"])
    else:
        print("Article too short")


filename = os.listdir(directory)[-1]
file = pd.read_csv(os.path.join(directory, filename))
file.apply(convertToCSV, axis=1)
tag_file.close()
content_file.close()

import os
import csv
import chinese_tagging_api
from bs4 import BeautifulSoup
import random
import time
from googletrans import Translator
import chinese_nlp

directory = 'static/articles/'
counter = 0
companies = chinese_tagging_api.load_company_names('Data/2000_Chinese_Companies.xlsx', 'Chinese Lexicon',
                                                   'Data/exclude_alias.txt')
filename_list = []
import re


def strTimeProp(start, end, format, prop):
    """Get a time at a proportion of a range of two formatted times.

    start and end should be strings specifying times formated in the
    given format (strftime-style), giving an interval [start, end].
    prop specifies how a proportion of the interval to be taken after
    start.  The returned time will be in the specified format.
    """

    stime = time.mktime(time.strptime(start, format))
    etime = time.mktime(time.strptime(end, format))

    ptime = stime + prop * (etime - stime)

    return time.strftime(format, time.localtime(ptime))


def randomDate(start, end, prop):
    return strTimeProp(start, end, '%d %b %Y %I:%M%p', prop)


translator = Translator()
with open('Data/Articles_Tags.csv', 'w', encoding='utf-8-sig') as tag_file:
    writer1 = csv.writer(tag_file)
    writer1.writerow(['Article_ID', 'PermID', 'RIC', 'Matched_Word', 'Relevance', 'Name', "Name_EN"])
    with open('Data/Articles_Content.csv', 'w', encoding='utf-8-sig') as content_file:
        writer2 = csv.writer(content_file)
        writer2.writerow(["Article_ID", "Content", 'Content_EN', 'Title', 'Source', 'Time', 'Link', ])
        for filename in os.listdir(directory):
            # for filename in os.listdir(os.path.join(directory, folder)):
            if filename in filename_list:
                continue
            filename_list.append(filename)
            # with open(os.path.join(directory, folder, filename), 'r', encoding='utf-8-sig',
            with open(os.path.join(directory, filename), 'r', encoding='utf-8-sig',
                      errors='ignore') as file:
                print(counter)
                counter += 1
                filename = filename.replace(".html", "")
                article = file.read()
                soup = BeautifulSoup(article, 'lxml-xml')
                if filename.startswith('2'):
                    article = soup.find('body').text
                    title = soup.find('headline').text
                    source = "Reuters"
                else:
                    article = soup.find('Title').text
                    title = soup.find('Body').text
                    source = soup.find('Source').text
                # try:
                #     title = soup.find('h3').text
                # except:
                #     title = ""
                # try:
                #     body = soup.find('body').text
                #     if "Reuters" in body:
                #         source = "Reuters"
                #     else:
                #         source = "Not Reuters"
                # except:
                #     body = ""
                #     source = "Not Reuters"
                # article = html2text.html2text(body)
                # if article.startswith("### "):
                #     article = article.replace('### ', "")
                #
                article_sim = chinese_nlp.convert2simplified(article)
                article_en = article
                matched_words = chinese_tagging_api.matching(article, companies)

                for word in matched_words:
                    for tag in word['Matched']:
                        article_en = article_en.replace(tag, " " + word["Name_EN"] + " ")

                try:
                    article_en = translator.translate(article_en).text
                except:
                    article_en = ""
                    print("Error!")

                if article_en:
                    article_en = article_en.replace("., ", ".,")
                    for word in matched_words:
                        word['Name_EN'] = word['Name_EN'].replace('., ', '.,')
                        for tag in word['Matched']:
                            if word['Name_EN'] in article_en:
                                score = sum(1 for _ in
                                            re.finditer(chinese_nlp.convert2simplified(tag), article_sim)) / float(
                                    len(article))
                                writer1.writerow(
                                    [filename, word['PermID'], word['RIC'], tag, score, word['Name'],
                                     word['Name_EN']])
                            else:
                                print("Translation Error!")

                    writer2.writerow([filename, article, article_en, title, source,
                                      randomDate("1 Jan 2016 1:30PM", "1 Jan 2018 1:30PM", random.random()),
                                      os.path.join('articles/', filename)])
                else:
                    print("Jump")

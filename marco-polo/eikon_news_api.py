import requests
import json
import eikon as ek
import re
import pandas as pd
import datetime
import chinese_tagging_api
import csv

companies = chinese_tagging_api.load_company_names('Data/2000_Chinese_Companies.xlsx', 'Chinese Lexicon',
                                                   'Data/exclude_alias.txt')

ric_list = ['财经']

for x in companies:
    ric_list.append(companies[x]['Name'])

ek.set_app_id('F5FA9CCFBBD5247AE06A30D6')
today = datetime.datetime.now()
from_date = datetime.date.strftime(today - datetime.timedelta(days=1), '%Y-%m-%dT%H:%M:%S')
today = datetime.date.strftime(today, '%Y-%m-%dT%H:%M:%S')


def get_news(ric):
    headlines = ek.get_news_headlines(ric + ' IN CHINESE', date_from=from_date, date_to=today, count=100)
    return [{'time': datetime.date.strftime(a, '%Y-%m-%dT%H:%M:%S'), 'source': d, 'headline': b, 'storyid': c,
             'content': ek.get_news_story(c)} for a, b, c, d in
            zip(headlines['versionCreated'], headlines['text'], headlines['storyId'], headlines['sourceCode'])]


with open('live_news/' + today + '.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(["Time", "Source", 'Title', 'Article_ID', 'Content'])
    for i in range(len(ric_list)):
        try:
            news = get_news(ric_list[i])
            for x in news:
                r = writer.writerow(
                    [x['time'], x['source'], x['headline'].replace('\r', '').replace('\n', ''), x['storyid'],
                     x['content'].replace('\r', '').replace('\n', '')])
            if i % 100 == 0:
                print('complete ' + str(i) + '/' + str(len(ric_list)) + ' at ' + str(datetime.datetime.now()))
        except:
            pass

from flask import Flask, request, render_template
import pandas as pd
import json

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def main():
    portfolio_id_list = []

    if request.method == 'POST':
        if 'portfolio' in request.form:
            portfolio_id_list = request.form['portfolio'].split(',')
    else:

        display_data = combined_data
    company_list = json.dumps([x.replace('\'', "") for x in
                               list(set(tags_file.apply(lambda x: x["Name_EN"] + ' (' + x['RIC'] + ')', axis=1)))])
    company_info_list = dataframe_to_dict(tags_file[["Name_EN", "RIC", "PermID"]].drop_duplicates())
    display_cards = pd.DataFrame([])
    for name, group in display_data.groupby(['Article_ID', 'PermID']):
        if len(group) > 1:
            group["Relevance"] = group["Relevance"].mean()
        display_cards = display_cards.append(group.iloc[0, :])

    display_cards["Relevance"] = display_cards["Relevance"].apply(int)
    return render_template('UI.html', company_list=company_list, company_info_list=company_info_list,
                           cards=dataframe_to_dict(display_cards))


def get_company_file(filename):
    company_file = pd.read_excel(filename)
    # company_file = company_file[['PermID', 'RIC', 'EN_Official','CH_Official', 'cnYES', 'Baidu', 'FID 1352']].fillna("")
    # company_file["Name_CN"] = company_file.apply(lambda x: get_company_name(x), axis=1)
    return company_file[['PermID', 'EN_Official', 'RIC']].sort_values(by=['EN_Official'])


def get_company_name(row):
    if row["Baidu"]:
        name = row['Baidu']
    elif row["cnYES"]:
        name = row['cnYES']
    elif row["FID 1352"]:
        name = row['FID 1352']
    else:
        name = row['CH_Official']
    return name


def dataframe_to_dict(dataframe):
    return list(dataframe.T.to_dict().values())


def format_content(content, keyword):
    content = content.replace(keyword,
                              '<mark style="background-color:yellow !important;-webkit-text-fill-color: black !important;">' + keyword + '</mark>')
    pos = content.find(keyword)
    content_width = 300
    if pos <= content_width:
        first_half = ""
        if pos >= len(content) - content_width:
            second_half = ""
            middle = content
        else:
            second_half = content[pos + content_width:]
            middle = content[:pos + content_width]
    else:
        first_half = content[:pos - content_width]
        if pos >= len(content) - content_width:
            second_half = ""
            middle = content[pos - content_width:]
        else:
            second_half = content[pos + content_width:]
            middle = content[pos - content_width:pos + content_width]

    # sentences = sent_tokenize(content)
    # index = 0
    # found = False
    # for sentence in sentences:
    #     if keyword in sentence:
    #         found = True
    #         break
    #     index += 1
    #
    # if found:
    #     index = sentences[index].find(keyword)
    # if not found or len(sentences[index]) > 800:
    #     pos = content.find(keyword)
    #     if pos > len(content) - 800:
    #         second_half = ""
    #     else:
    #         second_half = content[pos+700:]
    #     middle = content[pos:pos+700]
    #     first_half = content[:pos]
    # else:
    #     sentences[index] = sentences[index].replace(keyword, '<mark style="background-color:yellow !important;-webkit-text-fill-color: black !important;">' + keyword + '</mark>')
    #     if index > 0:
    #         first_half = "".join(sentences[:index])
    #     else:
    #         first_half = ""
    #     if index < len(sentences) - 2:
    #         second_half = "".join(sentences[index + 2:])
    #     else:
    #         second_half = ""
    #
    #     if index == 0:
    #         if index == len(sentences) - 1:
    #             middle = sentences[index]
    #         else:
    #             middle = "".join(sentences[index:index + 2])
    #     else:
    #         if index == len(sentences) - 1:
    #             middle = "".join(sentences[index - 1:index + 1])
    #         else:
    #             middle = "".join(sentences[index - 1: index + 2])

    return first_half, middle, second_half


def normalize(data):
    return abs(data - data.mean()) / (data.max() - data.min())


articles_file = pd.read_csv('Data/Articles.csv')
articles_file["Article_ID"] = articles_file["Article_ID"].apply(lambda x: x.replace(".", ""))

tags_file = pd.read_csv('Data/Tags.csv')
tags_file["Article_ID"] = tags_file["Article_ID"].apply(lambda x: x.replace(".", ""))
company_file = get_company_file('Data/2000_Chinese_Companies.xlsx')
company_file["PermID"] = company_file["PermID"].apply(str)
company_file["EN_Official"] = company_file["EN_Official"].apply(str)
tags_file["PermID"] = tags_file["PermID"].apply(str)
tags_file["Relevance"] = tags_file['Relevance'].rank(ascending=False, pct=True)
tags_file["Relevance"] = normalize(tags_file["Relevance"]) * 100
# tags_file = tags_file.join(company_file.set_index('PermID'), on='PermID')
tags_file["Article_ID"] = tags_file["Article_ID"].apply(str)
combined_data = tags_file.join(articles_file.set_index('Article_ID'), on='Article_ID')
combined_data["Content_EN"] = combined_data["Content_EN"].apply(str)
combined_data["Content_Sliced"] = combined_data.apply(lambda x: format_content(x["Content_EN"], x["Name_EN"]), axis=1)
combined_data["First_Half"] = combined_data["Content_Sliced"].apply(lambda x: x[0])
combined_data["Middle"] = combined_data["Content_Sliced"].apply(lambda x: x[1])
combined_data["Second_Half"] = combined_data["Content_Sliced"].apply(lambda x: x[2])
combined_data = combined_data.drop(['Content', 'Content_Sliced'], axis=1)
app.run()

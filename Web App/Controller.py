from flask import Flask, request, render_template
import pandas as pd

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def main():
    portfolio_id_list = []
    cards = []
    if request.method == 'POST':
        if 'portfolio' in request.form:
            portfolio_id_list = request.form['portfolio'].split(',')
    else:
        display_data = combined_data[45:55]
    company_list = dataframe_to_dict(company_file)
    display_cards = pd.DataFrame([])
    for name, group in display_data.groupby(['Article_ID', 'PermID']):
        if len(group) > 1:
            group["Relevance"] = group["Relevance"].mean()
        display_cards = display_cards.append(group.iloc[0, :])

    return render_template('UI.html', company_list=company_list, portfolio_id_list=portfolio_id_list,
                           cards=dataframe_to_dict(display_cards))


def get_company_file(filename):
    company_file = pd.read_excel(filename)
    company_file = company_file[['PermID', 'RIC', 'CH_Official', 'cnYES', 'Baidu', 'FID 1352']].fillna("")
    company_file["Name"] = company_file.apply(lambda x: get_company_name(x), axis=1)
    return company_file[['PermID', 'Name']].sort_values(by=['Name'])


def get_company_name(row):
    if row["Baidu"]:
        name = row['Baidu']
    elif row["cnYES"]:
        name = row['cnYES']
    elif row["FID 1352"]:
        name = row['FID 1352']
    else:
        name = row['CH_Official']
    return name + ' (' + row['RIC'] + ')'


def dataframe_to_dict(dataframe):
    return list(dataframe.T.to_dict().values())


def format_content(content, keyword):
    sentences = content.split("。")
    index = 0
    for sentence in sentences:
        if keyword in sentence:
            break
        index += 1
    if index > 0:
        first_half = "".join(sentences[:index])
    else:
        first_half = ""
    if index < len(sentences) - 2:
        second_half = "".join(sentences[index + 2:])
    else:
        second_half = ""

    if index == 0:
        if index == len(sentences) - 1:
            middle = sentences[index]
        else:
            middle = "".join(sentences[index:index + 2])
    else:
        if index == len(sentences) - 1:
            middle = "".join(sentences[index - 1:index + 1])
        else:
            middle = "".join(sentences[index - 1: index + 2])

    return first_half, middle, second_half


articles_file = pd.read_csv('Data/Articles.csv')
articles_file["Article_ID"] = articles_file["Article_ID"].apply(lambda x: x.replace(".", ""))

tags_file = pd.read_csv('Data/Tags.csv')
tags_file["Article_ID"] = tags_file["Article_ID"].apply(lambda x: x.replace(".", ""))
company_file = get_company_file('Data/2000_Chinese_Companies.xlsx')
company_file["PermID"] = company_file["PermID"].apply(str)
tags_file["PermID"] = tags_file["PermID"].apply(str)
# tags_file = tags_file.join(company_file.set_index('PermID'), on='PermID')
tags_file["Article_ID"] = tags_file["Article_ID"].apply(str)
combined_data = tags_file.join(articles_file.set_index('Article_ID'), on='Article_ID')
combined_data["Content_Sliced"] = combined_data.apply(lambda x: format_content(x["Content"], x["Matched_Word"]), axis=1)
combined_data["First_Half"] = combined_data["Content_Sliced"].apply(lambda x: x[0])
combined_data["Middle"] = combined_data["Content_Sliced"].apply(lambda x: x[1])
combined_data["Second_Half"] = combined_data["Content_Sliced"].apply(lambda x: x[2])
combined_data = combined_data.drop(['Content', 'Content_Sliced'], axis=1)
app.run()

import requests
import os
from PyPDF2 import PdfFileReader
import pytesseract
from PIL import Image

def sendFile(file, headers, output_dir, output_file_name):
    response = requests.post(calais_url, data=file, headers=headers, timeout=80)
    print ('status code: %s' % response.status_code)
    content = response.text
    print ('Results received: %s' % content)
    if response.status_code == 200:
        saveFile(output_file_name, output_dir, content)


def saveFile(file_name, output_dir, content):
    output_file_name = os.path.basename(file_name) + '.txt'
    output_file = open(os.path.join(output_dir, output_file_name), 'wb')
    output_file.write(content.encode('utf-8'))
    output_file.close()

def getPDFContent(path):
    content = ""
    # Load PDF into pyPDF
    pdf = PdfFileReader(path, "rb")
    # Iterate pages
    for i in range(0, pdf.getNumPages()):
        # Extract text from page and add to content
        content += pdf.getPage(i).extractText() + "\n"
    # Collapse whitespace
    content = " ".join(content.replace("\xa0", " ").strip().split())
    return content
# pytesseract.pytesseract.tesseract_cmd = 'C:/Users/uc238618/Desktop/Tesseract-OCR/tesseract'
# image = Image.open('Data/8.jpg')
# print (pytesseract.image_to_string(image))
calais_url = 'https://api.thomsonreuters.com/permid/calais'
access_token = "Mck6PohAvY2jMrqDYXdK7ngcuDCPFwrP"
input_file = "Data/report.pdf"
headers = {'X-AG-Access-Token': access_token, 'Content-Type': 'text/raw', 'outputformat': 'application/json'}
file = getPDFContent(input_file)
sendFile(file, headers, 'Output/', 'test')

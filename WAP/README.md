# sgml-converter

This is the repo for sgml-converter, which takes scanned PDF files as the input and generates the corresponding SGML file.

### Discription

The process of this converter can be summarized as:

![flow](img/flow.png)

* reason for DOCX:

  > We have tried the most popular open-sourced library: "Tesseract" with newest 4.0 version(LSTM integrated). Although it is pretty stable for text extraction, `Tesseract` is unsuitable for extracting the text formats. After several experiments, we found that the OCR API supported by `ABBYY` is currently the best option. It is a commercial SDK, we purchased the license for converting PDF to DOCX with most of styles. For demo, we replace the license with a free, limited one.

* reason for HTML:

  > We tried to make a fusion of text contents and its styles from DOCX file. However, it seems that the best way to interact with DOCX is using C#, and most of the Python packages exist some vital weakness. For utility and readability, we decided to use HTML as temp data.

* handcrafted rules for SGML: 

  > There is a group of rules for SGML elements. For further details, please refer to `SGML_standard.pdf`.



**Notice**: currently, due to the unstable results in OCR results, we FAIL to convert the `tables` and `images(signature)` in PDF file. These contents need human's intervention.

### Requirements

* Python 2.7
* Java JRE 8

### Install
If you do not have Docker already you can download it from here https://www.docker.com/community-edition. Docker must be running for the install to work.

```shell
# clone this repository
git clone https://git.sami.int.thomsonreuters.com/Rees.Simmons/sgml-converter
# navigate to the directory of the cloned repo

# build the image from Dockerfile, should be around 211 MB
docker build -t converter .
```
### Example

```
example_directory
└───Sears_Canada
│   │   Case_file_1.pdf
│   │   Case_file_2.pdf
|   |   case_metadata.txt
```

##### case_metadata.txt 

format
```
COMPANY_NAME
COURT_FILE_NUMBER
COURT_NAME
```

example
```
Sears Canada
1201-14658
SUPERIOR COURT OF JUSTICE
```

### Usage
```shell
#To OCR all PDF files in /Sears_Canada navigate to the folder and run this exact command.
#The case_metadata.txt file must be present to properly convert all 

docker run --rm -v "$(PWD):/tmp" -it converter --all
```


### * Machine Learning Approach

```

We are curious about how to solve this problem by machine learning approachs. Currently, we are experimenting LSTM and BoostingTree methods. However, since the SGML rules are special in a way, we are not optimized about the results.
```
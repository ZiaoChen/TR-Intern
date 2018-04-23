# Marco Polo Web App

* Data contains mostly files provided by TMS
* `load_data.py` generates the `Articles.csv` and `Tags.csv` files for consumption by the API
* `Controller.py` is the flask backend code
* `chinese_nlp.py` is the core NLP algorithm to segment articles
* `chinese_tagging_api.py` is the core API to tag articles
* `static` and `templates` folders are frontend ressources served by flask
* `requirements.txt` is the list of packages to install using `pip install -r requirements.txt`

## Installation

```
docker build -t marco-polo .
```

## Run app on docker container

```
docker run -d -p 5000:5000 marco-polo:latest
```

Then you should be able to access at http://localhost:5000

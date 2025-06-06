from flask import Flask, render_template, request
from flask_cors import CORS, cross_origin
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen as uReq
import logging
import pymongo
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


logging.basicConfig(filename="scrapper.log", level=logging.INFO)

app = Flask(__name__)

@app.route("/", methods=['GET'])
def homepage():
    return render_template("index.html")

@app.route("/review", methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        try:
            searchString = request.form['content'].replace(" ", "")
            flipkart_url = "https://www.flipkart.com/search?q=" + searchString
            uClient = uReq(flipkart_url)
            flipkartPage = uClient.read()
            uClient.close()

            flipkart_html = bs(flipkartPage, "html.parser")
            bigboxes = flipkart_html.find_all("div", {"class": "_75nlfW"})

            # Avoid index out of range
            if len(bigboxes) <= 3:
                logging.info("Not enough product boxes found. Length: {}".format(len(bigboxes)))
                return "No products found or page layout has changed."

            del bigboxes[0:3]

            if not bigboxes:
                logging.info("No product box found after deleting first 3 items.")
                return "No products found. Try another search keyword."

            box = bigboxes[1]

            productLink = "https://www.flipkart.com" + box.div.div.a['href']
            prodRes = requests.get(productLink)
            prodRes.encoding = 'utf-8'
            prod_html = bs(prodRes.text, "html.parser")

            commentboxes = prod_html.find_all('div', {'class': "RcXBOT"})

            filename = searchString + ".csv"
            with open(filename, "w", encoding='utf-8') as fw:
                headers = "Product, Customer Name, Rating, Heading, Comment\n"
                fw.write(headers)

                reviews = []
                for commentbox in commentboxes:
                    try:
                        name = commentbox.div.div.find_all('p', {'class': '_2NsDsF AwS1CA'})[0].text
                    except:
                        name = "No Name"
                        logging.info("Name not found")

                    try:
                        rating = commentbox.div.div.div.div.text
                    except:
                        rating = 'No Rating'
                        logging.info("Rating not found")

                    try:
                        commentHead = commentbox.div.div.div.p.text
                    except:
                        commentHead = 'No Comment Heading'
                        logging.info("Comment Head not found")

                    try:
                        comtag = commentbox.div.div.find_all('div', {'class': 'ZmyHeo'})
                        custComment = comtag[0].div.text
                    except:
                        custComment = "No Comment"
                        logging.info("Customer Comment not found")

                    mydict = {
                        "Product": searchString,
                        "Name": name,
                        "Rating": rating,
                        "CommentHead": commentHead,
                        "Comment": custComment
                    }
                    reviews.append(mydict)

                    fw.write(f"{searchString}, {name}, {rating}, {commentHead}, {custComment}\n")

            logging.info("Final reviews: {}".format(reviews))
            uri = "mongodb+srv://2022csravina12304:221004@cluster0.kixryvt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
            client = MongoClient(uri, server_api=ServerApi('1'))
            db = client['review_scrap']
            review_col = db['review_scrap_data']
            review_col.insert_many(reviews)

            return render_template('result.html', reviews=reviews)

        except Exception as e:
            logging.error("Exception occurred", exc_info=True)
            return 'Something went wrong. Please try again.'
    else:
        return render_template('index.html')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

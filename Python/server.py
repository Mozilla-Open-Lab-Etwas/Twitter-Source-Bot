from modules import ProcessBody
from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
from googlesearch import search
import tornado
import asyncio
from pymongo import MongoClient

from dotenv import load_dotenv
from pathlib import Path

import os
import json
import requests

load_dotenv(dotenv_path=Path("../.env"))


class GetSample(RequestHandler):
    def get(self):
        self.write({"status": "true"})


def env_or_break(var):
    """
    Get the environment variable `var` or break.
    """
    val = os.getenv(var)
    if val is None:
        raise ValueError(f"Environment variable `{var}` needs to be set.")
    return val


async def db_output(output, tweetId):
    tweetId = str(tweetId)
    client = MongoClient('mongodb://{}'.format(env_or_break("MONGO_URL")))
    db = client['tweets']

    output = [str(item) for item in output]

    tweet = db.nlpSchemas.find_one(
        {"tweetId": tweetId})
    if tweet is not None:
        nlpOutput = tweet['nlpOutput'] + "\n".join(output)
        db.nlpSchemas.update_one({"tweetId": tweetId}, {
            "$set": {"nlpOutput": nlpOutput}
        })
    else:
        nlpOutput = "\n".join(output)
        db.nlpSchemas.insert_one(
            {"tweetId": tweetId, "nlpOutput": nlpOutput})


class handleProcessBody(RequestHandler):
    async def post(self):
        body = self.request.body
        body = json.loads(body)

        print("---- New Request ----")
        data = body["data"]
        keywords = body["keywords"]
        url = body["url"]
        tweetId = body["tweetId"]

        score, output = await ProcessBody.getDocumentScore(data, url, keywords)
        print("FINAL SCORE", score, url)

        output.append("---- Keywords  ----")
        for keyword in keywords:
            if "partOfSpeech" in list(keyword.keys()):
                partOfSpeech = keyword["partOfSpeech"]
            else:
                partOfSpeech = "None"

            output.append(
                "Word: " + keyword['word'] + " | Part of Speech: " + partOfSpeech)
        #output.append(" ---- Full Body --- ")
        #output.append("---- Url ---- \t" + url)
        # output.append(data['text'])
        # output.append("\n\n")
        await db_output(output, tweetId)

        self.write({"score": score})


class searchResults(RequestHandler):
    async def get(self):
        print("-- Search Request --")
        query = self.get_argument('query', None)

        results = list(search("{}".format(query), num=10, stop=10, pause=2))

        processed = [{"url": link} for link in results]
        print(processed)

        self.write({"results": processed})


def make_app():
    urls = [
        ("/", GetSample),
        ("/processBody", handleProcessBody),
        ('/search', searchResults),
    ]
    return Application(urls)


def discord_webhook():

    discord_url = env_or_break("DISCORD_SERVER_URL")
    requests.post(discord_url, data={'content': 'Python Server running', 'username': 'Who Said This Bot(Python)',
                                     'avatar_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png'})


if __name__ == "__main__":
    port = 5000
    print("Tornado is up and running!")
    discord_webhook()
    app = make_app()
    app.listen(port)

    IOLoop.instance().start()

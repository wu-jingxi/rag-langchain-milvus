import requests

def rerank(query, docs):
    res = requests.post(
        "http://localhost:8001/rerank",
        json={
            "query": query,
            "docs": docs
        }
    ).json()

    return [x["text"] for x in res["results"]]
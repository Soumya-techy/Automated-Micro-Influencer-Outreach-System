from apify_client import ApifyClient
import os
from dotenv import load_dotenv
load_dotenv()

def instagram_details_finder(url:list[str]):
    client=ApifyClient(os.getenv('APIFY_API_TOKEN'))
    run_input={
    "addParentData": False,
    "directUrls": url,
    "onlyPostsNewerThan": "2026-01-01",
    "resultsLimit": 3,
    "resultsType": "details",
    "skipPinnedPosts": True
    }
    run=client.actor("apify/instagram-scraper").call(run_input=run_input)
    dataset_id=run.default_dataset_id
    dataset=client.dataset(dataset_id=dataset_id).list_items().items
    print(dataset)
instagram_details_finder(['https://www.instagram.com/satshyaa/'])
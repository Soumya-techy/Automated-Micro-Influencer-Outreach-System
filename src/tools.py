from apify_client import ApifyClient
import os
from dotenv import load_dotenv
load_dotenv()

def instagram_details_finder(url:list[str]):
    creator_info=[]
    client=ApifyClient(os.getenv('APIFY_API_TOKEN'))
    run_input={
    "addParentData": False,
    "directUrls": url,
    "onlyPostsNewerThan": "2026-01-01",
    "resultsLimit": 5,
    "resultsType": "details",
    "skipPinnedPosts": True
    }
    run=client.actor("apify/instagram-scraper").call(run_input=run_input)
    dataset_id=run.default_dataset_id
    dataset=client.dataset(dataset_id=dataset_id).list_items().items
    for item in dataset:
        posts = item.get("latestIgtvVideos", [])
    
        total_likes = sum(p.get("likesCount", 0) for p in posts)
        total_comments = sum(p.get("commentsCount", 0) for p in posts)
        total_views = sum(p.get("videoViewCount", 0) for p in posts)
    
        engagement = (total_likes + total_comments) / total_views if total_views > 0 else 0.0

        creator_dict = {
            "username": item.get("username"),
            "full_name": item.get("fullName"),
            "followers": item.get("followersCount"),
            "engagement": engagement
        }
    
        creator_info.append(creator_dict)
    return creator_info
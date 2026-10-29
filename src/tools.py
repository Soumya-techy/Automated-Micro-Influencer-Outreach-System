from apify_client import ApifyClient
import os
from dotenv import load_dotenv
import requests
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
    run=client.actor("apify/instagram-scraper").call(run_input=run_input,max_total_charge_usd=1.0)
    dataset_id=run.default_dataset_id
    dataset=client.dataset(dataset_id=dataset_id).list_items().items
    for item in dataset:
        posts = item.get("latestIgtvVideos", [])
        post_caption=item.get('latestIgtvVideos',[])
        if post_caption:
            caption=post_caption[0].get('caption',"")
    
        total_likes = sum(p.get("likesCount", 0) for p in posts)
        total_comments = sum(p.get("commentsCount", 0) for p in posts)
        total_views = sum(p.get("videoViewCount", 0) for p in posts)
    
        engagement = (total_likes + total_comments) / total_views if total_views > 0 else 0.0

        creator_dict = {
            "username": item.get("username"),
            "full_name": item.get("fullName"),
            "followers": item.get("followersCount"),
            'bio': item.get('biography'),
            "engagement": engagement,
            'latest_reel_caption': caption
        }
    
        creator_info.append(creator_dict)
    return creator_info

def instagram_account_finder():
    client=ApifyClient(os.getenv('APIFY_API_TOKEN'))
    run_input={
  "hashtags": [
    "beauty","makeup","glowup","skincare","fashion"
  ],
  "maxInfluencers": 25,
  "minFollowers": 5000,
  "crawlWebsite": True,
  "product": "instagram-influencers"
}
    run=client.actor("aolmo/instagram-influencers").call(run_input=run_input,max_total_charge_usd=1.0)
    dataset_id=run.default_dataset_id
    dataset=client.dataset(dataset_id=dataset_id).list_items().items
    print(dataset)

from apify_client import ApifyClient
import os
import re
from dotenv import load_dotenv
import requests
load_dotenv()

def extract_emails_from_bio(bio_text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, bio_text)  
    return list(set(email.lower() for email in emails))

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

        if item['followersCount']<5000 or item['followersCount']>100000 or engagement<0.03 or len(extract_emails_from_bio(item['biography']))==0:
            continue 
        creator_dict = {
            "url": item.get("username"),
            "full_name": item.get("fullName"),
            "followers": item.get("followersCount"),
            'contact': extract_emails_from_bio(bio_text=item["biography"]),
            "engagement": engagement,
            'latest_reel_caption': caption,
            'Platform': 'Youtube',
            'Contacted': False
        }
    
        creator_info.append(creator_dict)
    return creator_info

def instagram_influencer_finder():
    client=ApifyClient(os.getenv('APIFY_API_TOKEN'))
    run_input={
  "hashtags": [
    "beauty","makeup","glowup","skincare","fashion"
  ],
  "maxInfluencers": 35,
  "minFollowers": 5000,
  "crawlWebsite": True,
  "product": "instagram-influencers"
}
    run=client.actor("aolmo/instagram-influencers").call(run_input=run_input,max_total_charge_usd=1.0)
    dataset_id=run.default_dataset_id
    dataset=client.dataset(dataset_id=dataset_id).list_items().items

def Youtube_creator_finder():
    response=requests.get(url='https://www.googleapis.com/youtube/v3/search',params={'part': 'snippet',
                                                                                     'q':	'shef skincare, makeup, glowup',
                                                                                     'type':	'channel',
                                                                                     'regionCode':'IN',
                                                                                     'maxResults':1,
                                                                                     'key':os.getenv('YT_API_KEY')})
    result=response.json()
    for item in result.get('items', []):
        description = item['snippet']['description']
    print(description)
Youtube_creator_finder()

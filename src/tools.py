from apify_client import ApifyClient
import os
import re
from dotenv import load_dotenv
from datetime import datetime,timezone
import requests
load_dotenv()

def extract_emails_from_bio(bio_text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, bio_text)  
    return list(set(email.lower() for email in emails))

def extract_instagram_handles(text: str) -> list[str]:
    IG_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:instagram\.com|instagr\.am)/"
    r"([A-Za-z0-9._]{1,30})(?![A-Za-z0-9._])",
    re.IGNORECASE,
    )

    IG_MENTION_RE = re.compile(
    r"\b(?:insta(?:gram)?|ig)\b\s*[:\-–|]?\s*@([A-Za-z0-9._]{1,30})(?![A-Za-z0-9._])",
    re.IGNORECASE,
    )

    RESERVED = {
    "p", "reel", "reels", "tv", "stories", "explore", "accounts",
    "direct", "about", "legal", "developer", "web", "share", "s",
    }
    if not text:
        return []

    candidates = IG_URL_RE.findall(text) + IG_MENTION_RE.findall(text)

    handles, seen = [], set()
    for h in candidates:
        h = h.strip(".").lower()          
        if not h or h in RESERVED or h in seen:
            continue
        seen.add(h)
        handles.append(h)
    return handles

def instagram_details_finder(url:list[str]):
    creator_info=[]
    seen=set()
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
        contact=extract_emails_from_bio(bio_text=item["biography"])

        if item['followersCount']<5000 or item['followersCount']>100000 or engagement<0.03 or len(extract_emails_from_bio(item['biography']))==0:
            continue
        if contact in seen:
            continue
        seen.add(contact)
        creator_dict = {
            "url": item.get("username"),
            "full_name": item.get("fullName"),
            "followers": item.get("followersCount"),
            'contact': contact,
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
  "maxInfluencers": 50,
  "minFollowers": 500,
  "crawlWebsite": False,
  "product": "instagram-influencers"
}
    run=client.actor("aolmo/instagram-influencers").call(run_input=run_input,max_total_charge_usd=1.0)
    dataset_id=run.default_dataset_id
    dataset=client.dataset(dataset_id=dataset_id).list_items().items

    creator_info = [f"www.instagram.com/{item['username']}" for item in dataset if "username" in item]
    return creator_info



def Youtube_creator_finder():
    QUERIES = ["GRWM India", "affordable makeup haul", "skincare routine Hindi", "lehenga lookbook", "drugstore skincare India"]
    seen=set()
    creator_info=[]
    for q in QUERIES:
        token=None
        for _ in range(2):
            response=requests.get(url='https://www.googleapis.com/youtube/v3/search',params={
            'part':'snippet',
            'q':q,
            'type':'video',
            'max_results':10,
            'regionCode':'IN',
            'publishedAfter':'2026-05-04',
            'publishedBefore': datetime.now(timezone.utc).isoformat(),
            'pageToken':token
        })
            result=response.json()
            for item in result['items']:
                cid = item["snippet"]["channelId"]
                if cid in seen:
                    continue
                seen.add(cid)
                snip=item['snippet']
                desc=snip.get('description',"")
                if not extract_instagram_handles(desc):
                    continue
                creator_info.extend(extract_instagram_handles(desc))
            token=result.get('nextPageToken')
            if not token:
                break
    return creator_info

Youtube_creator_finder()
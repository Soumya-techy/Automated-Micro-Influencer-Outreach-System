from apify_client import ApifyClient
import os
import re
from dotenv import load_dotenv
from datetime import datetime,timezone
import requests
from pymongo import MongoClient
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
load_dotenv()

client=MongoClient('mongodb://localhost:27017/')
db=client['Influencer_data']
collection1=db['Aceepted']
collection2=db['Rejected']

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
        handles.append(f"www.instagram.com/{h}")
    return handles

def calc_engagement(posts, followers):
    posts = posts[:5]
    if not posts or not followers:
        return 0.0
    total = sum(max(p.get("likesCount") or 0, 0) + (p.get("commentsCount") or 0) for p in posts)
    return (total / len(posts)) / followers 

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
        posts = item.get("latestPosts", [])
        followers=item.get("followersCount",0)
        if posts:
            caption=posts[0].get('caption',"")
    
        engagement = calc_engagement(posts=posts,followers=followers)

        contact=extract_emails_from_bio(bio_text=item.get('biography',""))

        if item.get('followersCount',0)<5000 or item.get('followersCount',0)>250000 or engagement<0.1 or len(contact)==0:
            collection2.insert_one({"url": f'www.instagram.com/{item.get("username")}',
                                    "full_name": item.get("fullName"),
                                    'followers_issue':item.get('followersCount',0)<5000 or item.get('followersCount',0)>250000,
                                    'engagement_issue':engagement<0.1,
                                    'contact_found_issue':True if len(contact)==0 else False})
            continue
        if contact in list(collection1.find({},{'contact':1, "_id":0})):
            continue
        seen.add(contact)
        creator_dict = {
            "url": f'www.instagram.com/{item.get("username")}',
            "full_name": item.get("fullName"),
            "followers": item.get("followersCount"),
            'contact': contact,
            "engagement": engagement,
            'latest_reel_caption': caption,
            'Contacted': False
        }
    
        creator_info.append(creator_dict)
    if creator_info:
        collection1.insert_many(creator_info)
    return creator_info

def instagram_influencer_finder():
    client=ApifyClient(os.getenv('APIFY_API_TOKEN'))
    run_input={
  "hashtags": [
    "beauty","makeup","glowup","skincare","fashion"
  ],
  "maxInfluencers": 12,
  "minFollowers": 500,
  "crawlWebsite": False,
  "product": "instagram-influencers"
}
    run=client.actor("aolmo/instagram-influencers").call(run_input=run_input,max_total_charge_usd=1.0)
    dataset_id=run.default_dataset_id
    dataset=client.dataset(dataset_id=dataset_id).list_items().items

    creator_info = [f"https://www.instagram.com/{item['username']}/" for item in dataset if "username" in item]
    return creator_info



def Youtube_creator_finder():
  QUERIES = [
      "GRWM India",
      "affordable makeup haul",
      "skincare routine Hindi",
      "lehenga lookbook",
      "drugstore skincare India",
  ]
  seen = set()
  creator_info = []

  api_key = os.getenv("YT_API_KEY")
  if not api_key:
    print("Error: YT_API_KEY environment variable is not set!")
    return creator_info

  for q in QUERIES:
    token = None
    for _ in range(2):
      search_resp = requests.get(
          url="https://www.googleapis.com/youtube/v3/search",
          params={
              "part": "id,snippet",
              "q": q,
              "type": "video",
              "maxResults": 50,
              "regionCode": "IN",
              "publishedAfter": "2026-05-04T00:00:00Z",
              "publishedBefore": datetime.now(timezone.utc).isoformat(),
              'videoDuration':'medium',
              "pageToken": token,
              "key": api_key,
          },
      ).json()
      items = search_resp.get("items", [])
      if not items:
        break

      video_ids = []
      for item in items:
        vid = item.get("id", {}).get("videoId")
        if vid:
          video_ids.append(vid)

      if not video_ids:
        continue

      for i in range(0, len(video_ids), 50):
        batch_ids = ",".join(video_ids[i : i + 50])
        details_resp = requests.get(
            url="https://www.googleapis.com/youtube/v3/videos",
            params={"part": "snippet", "id": batch_ids, "key": api_key},
        ).json()

        for v_item in details_resp.get("items", []):
          snip = v_item["snippet"]
          cid = snip.get("channelId")

          if cid.lower() in seen:
            continue

          desc = snip.get("description", "").lower()
          handles = extract_instagram_handles(desc)

          if not handles:
            continue
          seen.add(cid.lower())
          creator_info.extend(handles)  
      token = search_resp.get("nextPageToken")
      if not token:
        break
    handle=set(creator_info)
    creator_info=list(handle)
  return creator_info

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send'
]
def get_gmail_service():
    creds = None
    # token.json stores the user's access and refresh tokens
    import os
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('gmail_api_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)
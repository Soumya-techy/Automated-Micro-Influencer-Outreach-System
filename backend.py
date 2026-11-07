from langgraph.graph import StateGraph,START,END
from src.tools import instagram_details_finder,instagram_influencer_finder,Youtube_creator_finder,collection1,send_gmail
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import SystemMessage
from typing import TypedDict,Annotated
from langchain_groq import ChatGroq
from uuid import uuid4
import os
from pydantic import BaseModel
from bson import ObjectId
from dotenv import load_dotenv
load_dotenv()
conn=sqlite3.connect('checkpointer.sqlite',check_same_thread=False)
thread=str(uuid4())
config={'configurable':{'thread_id':thread}}
checkpointer=SqliteSaver(conn=conn)

prompt=SystemMessage(content=("You are a professional promotion department head in a company called Somya Enterprises"
"The main business of this company is it sells makeup produt and our company is new in the market"
"As our company is new we are planning to run a promotion campaign where we reach out to influencers to promote our product from their social media handle"
"So your job is draft professional emails to these creators it should be highly personalised not generic it should be based on one of their latest reel caption that is given to you,for eaxmple you can start with we loved your reel about xyz and we would love to collaborate"
"You should ask creators for a barter collab promotion campaign where we will send 3-4 products to creators and they will post 3 reels and 2 stories about our product"
"Return ONLY a JSON object with exactly these keys: {{'to': 'email of the creator', 'subject': 'subject of the mail', 'body': 'body of the email'}}"))

def append_group(old: list, new: list) -> list:
    return old + [new]
class state(TypedDict,total=False):
    raw_urls:Annotated[list[list[str]],append_group]
    profiles:list[dict]

class email_format(BaseModel):
    to:str
    subject:str
    body:str

llm=ChatGroq(model='openai/gpt-oss-120b',
    api_key=os.getenv('GROQ_API_KEY')).with_structured_output(email_format,method='json_mode')

def ig_influencer_finder(state:state):
    return {'raw_urls':instagram_influencer_finder()}

def yt_influencer_finder(state:state):
    return {'raw_urls':Youtube_creator_finder()}

def ig_details_finder(state:state):
    details=instagram_details_finder(url=state['raw_urls'][0])+instagram_details_finder(url=state['raw_urls'][1])
    return {'profiles':details}

def send_promo_email(state:state):
    task=list(collection1.find({"$and":[{'Contacted':False},{'contact':{"$ne":"Not found"}}]},{'_id':1,'full_name':1,'contact':1,'latest_reel_caption':1}))
    for creator in task:
        message=[prompt,f"email of creator: {creator['contact'][0]}, creator name: {creator['full_name']}, latest reel caption: {creator['latest_reel_caption']}"]
        result=llm.invoke(message)
        send_gmail(to=result.to,subject=result.subject,body=result.body)
        collection1.update_one({"_id":ObjectId(creator['_id'])},{"$set":{"Contacted":True}})

graph=StateGraph(state)
graph.add_node("ig_influencer_finder",ig_influencer_finder)
graph.add_node("yt_influencer_finder",yt_influencer_finder)
graph.add_node("ig_details_finder",ig_details_finder)
graph.add_node("send_promo_email",send_promo_email)
graph.add_edge(START,"ig_influencer_finder")
graph.add_edge(START,"yt_influencer_finder")
graph.add_edge("ig_influencer_finder","ig_details_finder")
graph.add_edge("yt_influencer_finder","ig_details_finder")
graph.add_edge("ig_details_finder","send_promo_email")
graph.add_edge("send_promo_email",END)
workflow=graph.compile(checkpointer=checkpointer)
workflow.invoke({},config=config)
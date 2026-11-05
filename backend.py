from langgraph.graph import StateGraph,START,END
from src.tools import instagram_details_finder,instagram_influencer_finder,Youtube_creator_finder,collection1
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import TypedDict,Optional,Annotated
from uuid import uuid4
conn=sqlite3.connect('checkpointer.sqlite',check_same_thread=False)
thread=uuid4()
config={'configurable':{'thread_id':thread}}
checkpointer=SqliteSaver(conn=conn)

def append_group(old: list, new: list) -> list:
    return old + [new]
class state(TypedDict,total=False):
    raw_urls:Annotated[list[list[str]],append_group]
    profiles:list[dict]

def ig_influencer_finder(state:state):
    return {'raw_urls':instagram_influencer_finder()}

def yt_influencer_finder(state:state):
    return {'raw_urls':Youtube_creator_finder()}

def ig_details_finder(state:state):
    details=instagram_details_finder(url=state['raw_urls'][0])+instagram_details_finder(url=state['raw_urls'][1])
    return {'profiles':details}

"""def send_promo_email(state:state):
    task=list(collection1.find({'contacted':False},{'_id':0,'full_name':1,'contact':1,'latest_reel_caption':1}))
    for creator in task:"""
graph=StateGraph(state)
graph.add_node("ig_influencer_finder",ig_influencer_finder)
graph.add_node("yt_influencer_finder",yt_influencer_finder)
graph.add_node("ig_details_finder",ig_details_finder)
graph.add_edge(START,"ig_influencer_finder")
graph.add_edge(START,"yt_influencer_finder")
graph.add_edge("ig_influencer_finder","ig_details_finder")
graph.add_edge("yt_influencer_finder","ig_details_finder")
graph.add_edge("ig_details_finder",END)
workflow=graph.compile(checkpointer=checkpointer)
workflow.invoke({},config=config)
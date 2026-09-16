import json,subprocess,time,re,sys,os
from difflib import SequenceMatcher
OWN="UCYASX2PAaV_7aEX6EPpP8Dg"
OWN_SET={"UCYASX2PAaV_7aEX6EPpP8Dg","UCGbs0tw5UQpzL26nmQ20Bzg","UCJdP64Vdr3lFZt2wi4WJLjA"}
ctx={"context":{"client":{"clientName":"WEB","clientVersion":"2.20240101.00.00","hl":"ja","gl":"JP"}}}
def call(ep,body):
    for i in range(3):
        out=subprocess.run(["curl","-s","--max-time","30","-X","POST",f"https://youtubei.googleapis.com/youtubei/v1/{ep}?prettyPrint=false","-H","Content-Type: application/json","-H","User-Agent: Mozilla/5.0","-d",json.dumps(body)],capture_output=True,text=True).stdout
        try: return json.loads(out)
        except Exception: time.sleep(2)
    return {}
def walk(o,key,acc):
    if isinstance(o,dict):
        if key in o: acc.append(o[key])
        for v in o.values(): walk(v,key,acc)
    elif isinstance(o,list):
        for x in o: walk(x,key,acc)
    return acc
def txt(o):
    if not o: return None
    if 'simpleText' in o: return o['simpleText']
    if 'runs' in o: return ''.join(r.get('text','') for r in o['runs'])
def norm(t):
    t=re.sub(r'【[^】]*】','',t or '')
    t=re.sub(r'[\s　…\.．、。,，!！?？wｗ→⇒「」『』（）()\-ー\"\'\[\]]','',t)
    return t
# 1. channel list
if os.path.exists('own_videos.json'):
    own=json.load(open('own_videos.json'))
else:
    own=[]
    d=call('browse',{**ctx,"browseId":OWN,"params":"EgZ2aWRlb3PyBgQKAjoA"})
    while True:
        for it in walk(d,'videoRenderer',[]):
            if it.get('videoId'): own.append(dict(id=it['videoId'],title=txt(it.get('title')),pub=txt(it.get('publishedTimeText')),views=txt(it.get('viewCountText'))))
        for lu in walk(d,'lockupViewModel',[]):
            vid=lu.get('contentId'); md=lu.get('metadata',{}).get('lockupMetadataViewModel',{})
            if not vid or not md: continue
            title=md.get('title',{}).get('content')
            parts=[p.get('text',{}).get('content') for row in md.get('metadata',{}).get('contentMetadataViewModel',{}).get('metadataRows',[]) for p in row.get('metadataParts',[])]
            own.append(dict(id=vid,title=title,pub=' / '.join(x for x in parts if x),views=None))
        cir=walk(d,'continuationItemRenderer',[])
        toks=[c.get('continuationEndpoint',{}).get('continuationCommand',{}).get('token') for c in cir]
        toks=[t for t in toks if t]
        if not toks: break
        d=call('browse',{**ctx,"continuation":toks[0]})
        if not d: break
        time.sleep(0.3)
    seen=set();own=[v for v in own if not (v['id'] in seen or seen.add(v['id']))]
    json.dump(own,open('own_videos.json','w'),ensure_ascii=False)
print('own videos',len(own),flush=True)
# 2. search each
done={}
if os.path.exists('hits.json'): done=json.load(open('hits.json'))
for i,v in enumerate(own):
    if v['id'] in done: continue
    q=re.sub(r'【[^】]*】','',v['title'] or '').strip()[:60]
    d=call('search',{**ctx,"query":q,"params":"EgIQAQ%3D%3D"})
    hits=[]
    nt=norm(v['title'])
    for r in walk(d,'videoRenderer',[]):
        vid=r.get('videoId'); 
        if not vid or vid==v['id']: continue
        rt=txt(r.get('title')) or ''
        nr=norm(rt)
        ratio=SequenceMatcher(None,nt,nr).ratio()
        prefix = len(nt)>=20 and (nt[:20] in nr or nr[:20] in nt)
        if ratio>=0.72 or prefix:
            ch=r.get('ownerText',{}).get('runs',[{}])[0]
            cid=ch.get('navigationEndpoint',{}).get('browseEndpoint',{}).get('browseId')
            hits.append(dict(id=vid,title=rt,channel=ch.get('text'),channelId=cid,pub=txt(r.get('publishedTimeText')),views=txt(r.get('viewCountText')),ratio=round(ratio,2)))
    done[v['id']]=hits
    if i%20==0:
        json.dump(done,open('hits.json','w'),ensure_ascii=False)
        print(i,len(own),sum(len(x) for x in done.values()),flush=True)
    time.sleep(0.5)
json.dump(done,open('hits.json','w'),ensure_ascii=False)
print('DONE',flush=True)

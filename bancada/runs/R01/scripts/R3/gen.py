import json,copy,sys
src=json.load(open('fixtures/otium_produto.json'))
AW,AH=1800,1000; LR=304/673
def crop(bw,bh,cx=0.435,ch=1.0,cy=None):
    w=bw/bh*ch*AH/AW
    if w>1: w=1; ch=(AW/(bw/bh))/AH
    x=min(max(cx-w/2,0),1-w)
    y=(1-ch)/2 if cy is None else min(max(cy-ch/2,0),1-ch)
    return [round(x,4),round(y,4),round(w,4),round(ch,4)]
def build(fmt,W,H,g):
    els=[]
    for e in src['elements']:
        e=copy.deepcopy(e); d=g[e['id']]
        e['geometry'].update({k:d[k] for k in ('x','y','width','height')})
        if e['type']=='TEXT':
            for k in ('size','line_height','align'):
                if k in d: e['style'][k]=d[k]
        if 'crop' in d: e['crop']=d['crop']
        els.append(e)
    c={"schema_version":"bancada-0.1","layout_id":src['layout_id'],"brand":src['brand'],"_format":fmt,
       "canvas":{"width":W,"height":H,"background":src['canvas']['background']},"elements":els}
    json.dump(c,open(f'runs/R01/candidates/R3/otium_produto__{fmt}.json','w'),ensure_ascii=False,indent=1)
def logo(x,y,w): return dict(x=x,y=y,width=w,height=round(w*LR,2))
F={}
hh=720
F['email_600x1200']=(600,1200,dict(
 hero=dict(x=0,y=0,width=600,height=hh,crop=crop(600,hh)),
 logo=logo(32,764,150),
 headline=dict(x=32,y=870,width=536,height=112,size=48,line_height=1.05),
 selo=dict(x=32,y=1012,width=536,height=34,size=26,line_height=1.15),
 cta=dict(x=32,y=1062,width=536,height=30,size=22,line_height=1.15)))
hh=760
F['post_1080x1350']=(1080,1350,dict(
 hero=dict(x=0,y=0,width=1080,height=hh,crop=crop(1080,hh)),
 logo=logo(60,816,200),
 headline=dict(x=60,y=962,width=760,height=164,size=72,line_height=1.05),
 selo=dict(x=60,y=1154,width=960,height=44,size=34,line_height=1.15),
 cta=dict(x=60,y=1218,width=960,height=36,size=28,line_height=1.15)))
hh=590
F['card_1080x1080']=(1080,1080,dict(
 hero=dict(x=0,y=0,width=1080,height=hh,crop=crop(1080,hh,cy=0.47)),
 logo=logo(60,634,170),
 headline=dict(x=60,y=742,width=640,height=136,size=60,line_height=1.05),
 selo=dict(x=60,y=900,width=960,height=38,size=30,line_height=1.15),
 cta=dict(x=60,y=952,width=960,height=34,size=26,line_height=1.15)))
hh=1040
F['stories_1080x1920']=(1080,1920,dict(
 hero=dict(x=0,y=0,width=1080,height=hh,crop=crop(1080,hh)),
 logo=logo(64,1090,200),
 headline=dict(x=64,y=1224,width=760,height=164,size=72,line_height=1.05),
 selo=dict(x=64,y=1408,width=952,height=44,size=36,line_height=1.15),
 cta=dict(x=64,y=1462,width=952,height=46,size=30,line_height=1.15)))
F['banner_970x250']=(970,250,dict(
 hero=dict(x=0,y=0,width=340,height=250,crop=crop(340,250,ch=0.86,cy=0.47)),
 logo=logo(372,round((250-130*LR)/2,1),130),
 headline=dict(x=546,y=50,width=385,height=82,size=36,line_height=1.05),
 selo=dict(x=546,y=146,width=408,height=24,size=18,line_height=1.15),
 cta=dict(x=546,y=178,width=408,height=24,size=16,line_height=1.15)))
for k in (sys.argv[1:] or F):
    W,H,g=F[k]; build(k,W,H,g); print(k,g['hero']['crop'])

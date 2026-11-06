import sys
from PIL import ImageFont
F={'Archivo':'Archivo-700','Host Grotesk':'HostGrotesk-600','Poppins':'Poppins-400'}
T={'headline':('Archivo',"Jardim das Perdizes, no seu ritmo"),'selo':('Host Grotesk',"3 suítes · 142 m² · 2 vagas"),'cta':('Poppins',"Visite o stand · otiumartefacto.com.br")}
def wrap(id,size,maxw):
    f,t=T[id]; ft=ImageFont.truetype('/home/user/teste_/bancada/fonts/%s.ttf'%F[f],size)
    words=t.split(' '); lines=[];cur=''
    for w in words:
        c=(cur+' '+w).strip()
        if ft.getlength(c)<=maxw or not cur: cur=c
        else: lines.append(cur);cur=w
    lines.append(cur)
    return [(l,round(ft.getlength(l))) for l in lines]
for a in sys.argv[1:]:
    id,s,w=a.split(':'); print(id,s,w,wrap(id,int(s),int(w)))

"""Only run on GitHub: pair original scan OCR by set and number, validate, then match source lectures."""
import argparse,hashlib,json,re,pathlib,sys
from matching import match_references
ROOT=pathlib.Path(__file__).resolve().parents[1];ID='mipeng6';BASE='https://aokid666.github.io/zz-mipeng-2027/'
def dump(name,obj):(ROOT/'data'/name).write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
def norm(t):return re.sub(r'\s+','',t).replace('．','.').replace('。','.').replace('、','.')
def useful(r,p):
 t=r['t'].strip();
 if r['b'][1]>p['height']*.87 and (re.fullmatch(r'\d{1,3}',t) or re.search('配套课程|联系微信|公众号|1931637888',t)):return False
 return r['b'][1]>p['height']*.045 and r['b'][3]<p['height']*.945 and not re.search('全真(?:模拟)?试卷|单项选择题|多项选择题|下列每题给出|在每小题|全部选对|少选得|答题卡|分析题.*小题',t)
def head(r,p,answer=False):
 if r['b'][0]>p['width']*.26:return None
 m=re.match(r'^(\d{1,2})\s*[.．、。，:：]\s*(.*)',r['t'])
 if not m:return None
 no=int(m[1]);rest=m[2].strip()
 if not 1<=no<=38:return None
 if answer and not(re.match(r'[ABCDabcd](?:[^A-Za-z]|$)',rest) or re.match(r'[ABCDabcd]{2,4}(?:[^A-Za-z]|$)',rest) or any(x in rest[:12] for x in ['参考答案','答案要点','答案要','答题要点'])):return None
 return no,rest

def group_pages(pages,answer=False):
 groups=[];expected=1;current=[];first=None;group={}
 for p in pages:
  for r in p['rows']:
   if not useful(r,p):continue
   l={**r,'p':p['page']};h=head(l,p,answer)
   if h and ((h[0]>=expected and h[0]-expected<=2) or (h[0]==1 and expected>=34)):
    if first is not None:group[first]=(current,current[0]['rest'])
    if h[0]==1 and expected>=34:groups.append(group);group={};expected=1
    first=h[0];current=[{**l,'rest':h[1]}];expected=h[0]+1
   elif first is not None:current.append(l)
 if first is not None:group[first]=(current,current[0]['rest'])
 if group:groups.append(group)
 return groups

def refs(rows,pages):
 out=[]
 for pn in dict.fromkeys(r['p'] for r in rows):
  rs=[r for r in rows if r['p']==pn];p=pages[pn-1];x=max(0,min(r['b'][0] for r in rs)-7);y=max(0,min(r['b'][1] for r in rs)-7);right=min(p['width'],max(r['b'][2] for r in rs)+7);bottom=min(p['height'],max(r['b'][3] for r in rs)+7)
  out.append({'page':pn,'b':[round(x,2),round(y,2),round(right-x,2),round(bottom-y,2)]})
 return out

def options(rows,first):
 stem=[first];opts={};field=None
 for l in rows[1:]:
  t=l['t'];ms=list(re.finditer(r'(?<![A-Za-z])([ABCDabcd])[.．、。:：]\s*',t))
  if not ms:
   m=re.match(r'^([ABCDabcd])\s*(?=[\u4e00-\u9fff“])',t)
   if m:ms=[m]
  if ms:
   before=t[:ms[0].start()].strip()
   if before:
    if field:opts[field]+=before
    else:stem.append(before)
   for i,m in enumerate(ms):
    field=m[1].upper()
    if field in opts:opts[field]+='〔重复选项标记〕'
    else:opts[field]=''
    opts[field]+=t[m.end():ms[i+1].start() if i+1<len(ms) else len(t)].strip()
  elif field:opts[field]+=t
  else:stem.append(t)
 return '\n'.join(stem),opts

def quick_keys(page):
 # Independent cross-check using the printed quick-answer page.
 groups=[];current={}
 for row in page['rows']:
  for m in re.finditer(r'(\d{1,2})\s*[.．、。，]\s*([ABCDabcd]{1,4})(?![A-Za-z])',row['t']):
   n=int(m[1]);a=m[2].upper()
   if n==1 and current:groups.append(current);current={}
   if 1<=n<=33:current[n]=a
 if current:groups.append(current)
 return groups

def main():
 a=argparse.ArgumentParser();a.add_argument('--site',type=pathlib.Path,required=True);a.add_argument('--inspect',action='store_true');args=a.parse_args()
 pages=json.loads((ROOT/'data/ocr-pages.json').read_text());qpages=[p for p in pages if p['kind']=='questions' and p['sourcePage']>=7];apages=[p for p in pages if p['kind']=='answers' and p['sourcePage']>=6];qgroups=group_pages(qpages);agroups=group_pages(apages,True);errors=[];qs=[];keys=quick_keys(next(p for p in pages if p['kind']=='answers' and p['sourcePage']==5))
 report={'questionGroups':[list(g) for g in qgroups],'answerGroups':[list(g) for g in agroups],'quickKeyGroups':[len(g) for g in keys]}
 if len(qgroups)!=6 or len(agroups)!=6:errors.append('Expected six complete question/answer groups')
 for s in range(min(len(qgroups),len(agroups))):
  for n in range(1,39):
   if n not in qgroups[s] or n not in agroups[s]:errors.append(f'{s+1}-{n}: missing question or answer');continue
   qr,first=qgroups[s][n];ar,afirst=agroups[s][n];choice=n<=33;stem,opts=options(qr,first) if choice else ('\n'.join([first]+[r['t'] for r in qr[1:]]),{});answer=''
   if choice:
    m=re.match(r'([ABCDabcd]{1,4})(?![A-Za-z])',afirst)
    if m:answer=''.join(sorted(set(m[1].upper())))
    if set(opts)!=set('ABCD') or any(not x or '〔重复选项标记〕' in x for x in opts.values()):errors.append(f'{s+1}-{n}: bad options {opts}')
    if not answer or (n<=16 and len(answer)!=1) or (n>=17 and len(answer)<2):errors.append(f'{s+1}-{n}: invalid answer {afirst}')
    if s<len(keys) and n in keys[s] and answer!=keys[s][n]:errors.append(f'{s+1}-{n}: answer differs from printed key {answer} vs {keys[s][n]}')
   text='\n'.join([afirst]+[r['t'] for r in ar[1:]]);text=re.sub(r'^[ABCDabcd]{1,4}\s*','',text) if choice else text
   q={'id':f'pr-{ID}-'+('choice' if choice else 'written')+f'-{s+1}-{n:02}','bookId':ID,'type':'choice' if choice else 'written','source':'p','moduleIdx':11,'module':'米鹏6套卷','chapter':f'第{s+1}套','chapterTitle':f'第{s+1}套','section':'单项选择题' if n<=16 else '多项选择题' if choice else '材料分析题','no':n,'originalNo':n,'examSet':s+1,'stem':stem,'options':opts,'multi':17<=n<=33,'answer':answer,'qRefs':refs(qr,pages),'keyRefs':refs(ar,pages),'analysis':[{'k':'原书解析' if choice else '原书参考答案','t':text}],'kPages':[],'sPages':[],'mRefs':[],'aPages':[],'aCrops':[],'extractionNote':'扫描版 OCR 文字，疑难字请对照原始题面；原图保持原格式。'}
   qs.append(q)
 report.update(questionCount=len(qs),errors=errors);dump('parse-report.json',report);dump('draft-questions.json',qs)
 print(json.dumps(report,ensure_ascii=False),flush=True)
 if errors or len(qs)!=228:
  if args.inspect:return
  raise RuntimeError('Validation failed; original website must not be changed')
 match_references(qs,args.site)
 manifest=json.loads((ROOT/'data/source-manifest.json').read_text());sha=hashlib.sha256(''.join(p['sha256'] for p in manifest['pdfs']).encode()).hexdigest();manifest['pdfSha256']=sha
 chapters=[{'key':f'米鹏6套卷 · 第{s}套','title':f'第{s}套','count':38,'firstPage':next(q['qRefs'][0]['page'] for q in qs if q['examSet']==s)} for s in range(1,7)]
 parts=[{'firstPage':1,'lastPage':88,'url':manifest['pdfs'][0]['url']},{'firstPage':89,'lastPage':182,'url':manifest['pdfs'][1]['url']}]
 book={'id':ID,'title':'米鹏6套卷','url':parts[0]['url'],'file':'米鹏全真模拟六套卷 · 试题册与解析册','pages':182,'sha256':sha,'count':228,'counts':{'choice':198,'written':30},'chapters':chapters,'kind':'mock','sourceBase':BASE,'pageSizes':[{'width':p['width'],'height':p['height']} for p in pages],'pdfParts':parts,'readSections':[{'title':'解析册 · 第'+str(s)+'套','firstPage':next(q['keyRefs'][0]['page'] for q in qs if q['examSet']==s)} for s in range(1,7)]}
 bank={'bookId':ID,'questions':qs,'pages':[{k:p[k] for k in ['page','width','height','text','kind','sourcePage']} for p in pages]}
 report.update(single=96,multiple=102,written=30,imageCount=182,references={k:sum(bool(q[k]) for q in qs) for k in ['kPages','sPages','mRefs']},pdfSha256=sha)
 dump('book.json',book);dump(ID+'.json',bank);dump('source-manifest.json',manifest);dump('build-report.json',report)
if __name__=='__main__':main()

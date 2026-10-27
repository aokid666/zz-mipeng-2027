"""Supplement missing whole lines with an independent OCR engine; keep original scan bytes."""
import concurrent.futures,csv,io,json,pathlib,re,subprocess,os
os.environ['OMP_THREAD_LIMIT']='1'
ROOT=pathlib.Path(__file__).resolve().parents[1]
def work(p):
 path=ROOT/'img/mipeng6'/f'{p["page"]:03}.png'
 raw=subprocess.check_output(['tesseract',str(path),'stdout','-l','chi_sim+eng','--psm','6','tsv'],stderr=subprocess.DEVNULL,text=True)
 groups={}
 for w in csv.DictReader(io.StringIO(raw),delimiter='\t'):
  if not w.get('text','').strip() or int(w.get('level',0))!=5:continue
  groups.setdefault((w['block_num'],w['par_num'],w['line_num']),[]).append(w)
 extra=[]
 for words in groups.values():
  x=min(int(w['left']) for w in words);y=min(int(w['top']) for w in words);right=max(int(w['left'])+int(w['width']) for w in words);bottom=max(int(w['top'])+int(w['height']) for w in words)
  if any(abs((r['b'][1]+r['b'][3])/2-(y+bottom)/2)<max(9,(bottom-y)*.65) for r in p['rows']):continue
  t=' '.join(w['text'] for w in words).strip()
  for _ in range(2):t=re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])','',t)
  t=re.sub(r'(?<=\d)\s+(?=[.．、])','',t)
  extra.append({'t':t,'b':[x,y,right,bottom],'score':0.0,'engine':'tesseract-supplement'})
 p['rows'].extend(extra);p['rows'].sort(key=lambda r:(round(r['b'][1]/8),r['b'][0]));p['text']='\n'.join(r['t'] for r in p['rows']);p['supplemented']=True
 (ROOT/'data/ocr'/f'{p["page"]:03}.json').write_text(json.dumps(p,ensure_ascii=False));return len(extra)
if __name__=='__main__':
 path=ROOT/'data/ocr-pages.json';pages=json.loads(path.read_text())
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:counts=list(ex.map(work,pages))
 pages=[json.loads(p.read_text()) for p in sorted((ROOT/'data/ocr').glob('*.json'))];path.write_text(json.dumps(pages,ensure_ascii=False));print('Supplemented missing lines:',sum(counts),flush=True)

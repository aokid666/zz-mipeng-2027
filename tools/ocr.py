import os
os.environ['OMP_NUM_THREADS']='1'
import concurrent.futures,hashlib,json,pathlib,urllib.request,fitz
ROOT=pathlib.Path(__file__).resolve().parents[1]
def work(job):
 from rapidocr_onnxruntime import RapidOCR
 kind,pn,globaln=job;doc=fitz.open(ROOT/'pdf'/f'{kind}.pdf');page=doc[pn-1]
 image=max(page.get_images(),key=lambda x:x[2]*x[3]);raw=doc.extract_image(image[0]);assert raw['ext']=='png',raw['ext']
 out=ROOT/'img/mipeng6'/f'{globaln:03}.png';out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw['image'])
 engine=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1);result,_=engine(str(out));rows=[]
 for poly,t,score in result or []:
  xs=[p[0] for p in poly];ys=[p[1] for p in poly];rows.append({'t':t,'b':[min(xs),min(ys),max(xs),max(ys)],'score':float(score)})
 rows.sort(key=lambda l:(round(l['b'][1]/8),l['b'][0]))
 record={'page':globaln,'kind':kind,'sourcePage':pn,'width':raw['width'],'height':raw['height'],'text':'\n'.join(r['t'] for r in rows),'rows':rows,'sha256':hashlib.sha256(raw['image']).hexdigest(),'bytes':len(raw['image']),'ext':'png'}
 dst=ROOT/'data/ocr'/f'{globaln:03}.json';dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(json.dumps(record,ensure_ascii=False));print(f'OCR {kind} {pn} -> {globaln}',flush=True);return globaln
if __name__=='__main__':
 (ROOT/'pdf').mkdir(exist_ok=True);jobs=[];offset=0;manifest=[]
 for kind in ['questions','answers']:
  p=ROOT/'pdf'/f'{kind}.pdf'
  if not p.exists():urllib.request.urlretrieve(f'https://github.com/aokid666/zz-mipeng-2027/releases/download/source-v1/{kind}.pdf',p)
  d=fitz.open(p);manifest.append({'kind':kind,'pages':len(d),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'url':f'https://github.com/aokid666/zz-mipeng-2027/releases/download/source-v1/{kind}.pdf'})
  for i in range(1,len(d)+1):
   n=offset+i
   if not (ROOT/'data/ocr'/f'{n:03}.json').exists():jobs.append((kind,i,n))
  offset+=len(d)
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:list(ex.map(work,jobs))
 records=[json.loads(p.read_text()) for p in sorted((ROOT/'data/ocr').glob('*.json'))];assert len(records)==182
 (ROOT/'data/ocr-pages.json').write_text(json.dumps(records,ensure_ascii=False))
 (ROOT/'data/source-manifest.json').write_text(json.dumps({'id':'mipeng6','pdfs':manifest,'pages':[{k:r[k] for k in ['page','kind','sourcePage','width','height','bytes','sha256','ext']} for r in records]},ensure_ascii=False))

import collections,json,re
def textnorm(t):return re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',t).lower()
def match_references(qs,site):
 docs={k:json.loads((site/'data'/f'lecture-{k}.json').read_text()) for k in ['k','s']}
 docs['m']={p['id']:p['text'] for p in json.loads((site/'data/manual-index.json').read_text())['pages']}
 for kind,pages in docs.items():
  ix=collections.defaultdict(set)
  for key,text in pages.items():
   text=textnorm(text)
   for n in range(len(text)-11):ix[text[n:n+12]].add(key)
  for q in qs:
   query=textnorm(q['stem']+'\n'+'\n'.join(q['options'][k] for k in q['answer'])+(''.join(a['t'] for a in q['analysis'])[:600] if q['type']=='written' else ''));grams={query[n:n+12] for n in range(len(query)-11)};scores=collections.Counter()
   for gram in grams:
    keys=ix.get(gram,())
    if len(keys)<=4:scores.update(keys)
   hits=[key for key,count in scores.most_common(2) if count>=6]
   q[{'k':'kPages','s':'sPages','m':'mRefs'}[kind]]=list(map(int,hits)) if kind!='m' else hits
 for q in qs:q['referenceMethod']='题干与正确选项中的连续相同原文匹配；未匹配资料明确显示没找到，请核对原文语境。'


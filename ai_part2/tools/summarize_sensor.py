import argparse,json
p=argparse.ArgumentParser();p.add_argument('log');a=p.parse_args()
rows=[]
with open(a.log) as f:
 for line in f:
  try:r=json.loads(line)
  except ValueError:continue
  if 'ok' in r:rows.append(r)
if not rows:raise SystemExit('No sensor results; inspect log, not a successful run')
lat=sorted(r['elapsed_ms'] for r in rows)
print(json.dumps({'attempts':len(rows),'success':sum(r['ok'] for r in rows),'failures':sum(not r['ok'] for r in rows),
 'elapsed_ms_median':lat[len(lat)//2], 'elapsed_ms_p95':lat[min(len(lat)-1,int(.95*len(lat)))]},indent=2))

"""Select pair calibration by CV on calibration rows; evaluate holdout once."""
import json
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, cohen_kappa_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

records=json.loads(Path('data/evaluation/matching-calibration-input.json').read_text())['records']
train=[r for r in records if r['split']=='calibration' and r['gold']!='match']
holdout=[r for r in records if r['split']=='holdout']
candidates=[
    ['score','resp'],
    ['score','resp','covered','keyword'],
    ['score','hard','resp','qual','keyword','covered','partial','missing'],
    ['score','hard','resp','qual','keyword','covered','partial','missing','must_covered','must_partial','hard_covered','hard_partial','lexical','semantic'],
]

def matrix(rows, features): return [[r[f] for f in features] for r in rows]
def labels(rows): return [1 if r['gold']=='partial' else 0 for r in rows]
def metrics(rows,pred):
    y=labels(rows); p,r,f,_=precision_recall_fscore_support(y,pred,pos_label=0,average='binary',zero_division=0)
    return {'accuracy':accuracy_score(y,pred),'kappa':cohen_kappa_score(y,pred),
            'mismatch_precision':p,'mismatch_recall':r,'mismatch_f1':f}

cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
options=[]
for features in candidates:
    for c in [.01,.03,.1,.3,1.0]:
        model=make_pipeline(StandardScaler(),LogisticRegression(C=c,class_weight='balanced',random_state=42,max_iter=10000))
        pred=cross_val_predict(model,matrix(train,features),labels(train),cv=cv)
        options.append((metrics(train,pred),features,c))
options.sort(key=lambda x:(x[0]['kappa'],x[0]['mismatch_f1'],x[0]['accuracy']),reverse=True)
for item in options[:8]: print('CV',json.dumps(item))
chosen=options[0]
features,c=chosen[1],chosen[2]
model=make_pipeline(StandardScaler(),LogisticRegression(C=c,class_weight='balanced',random_state=42,max_iter=10000)).fit(matrix(train,features),labels(train))
pred=model.predict(matrix(holdout,features))
print('CHOSEN',features,c)
print('HOLDOUT',metrics(holdout,pred),list(zip([r['pair_number'] for r in holdout],[r['gold'] for r in holdout],['partial' if x else 'mismatch' for x in pred])))
scale=model[0]; lr=model[1]
raw_coef=(lr.coef_[0]/scale.scale_).tolist()
raw_intercept=float(lr.intercept_[0]-(lr.coef_[0]*scale.mean_/scale.scale_).sum())
print('PRODUCTION_JSON',json.dumps({'version':1,'features':features,'coefficients':raw_coef,'intercept':raw_intercept,
      'probability_cutoff':0.5,
      'match_score_floor':(min(r['score'] for r in records if r['gold']=='match') + max(r['score'] for r in train if r['gold']=='partial'))/2,
      'fit_on_pairs':[r['pair_number'] for r in train],
      'holdout_pairs':[r['pair_number'] for r in holdout], 'cv_metrics':chosen[0], 'holdout_metrics':metrics(holdout,pred)},indent=2))

"""Offline exploration only; does not write production thresholds or labels."""
import json
from pathlib import Path
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, cohen_kappa_score

r=json.loads(Path('data/evaluation/matching-calibration-input.json').read_text())['records']
features=['score','hard','resp','qual','keyword','covered','partial','missing','must_covered','must_partial','hard_covered','hard_partial','lexical','semantic']
train=[x for x in r if x['split']=='calibration' and x['gold']!='match']
test=[x for x in r if x['split']=='holdout']
X=lambda z:[[x[f] for f in features] for x in z]
y=lambda z:[x['gold'] for x in z]
for depth in [1,2,3,4]:
    model=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=3,random_state=42,class_weight='balanced').fit(X(train),y(train))
    for name,z in [('train',train),('test',test)]:
        pred=model.predict(X(z))
        print('tree',depth,name,round(accuracy_score(y(z),pred),3),round(cohen_kappa_score(y(z),pred),3),list(zip([x['pair_number'] for x in z],y(z),pred)))
    print(export_text(model,feature_names=features))
for c in [.01,.1,1,10]:
    model=LogisticRegression(C=c,class_weight='balanced',random_state=42,max_iter=10000).fit(X(train),y(train))
    for name,z in [('train',train),('test',test)]:
        pred=model.predict(X(z))
        print('lr',c,name,round(accuracy_score(y(z),pred),3),round(cohen_kappa_score(y(z),pred),3),list(zip([x['pair_number'] for x in z],y(z),pred)))
    print(dict(zip(features,model.coef_[0])),model.intercept_)

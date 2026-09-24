// Run with NODE_PATH pointing to a Playwright installation. Mock writes only;
// the production CSV is never used for browser approval tests.
const { chromium } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const html = fs.readFileSync(require('node:path').join(__dirname,'../api/review_ui.html'),'utf8');
const options = [
  {key:'skills_primary:1',text:'Python',context:'skills_primary',type:'skill',entities:{tech:['Python']}},
  {key:'skills_secondary:1',text:'Docker',context:'skills_secondary',type:'skill',entities:{tech:['Docker']}}
];
function fixture(index){return {
 index, row:{resume_id:String(index+1),jd_id:'job'+index,review_status:'needs_human_review'},
 profile:{skills_primary:['Python'],skills_secondary:['Docker']},job:{title:'Engineer',description:'Python and Docker'},
 origin:'proposal',revision:'initial',fact_options:options,validation_errors:[],rejected:false,
 proposal:{decision:index?'mismatch':'partial',uncertain_reasons:[]},
 seed:{fact_keys:options.map(o=>o.key),decision:index?'mismatch':'partial',confidence:'medium',notes:'',
 requirements:[{req_id:'R01',text:'Python',type:'hard_skill',min_years:0,must_have:true,canonical_skills:['python'],logic:'single'},
 {req_id:'R02',text:'Docker',type:'tool',min_years:0,must_have:false,canonical_skills:['docker'],logic:'single'}],
 matches:[{req_id:'R02',fact_keys:['skills_secondary:1'],status:'covered',method:'lexical',score:.91},
 {req_id:'R01',fact_keys:['skills_primary:1'],status:'partial',method:'semantic',score:.61}]}
}}
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const fixtures=[fixture(0),fixture(1)];const writes=[];
 await page.route('http://review.test/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname;
  if(path==='/review')return route.fulfill({contentType:'text/html',body:html});
  if(path==='/v1/review/pairs')return route.fulfill({json:{total:2,reviewed:fixtures.filter(f=>f.origin==='gold').length,pairs:fixtures.map((f,i)=>({index:i,resume_id:f.row.resume_id,jd_id:f.row.jd_id,status:f.row.review_status}))}});
  const f=fixtures[Number(path.split('/').at(-1))];
  if(req.method()==='PUT'){
    const p=req.postDataJSON();writes.push(p);
    if(p.action==='accept'){f.origin='gold';f.seed=p;f.row.review_status='reviewed_'+p.decision}
    if(p.action==='draft'){f.origin='draft';f.seed=p}
    if(p.action==='reject'){f.rejected=true;f.row.review_status='proposal_rejected'}
    return route.fulfill({json:{ok:true,review_status:f.row.review_status}})
  }
  return route.fulfill({json:f});
 });
 await page.goto('http://review.test/review');await page.locator('[data-req-id="R02"]').waitFor();
 const r1=page.locator('[data-req-id="R01"]'),r2=page.locator('[data-req-id="R02"]');
 assert.equal(await r1.locator('select').nth(2).inputValue(),'partial');
 assert.equal(await r1.locator('select').nth(3).inputValue(),'semantic');
 assert.equal(await r1.locator('input[type=number]').nth(1).inputValue(),'0.61');
 assert.equal(await r2.locator('select').nth(2).inputValue(),'covered');
 assert.equal(await r2.locator('input[type=number]').nth(1).inputValue(),'0.91');
 assert.equal(await r2.locator('input[type=checkbox]').nth(2).isChecked(),true);
 assert.equal(await page.locator('#facts input:checked').count(),2);
 assert.match(await page.locator('#annotationLabel').textContent(),/PROPOSED/);
 assert.equal(writes.length,0);
 await page.click('#next');await page.waitForFunction(()=>document.querySelector('#pairTitle').textContent.includes('Pair 2'));
 assert.equal(await page.locator('input[name=decision]:checked').inputValue(),'mismatch');
 await page.click('#prev');await page.waitForFunction(()=>document.querySelector('#pairTitle').textContent.includes('Pair 1'));
 await page.click('#edit');await r1.locator('textarea').fill('');await page.click('#draft');
 await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('Progress saved'));
 await page.reload();await page.locator('[data-req-id="R01"]').waitFor();
 assert.equal(await page.locator('[data-req-id="R01"] textarea').inputValue(),'');
 assert.equal(await page.locator('[data-req-id="R02"] input[type=number]').nth(1).inputValue(),'0.91');
 await page.click('#edit');await page.locator('[data-req-id="R01"] textarea').fill('Python');
 await page.locator('[data-req-id="R01"] button').click();
 assert.equal(await page.locator('[data-req-id="R02"] select').nth(2).inputValue(),'covered');
 await page.locator('input[name=decision][value=mismatch]').check();await page.click('#accept');
 await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('Accepted'));
 const accepted=writes.at(-1);assert.equal(accepted.action,'accept');assert.equal(accepted.decision,'mismatch');
 assert.equal(accepted.matches[0].req_id,'R02');assert.equal(accepted.matches[0].score,.91);
 assert.deepEqual(accepted.matches[0].fact_keys,['skills_secondary:1']);
 await page.click('#next');await page.waitForFunction(()=>document.querySelector('#pairTitle').textContent.includes('Pair 2'));
 await page.click('#reject');await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('Proposal rejected'));
 assert.equal(writes.at(-1).action,'reject');assert.equal(fixtures[1].origin,'proposal');assert.deepEqual(errors,[]);
 // Read-only live integration: inspect actual proposals, never click ACCEPT.
 if(process.env.REVIEW_LIVE){
  const live=await browser.newPage();await live.goto(process.env.REVIEW_LIVE+'/review');await live.locator('[data-req-id="R01"]').waitFor();
  assert.equal(await live.locator('#facts input:checked').count(),10);
  console.log('Live Pair 1 renders prefilled requirements:',await live.locator('.requirement').count());
  await live.screenshot({path:require('node:path').join(__dirname,'../data/evaluation/review-ui-preview.png'),fullPage:false});
 }
 console.log('Browser checks passed: prefill, ID mapping, score, navigation, draft reload, edit/remove, accept, reject.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

'use strict';
const path = require('path');
const fs = require('fs');
const runtimePath = path.resolve(__dirname,'../frozen_targets/lung/artifacts/methodology_runtime.js');
const Runtime = require(runtimePath);

const artifacts = {
  release:{release_id:'lung-personalization-metamorphic-freeze'},
  contracts:{contracts:[]}, rules:{rules:[]},
  personalization:{mechanisms:[
    {id:'P-LUNG-SPO2-BASELINE',kind:'baseline_delta',value_field:'spo2',baseline_field:'baseline_spo2',output_field:'spo2_baseline_delta'},
    {id:'P-LUNG-FEV1-BASELINE',kind:'baseline_percent_change',value_field:'fev1',baseline_field:'baseline_fev1',output_field:'fev1_baseline_percent_change'}
  ]}
};

let seed=20261012;
function rnd(){ seed=(1664525*seed+1013904223)>>>0; return seed/4294967296; }
function approx(a,b,t=1e-9){ return Math.abs(a-b)<=t; }
function round3(x){ return Number(x.toFixed(3)); }
const configs=[
  {id:'spo2_delta', value:'spo2', base:'baseline_spo2', out:'spo2_baseline_delta', gen:()=>[70+30*rnd(),70+30*rnd()], expected:(v,b)=>round3(v-b)},
  {id:'fev1_percent', value:'fev1', base:'baseline_fev1', out:'fev1_baseline_percent_change', gen:()=>[0.3+4.7*rnd(),0.3+4.7*rnd()], expected:(v,b)=>round3(((v-b)/b)*100)}
];
const perMechanism=250;
let assertions=0, passed=0, cases=0;
const failures=[];
function check(ok, rec){ assertions++; if(ok) passed++; else failures.push(rec); }
for(const cfg of configs){
  for(let i=0;i<perMechanism;i++){
    cases++;
    const [v,b]=cfg.gen();
    const api=Runtime.create(artifacts);
    const unrelated={vq_ratio:0.8+0.2*rnd(), learner_diagnosis:'normal', age_years:18+Math.floor(rnd()*62)};
    api.reset(Object.assign({},unrelated,{[cfg.value]:v,[cfg.base]:b}));
    const s0=api.snapshot();
    const e0=cfg.expected(v,b);
    check(approx(s0[cfg.out],e0),{cfg:cfg.id,i,check:'formula',got:s0[cfg.out],expected:e0});
    check(approx(s0[cfg.value],v)&&approx(s0[cfg.base],b),{cfg:cfg.id,i,check:'source_immutability'});

    // Perturb unrelated context: personalized output must not change.
    api.reset(Object.assign({},unrelated,{vq_ratio:2.2,learner_diagnosis:'copd',age_years:79,[cfg.value]:v,[cfg.base]:b}));
    const su=api.snapshot();
    check(approx(su[cfg.out],e0),{cfg:cfg.id,i,check:'unrelated_noninterference',got:su[cfg.out],expected:e0});

    // Perturb declared baseline: only the personalized derived output should follow the declared formula.
    const b2 = cfg.id==='spo2_delta' ? Math.min(100,b+0.5) : Math.min(5,b+0.05);
    api.reset(Object.assign({},unrelated,{[cfg.value]:v,[cfg.base]:b2}));
    const sd=api.snapshot();
    const ed=cfg.expected(v,b2);
    check(approx(sd[cfg.out],ed),{cfg:cfg.id,i,check:'declared_dependency',got:sd[cfg.out],expected:ed});

    // Remove required baseline: derived personalization must disappear.
    api.reset(Object.assign({},unrelated,{[cfg.value]:v}));
    const sm=api.snapshot();
    check(sm[cfg.out]===undefined,{cfg:cfg.id,i,check:'missing_baseline',got:sm[cfg.out]});
  }
}
const result={study:'personalization_metamorphic_noninterference',seed:20261012,mechanisms:configs.map(c=>c.id),cases,assertions,passed,failed:failures.length,per_mechanism:perMechanism,failures:failures.slice(0,20)};
const out=path.resolve(__dirname,'../data/runs/personalization_metamorphic.json');
fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
if(failures.length) process.exit(1);

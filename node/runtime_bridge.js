#!/usr/bin/env node
'use strict';
const fs=require('fs');
const path=require('path');

function die(msg){ console.error(msg); process.exit(2); }
const repo=process.argv[2];
if(!repo) die('Usage: node runtime_bridge.js /path/to/repo');
require(path.join(repo,'artifacts','artifacts_embed.js'));
const R=require(path.join(repo,'artifacts','methodology_runtime.js'));
if(!global.TWIN_ARTIFACTS) die('TWIN_ARTIFACTS not loaded');
const rt=R.create(global.TWIN_ARTIFACTS);
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const outputs=[];

for(const s of input.steps || []){
  if(s.op==='reset'){
    const state=rt.reset(s.state||{});
    outputs.push({op:'reset',state:state,release_id:rt.releaseId,state_revision:rt.getRevision(),trace:rt.lastTrace()});
  } else if(s.op==='submit_observation'){
    const x=rt.submitObservation(s.observation||{});
    outputs.push(Object.assign({op:'submit_observation'},x,{release_id:rt.releaseId}));
  } else if(s.op==='evaluate_rules'){
    const x=rt.evaluateRules(s.context||{});
    const states={}; for(const r of x.evaluated) states[r.id]=r.result;
    outputs.push({op:'evaluate_rules',rule_states:states,active_rules:x.active.map(r=>r.id),unknown_rules:x.unknown.map(r=>r.id),hard_constraints:x.hard.map(r=>r.id),output_policy:x.output_policy,release_id:rt.releaseId,state_revision:rt.getRevision(),trace:rt.lastTrace()});
  } else if(s.op==='commit_decision'){
    const x=rt.commitDecision(s.event||{type:'cross_implementation'},s.context||{},s.patch||{},s.model_descriptors||[]);
    const states={}; for(const r of x.rule_evaluation.evaluated) states[r.id]=r.result;
    outputs.push({op:'commit_decision',rule_states:states,output_policy:x.output_policy,release_id:rt.releaseId,state_revision:rt.getRevision(),trace:x.trace,state:x.state});
  } else if(s.op==='snapshot'){
    outputs.push(Object.assign({op:'snapshot'},rt.snapshot()));
  } else {
    die('Unknown op '+s.op);
  }
}
process.stdout.write(JSON.stringify({case_id:input.case_id,twin:input.twin,release_id:rt.releaseId,steps:outputs,trace_history:rt.traceHistory()}));

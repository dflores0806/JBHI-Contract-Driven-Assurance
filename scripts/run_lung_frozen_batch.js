#!/usr/bin/env node
'use strict';
const fs=require('fs'); const path=require('path'); const readline=require('readline');
const repo=process.argv[2]; const infile=process.argv[3]; const outfile=process.argv[4];
if(!repo||!infile||!outfile){console.error('Usage: node run_lung_batch.js repo cases.jsonl out.jsonl');process.exit(2)}
require(path.join(repo,'artifacts','artifacts_embed.js'));
const R=require(path.join(repo,'artifacts','methodology_runtime.js'));
const out=fs.createWriteStream(outfile,{encoding:'utf8'});
function run(input){
 const rt=R.create(global.TWIN_ARTIFACTS); const outputs=[];
 for(const s of input.steps||[]){
  if(s.op==='reset'){ const state=rt.reset(s.state||{}); outputs.push({op:'reset',state,release_id:rt.releaseId,state_revision:rt.getRevision(),trace:rt.lastTrace()}); }
  else if(s.op==='submit_observation'){ const x=rt.submitObservation(s.observation||{}); outputs.push(Object.assign({op:'submit_observation'},x,{release_id:rt.releaseId})); }
  else if(s.op==='evaluate_rules'){ const x=rt.evaluateRules(s.context||{}); const states={}; for(const r of x.evaluated) states[r.id]=r.result; outputs.push({op:'evaluate_rules',rule_states:states,active_rules:x.active.map(r=>r.id),unknown_rules:x.unknown.map(r=>r.id),hard_constraints:x.hard.map(r=>r.id),output_policy:x.output_policy,release_id:rt.releaseId,state_revision:rt.getRevision(),trace:rt.lastTrace()}); }
  else if(s.op==='snapshot'){ outputs.push(Object.assign({op:'snapshot'},rt.snapshot())); }
 }
 return {case_id:input.case_id,twin:input.twin,release_id:rt.releaseId,steps:outputs,trace_history:rt.traceHistory(),external_source:input.external_source,external_kind:input.external_kind,source_record_id:input.source_record_id,reference:input.reference||{}};
}
const rl=readline.createInterface({input:fs.createReadStream(infile,{encoding:'utf8'}),crlfDelay:Infinity});
rl.on('line',line=>{if(!line.trim())return; out.write(JSON.stringify(run(JSON.parse(line)))+'\n');});
rl.on('close',()=>out.end());

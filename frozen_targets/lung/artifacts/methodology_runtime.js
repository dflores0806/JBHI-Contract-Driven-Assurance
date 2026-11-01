(function(g){
  'use strict';
  const TRUE='true', FALSE='false', UNKNOWN='unknown';
  function clone(v){ return v == null ? v : JSON.parse(JSON.stringify(v)); }
  function get(obj, path){ if(!path) return undefined; return path.split('.').reduce((acc,k)=>acc != null ? acc[k] : undefined, obj); }
  function exists(v){ return v !== undefined && v !== null && v !== ''; }
  function triNot(v){ return v===UNKNOWN ? UNKNOWN : (v===TRUE ? FALSE : TRUE); }
  function evalCondition(node, ctx){
    if(!node || !node.op) return UNKNOWN;
    const op=node.op;
    if(op==='and'){ let unknown=false; for(const a of (node.args||[])){ const r=evalCondition(a,ctx); if(r===FALSE) return FALSE; if(r===UNKNOWN) unknown=true; } return unknown?UNKNOWN:TRUE; }
    if(op==='or'){ let unknown=false; for(const a of (node.args||[])){ const r=evalCondition(a,ctx); if(r===TRUE) return TRUE; if(r===UNKNOWN) unknown=true; } return unknown?UNKNOWN:FALSE; }
    if(op==='not') return triNot(evalCondition(node.arg,ctx));
    const left=get(ctx,node.field); if(!exists(left)) return UNKNOWN;
    let right=node.value;
    if(op==='eq_field'||op==='neq_field'){ right=get(ctx,node.other); if(!exists(right)) return UNKNOWN; return (op==='eq_field' ? left===right : left!==right) ? TRUE : FALSE; }
    if(op==='contains_field'){ const rv=get(ctx,node.value_field); if(!exists(rv)) return UNKNOWN; if(!Array.isArray(left)) return FALSE; return left.includes(rv)?TRUE:FALSE; }
    if(op==='eq') return left===right?TRUE:FALSE;
    if(op==='neq') return left!==right?TRUE:FALSE;
    if(op==='in') return (node.values||[]).includes(left)?TRUE:FALSE;
    if(op==='lt') return left < right ? TRUE:FALSE;
    if(op==='lte') return left <= right ? TRUE:FALSE;
    if(op==='gt') return left > right ? TRUE:FALSE;
    if(op==='gte') return left >= right ? TRUE:FALSE;
    return UNKNOWN;
  }
  function encodingValid(value, enc){
    if(!enc) return true; const type=typeof enc==='string'?enc:enc.type;
    if(type==='integer') return Number.isInteger(value);
    if(type==='number') return typeof value==='number' && Number.isFinite(value);
    if(type==='boolean') return typeof value==='boolean';
    if(type==='string') return typeof value==='string';
    if(type==='categorical'){ if(typeof value!=='string') return false; return !enc.allowed || enc.allowed.includes(value); }
    return true;
  }
  function validateObservation(contract, obs, activeMeta){
    const failures=[], warnings=[]; if(!contract) return {status:'rejected', failures:['unknown_contract'], warnings};
    if(!Object.prototype.hasOwnProperty.call(obs,'value') || obs.value===undefined || obs.value===null || obs.value===''){ if(contract.requirement==='mandatory') failures.push('missing_value'); else return {status:'missing', failures:[], warnings:[]}; }
    if(failures.length===0 && !encodingValid(obs.value, contract.encoding)) failures.push('invalid_encoding');
    if(contract.unit && obs.unit !== contract.unit) failures.push(obs.unit==null?'missing_unit':'incompatible_unit');
    const dom=contract.admissible_domain;
    if(failures.length===0 && dom && typeof obs.value==='number' && typeof dom==='object' && !Array.isArray(dom)){ if(dom.min != null && obs.value < dom.min) failures.push('below_min'); if(dom.max != null && obs.value > dom.max) failures.push('above_max'); }
    const runtime=contract.runtime||{};
    if(runtime.allowed_sources && runtime.allowed_sources.length){ if(!obs.source || !runtime.allowed_sources.includes(obs.source)) failures.push('disallowed_source'); }
    if(runtime.quality_required && (!obs.quality || obs.quality.valid!==true)) failures.push('quality_failure');
    let acquisitionMs=null;
    if(runtime.requires_acquisition_time){ if(!obs.acquisition_time) failures.push('missing_acquisition_time'); else{ acquisitionMs=Date.parse(obs.acquisition_time); if(Number.isNaN(acquisitionMs)) failures.push('invalid_acquisition_time'); } }
    if(acquisitionMs!=null && runtime.stale_after_ms!=null){ if(Date.now()-acquisitionMs > runtime.stale_after_ms) return {status:'expired',failures:[],warnings:['stale'],acquisitionMs}; }
    const prev=activeMeta && activeMeta[contract.id];
    if(acquisitionMs!=null && prev && prev.acquisitionMs!=null && acquisitionMs < prev.acquisitionMs){ return {status:'accepted_with_warning',failures:[],warnings:['out_of_order_not_active'],acquisitionMs,doNotReplace:true}; }
    if(failures.length) return {status:'rejected',failures,warnings,acquisitionMs};
    return {status:warnings.length?'accepted_with_warning':'accepted',failures,warnings,acquisitionMs};
  }
  function create(artifacts){
    if(!artifacts || !artifacts.release) throw new Error('TWIN_ARTIFACTS not loaded');
    const contracts=artifacts.contracts.contracts||[]; const contractMap=Object.fromEntries(contracts.map(c=>[c.id,c]));
    const rules=(artifacts.rules && artifacts.rules.rules)||[]; const personalizations=(artifacts.personalization && artifacts.personalization.mechanisms)||[];
    let state={}, activeMeta={}, revision=0, lastTrace=null, history=[], seenEventIds=new Set();
    function computePersonalizations(){ for(const p of personalizations){ const value=state[p.value_field], baseline=state[p.baseline_field]; if(value==null || baseline==null){ delete state[p.output_field]; continue; } if(p.kind==='baseline_delta'){ state[p.output_field]=Number((value-baseline).toFixed(3)); }else if(p.kind==='baseline_percent_change'){ state[p.output_field]=baseline===0?null:Number((((value-baseline)/baseline)*100).toFixed(3)); } } }
    function makeTrace(event, opts={}){ const trace={trace_id:`${artifacts.release.release_id}:r${revision}:${Date.now()}`,release_id:artifacts.release.release_id,state_revision:revision,event:clone(event),contract_ids:clone(opts.contract_ids||[]),observation_status:opts.observation_status||null,observation_failures:clone(opts.observation_failures||[]),rules_evaluated:clone(opts.rules_evaluated||[]),active_rules:clone(opts.active_rules||[]),unknown_rules:clone(opts.unknown_rules||[]),hard_constraints:clone(opts.hard_constraints||[]),output_policy:opts.output_policy||'informative',model_descriptors:clone(opts.model_descriptors||[]),personalization_outputs:Object.fromEntries(personalizations.map(p=>[p.output_field,state[p.output_field]]).filter(([,v])=>v!==undefined)),timestamp:new Date().toISOString()}; lastTrace=trace; history.push(clone(trace)); return trace; }
    function reset(initialState={}, meta={}){ state=clone(initialState)||{}; activeMeta={}; seenEventIds=new Set(); revision=1; computePersonalizations(); makeTrace({type:meta.event_type||'reset', source:meta.source||'internal'}, {output_policy:'informative'}); return snapshot(); }
    function commitPatch(event, patch={}, opts={}){ const prevRevision=revision; Object.assign(state, clone(patch)||{}); computePersonalizations(); revision++; const trace=makeTrace(event, opts); trace.previous_state_revision=prevRevision; return {state:snapshot(),trace:clone(trace)}; }
    function submitObservation(obs){ const contract=contractMap[obs.contract_id]; if(obs.event_id && seenEventIds.has(obs.event_id)){ const opts={contract_ids:contract?[contract.id]:[],observation_status:'accepted_with_warning',observation_failures:[],output_policy:'informative'}; makeTrace({type:'observation',contract_id:obs.contract_id,event_id:obs.event_id,duplicate:true},opts); return {observation_status:'accepted_with_warning',failures:[],warnings:['duplicate_ignored'],state_revision:revision,state:snapshot(),trace:clone(lastTrace),state_effect:'duplicate_ignored'}; }
      const val=validateObservation(contract,obs,activeMeta); const opts={contract_ids:contract?[contract.id]:[],observation_status:val.status,observation_failures:val.failures||[],output_policy:val.status==='rejected'?'blocked':'informative'};
      if(val.status==='accepted' || val.status==='accepted_with_warning'){ if(obs.event_id) seenEventIds.add(obs.event_id); if(!val.doNotReplace){ state[contract.id]=clone(obs.value); activeMeta[contract.id]={acquisitionMs:val.acquisitionMs,source:obs.source,event_id:obs.event_id||null}; computePersonalizations(); revision++; } makeTrace({type:'observation',contract_id:obs.contract_id,event_id:obs.event_id||null},opts); } else { makeTrace({type:'observation',contract_id:obs.contract_id,event_id:obs.event_id||null},opts); }
      return {observation_status:val.status,failures:val.failures||[],warnings:val.warnings||[],state_revision:revision,state:snapshot(),trace:clone(lastTrace),state_effect:val.doNotReplace?'history_only':(val.status==='accepted'||val.status==='accepted_with_warning'?'active_state_updated':'active_state_unchanged')}; }
    function evaluateRules(contextOverride={}){ const ctx=Object.assign({}, state, clone(contextOverride)||{}); const evaluated=rules.map(r=>({id:r.id,type:r.type,category:r.category,priority:r.priority||0,result:evalCondition(r.condition,ctx),consequence:clone(r.consequence)})); const active=evaluated.filter(r=>r.result===TRUE).sort((a,b)=>a.priority-b.priority); const unknown=evaluated.filter(r=>r.result===UNKNOWN); const hard=active.filter(r=>r.type==='hard'); return {context:ctx,evaluated,active,unknown,hard,output_policy:hard.length?'blocked':'advisory'}; }
    function commitDecision(event, context, patch={}, modelDescriptors=[]){ const re=evaluateRules(context); const result=commitPatch(event,patch,{rules_evaluated:re.evaluated.map(r=>({id:r.id,result:r.result})),active_rules:re.active.map(r=>r.id),unknown_rules:re.unknown.map(r=>r.id),hard_constraints:re.hard.map(r=>r.id),output_policy:re.output_policy,model_descriptors:modelDescriptors}); return Object.assign(result,{rule_evaluation:re,output_policy:re.output_policy}); }
    function snapshot(){ return clone(state); } function lastTraceFn(){ return clone(lastTrace); } function traceHistory(){ return clone(history); } function getRevision(){ return revision; }
    return {releaseId:artifacts.release.release_id,reset,commitPatch,submitObservation,evaluateRules,commitDecision,snapshot,lastTrace:lastTraceFn,traceHistory,getRevision,contractMap};
  }
  const api={create,evalCondition,TRUE,FALSE,UNKNOWN}; g.TwinMethodologyRuntime=api; if(typeof module!=='undefined') module.exports=api;
})(typeof window!=='undefined'?window:globalThis);

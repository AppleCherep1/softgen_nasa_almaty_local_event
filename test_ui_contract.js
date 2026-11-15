// Headless JavaScript contract checks; this is not visual browser QA.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/crew-heart-check.html','utf8');
const start=html.indexOf('const Local = (()=>{'),end=html.indexOf('/* ---------- events ---------- */',start);
const listeners={},calls=[],logs=[];
let requestText='';
const context={
 location:{protocol:'http:',hostname:'127.0.0.1'},
 S:{lang:'ru',profile:'A',phase:'transit',link:true,aid:null,alerts:[],tab:'home'},
 document:{getElementById:()=>null,querySelector:()=>null,addEventListener:(event,fn)=>(listeners[event]??=[]).push(fn)},
 setTimeout:()=>0,performance:{now:()=>0},linkActive:()=>false,
 t:x=>x,esc:x=>String(x),logEv:(...x)=>logs.push(x),renderAll:()=>{},
 Voice:{_handle:()=>{throw Error('Unconfirmed text reached command parser')},heardText:()=>{}},
 fetch:async(path,opts)=>{
  calls.push(path);
  let data;
  if(path==='/health')data={stt:{ru:false},stt_status:{ru:'not_installed'},llm:{ready:true,status:'ready',model:'qwen3:4b'}};
  else if(path==='/session')data={session_id:'s42'};
  else if(path==='/extract'){
   requestText=JSON.parse(opts.body).text;
   data={proposal_id:3,status:'awaiting_confirmation',facts:[{field:'responsive',value:'no',evidence:'не отвечает'}],guard_warnings:[{field:'normal_breathing',value:'unknown',evidence:'дышит',reason:'breath'}],ms:5};
  }else if(path==='/confirm')data={status:'needs_clarification'};
  else throw Error('Unexpected request '+path);
  return {ok:true,json:async()=>data};
 }
};
vm.createContext(context);vm.runInContext(html.slice(start,end)+'\nglobalThis.Local=Local;',context);
async function flush(){for(let i=0;i<6;i++)await new Promise(setImmediate);}
(async()=>{
 context.Local._set({stt:{ru:false},stt_status:{ru:'not_installed'},llm:{ready:true,status:'ready',model:'qwen3:4b'}});
 assert(context.Local.badge().includes('не установлено'));
 const input={value:'Он не отвечает, но дышит'};
 const form={matches:()=>true,querySelector:()=>input};
 listeners.submit[0]({target:form,preventDefault:()=>{}});
 await flush();
 assert.equal(requestText,'Он не отвечает, но дышит');
 assert.equal(context.S.aid,null,'Unconfirmed text changed emergency screen');
 assert(context.Local.card().includes('af_normal_breathing_unknown'));
 const button={dataset:{ai:'ok'}};
 for(const fn of listeners.click)fn({target:{closest:()=>button}});
 await flush();
 assert(calls.includes('/confirm'));
 assert.equal(context.S.aid,'ask2','Unknown breathing did not route to clarification');
 context.S.aid='b2';context.Local._apply({responsive:'no',normal_breathing:'yes'});
 assert.equal(context.S.aid,'b2','Confirmation lowered the existing emergency screen');
 assert(!html.includes('handle(txt.toLowerCase()); paintBar(); Local.extract(txt)'));
 assert(!html.includes('Voice._handle(txt); Voice.heardText(txt); extract(txt)'));
 assert(!html.includes('fonts.googleapis.com'));
 assert(html.includes('m?L.aidUMicro:L.aidUList'));
 console.log('UI contract checks passed: confirmation gate, guard display, health states, no automatic downgrade, microgravity branch.');
})().catch(e=>{console.error(e);process.exit(1);});

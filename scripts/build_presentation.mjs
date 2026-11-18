import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const build=path.join(root,'.presentation-build');
const skill=process.env.CLIPAGENT_PRESENTATION_SKILL;
const runtime=process.env.CLIPAGENT_ARTIFACT_RUNTIME;
if(!skill || !runtime) throw new Error('Set CLIPAGENT_PRESENTATION_SKILL and CLIPAGENT_ARTIFACT_RUNTIME; see docs/ARTIFACT_BUILD.md');
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(build,'node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href).catch(async()=>await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href));
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(build,{recursive:true});
await fs.mkdir(path.join(root,'deliverables'),{recursive:true});
const evidence=JSON.parse(await fs.readFile(path.join(root,'evaluation/results/results.json'),'utf8'));
const summary=evidence.summary;
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={bg:'#0B1424',fg:'#F1F5FC',muted:'#ADBCD2',blue:'#75A9FF',cyan:'#67DDD0',line:'#30445F',amber:'#F0BD75',panel:'#14253C'};
function txt(s,t,x,y,w,h,size=28,color=C.fg,bold=false){const z=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});z.text=t;z.text.style={fontFamily:'Arial',fontSize:size,color,bold};return z;}
function slide(title,notes){const s=p.slides.add();s.background.fill=C.bg;txt(s,title,64,51,1152,85,46,C.fg,true);txt(s,'ClipAgent   /   COMP7608B   /   Group 59',64,671,950,24,16,C.muted);txt(s,String(p.slides.items.length).padStart(2,'0'),1160,669,56,28,18,C.blue);s.speakerNotes.text=notes;return s;}
function para(s,label,body,x,y,w=520){txt(s,label,x,y,w,42,29,C.blue,true);txt(s,body,x,y+53,w,135,27,C.muted);}
function box(s,title,body,x,y,w=330,h=135){const z=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:C.panel,line:{fill:C.line,width:1.5}});txt(s,title,x+20,y+17,w-40,36,27,C.fg,true);txt(s,body,x+20,y+60,w-40,h-65,22,C.muted);return z;}
function link(s,a,b,fromSide='right',toSide='left'){s.shapes.connect(a,b,{kind:'elbow',fromSide,toSide,line:{fill:C.blue,width:2},tail:{type:'arrow',width:'med',length:'med'}});}
function table(s,values,widths){const t=s.tables.add({rows:values.length,columns:values[0].length,left:64,top:205,width:1152,height:330,columnWidths:widths,values});t.borders.assign({fill:C.line,width:1});for(let r=0;r<values.length;r++)for(let c=0;c<values[r].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?C.panel:C.bg;cell.text.style={fontFamily:'Arial',fontSize:r===0?24:28,color:r===0?C.blue:C.fg,bold:r===0};}return t;}
let s=slide('ClipAgent','Introduce the implemented local demo as a rule-based autonomous video-editing controller with pretrained ASR. Team names verified against the local Group 59 proposal PDF. Do not describe proposed LLM orchestration as delivered.');
txt(s,'Evidence-grounded\nvideo editing',64,192,1100,180,69,C.fg,true);
txt(s,'A local editor with source-linked timelines and export checks',68,407,1100,65,30,C.muted);
txt(s,'Gao Xuefei   ·   Wang Ling   ·   Zhang Yiqun   ·   Fu Xuanyu',68,562,1120,42,25,C.blue);
s=slide('User scope and editing contract','The proposal targets 1–3 English lecture, interview or software-demo MP4s totaling 5–15 minutes. The delivered demo accepts 1–3 MP4s and includes short generated sample media. Do not imply that the proposal-scale workload has been evaluated. Sources: README.md, app.py, local proposal section 2.');
para(s,'INPUT','1–3 English MP4 source files\nA brief with topics, duration and aspect ratio',64,190);
para(s,'OUTPUT','MP4, SRT subtitles, editable JSON timeline and a verification report',680,190);
txt(s,'Example brief',64,412,1000,42,26,C.blue,true);
txt(s,'“Create a 25–40 second vertical recap covering the problem, solution and demonstration result.”',64,467,1130,115,37,C.fg);
txt(s,'Proposal target: 5–15 minutes of source footage. Current demonstration: short synthetic sources.',64,611,1150,43,21,C.muted);
s=slide('Implemented architecture','Read the top row from user to controller. The controller calls pretrained faster-whisper ASR, lexical planning, FFmpeg rendering and export verification. SQLite stores jobs, transcripts, timelines and events. Revisions reuse cached transcripts. Sources: app.py, clipagent/service.py, planning.py, media.py, storage.py. No LLM planner, LangGraph, MCP, VLM or preference memory is implemented.');
const ui=box(s,'Browser workbench','Brief, timeline, evidence',64,175,330,120);
const api=box(s,'FastAPI','Upload and job endpoints',474,175,330,120);
const ctl=box(s,'Controller','State and bounded repair',884,175,330,120);link(s,ui,api);link(s,api,ctl);
const asr=box(s,'Pretrained ASR','Speech with timestamps',64,365,330,120);
const plan=box(s,'Lexical planner','Source-linked clip selection',474,365,330,120);
const media=box(s,'Render + verify','FFmpeg, MP4 and SRT',884,365,330,120);link(s,asr,plan);link(s,plan,media);link(s,ctl,media,'bottom','top');
txt(s,'Controller invokes the analysis, planning and media stages',64,515,1120,40,26,C.muted);
txt(s,'SQLite + local files',64,578,330,40,27,C.cyan,true);txt(s,'Jobs, cached transcripts, timeline state and activity history',410,579,790,60,25,C.muted);
s=slide('Decision and recovery policy','Lexical ranking uses weighted token overlap and a phrase bonus. The service allows at most three render attempts, hence up to two duration repairs. Repair removes optional material or adds unused source speech. Manual timelines skip automatic duration repair. Missing requirements produce needs_review, while decoding errors cause failed. Source: clipagent/planning.py and service.py.');
para(s,'01  Select evidence','Rank spoken cues against requested topics. Preserve source IDs and timestamps.',64,178);
para(s,'02  Check the export','Validate timeline bounds, then inspect decoding, duration, aspect, audio and subtitle timing.',680,178);
para(s,'03  Repair within a bound','At most two duration repairs. Remove optional clips or add unused speech.',64,405);
para(s,'04  Report unresolved needs','Recheck retained speech after edits. Flag missing requirements for review.',680,405);
s=slide('Delivered work','Describe the working editor and exported artifacts. Follow-up instructions reuse the transcript, but this is job state rather than cross-session preference memory. Source: README.md, web/app.js, app.py, clipagent/storage.py and service.py. The benchmark is a separate component test and does not prove end-to-end media quality.');
txt(s,'An editable local workflow',64,182,1100,62,40,C.blue,true);
txt(s,'Source preview and frame thumbnails\nTimeline insertion, split, trim and reorder\nFollow-up edits using cached transcripts\nLive execution events and explicit review flags',64,280,1100,250,34,C.fg);
txt(s,'Downloadable MP4 + SRT + timeline JSON + report JSON',64,586,1130,60,29,C.cyan);
s=slide('Evaluation protocol','The evaluation uses 18 synthetic transcript-and-interval fixtures, with 14 feasible cases and four expected failures. An independent interval oracle scores requirement coverage. Compare chronological selection, lexical planner, and planner plus bounded repair. Timing uses 20 repeats after one warmup per case/method. Scope excludes ASR, media rendering, API and persistence. No human study has been conducted. Sources: evaluation/run.py, cases.json and results/results.json.');
txt(s,'18',64,178,250,125,100,C.blue,true);txt(s,'synthetic component cases',340,205,830,70,40,C.fg,true);
txt(s,'14 feasible cases + 4 expected failures',340,279,850,53,29,C.muted);
para(s,'Controlled comparison','Chronological baseline\nLexical planner\nPlanner with bounded repair',64,389);
para(s,'Independent scoring','Annotated acceptable intervals\nConstraint and ordering checks\n20 timing repeats after warmup',680,389);
txt(s,'Simulated duration observations. No ASR, rendering, API, persistence or human scores.',64,614,1140,38,22,C.amber);
s=slide('Planning improves fixture coverage','Report the exact synthetic component results. Coverage is the aggregate fraction of annotated content requirements met, not human quality. Feasible pass counts require all scored constraints. False-complete is a diagnostic mismatch between production reporting and the independent oracle. All three methods flag all four expected failures. Source: evaluation/results/results.json generated '+evidence.metadata.generated_utc+'.');
const methods=[['Chronological','chronological'],['Planner','planner'],['Planner + repair','planner_repair']];
table(s,[['Method','Feasible passes','Coverage','False-complete'],...methods.map(([n,k])=>[n,`${summary[k].feasible_passes}/${summary[k].feasible_cases}`,`${(summary[k].requirement_coverage*100).toFixed(1)}%`,`${summary[k].false_complete}`])],[360,260,240,292]);
txt(s,'All methods flagged 4/4 expected failures.',64,562,1130,44,29,C.cyan);
txt(s,'18 synthetic cases. Coverage measures annotated requirements, not perceived video quality.',64,615,1150,40,22,C.muted);
s=slide('Regression-driven repair improvement','The challenging_repair_order fixture exposed loss of the first-topic constraint after adding context. repair_duration now restores the requested first topic, and the regression test checks duration and ordering together. Current results have 10/14 feasible passes with repair and two false-complete cases. Sources: evaluation results, tests/test_evaluation.py, planning.py.');
para(s,'Before repair','Requested order preserved\nDuration below target',64,190);
para(s,'After the fix','Duration meets target\nRequested order preserved',680,190);
txt(s,'A passing media check does not prove the edit satisfies the brief.',64,422,1120,118,42,C.fg,true);
txt(s,'Regression test: check the duration and first-topic constraint together.',64,572,1140,65,28,C.cyan);
s=slide('Limitations and proposal boundary','Be explicit about the gap between proposal and delivery. Current selection is lexical, with weaknesses for paraphrases, negation and visual-only content. No human quality evaluation or broad benchmark is available. LLM planning, LangGraph, MCP tools, VLM grounding, cross-session preference memory and learned planner experiments remain proposed. Sources: README.md, docs/PLAN.md, implementation and evaluation fixtures.');
para(s,'Current limitations','Lexical matching misses meaning.\nSpeech evidence cannot verify visuals.\nMerged clips can violate topic order.',64,190);
para(s,'Proposed, not implemented','LLM planner, LangGraph and MCP\nVLM or embedding retrieval\nCross-session preference memory',680,190);
txt(s,'Next evidence needed',64,439,1100,45,29,C.blue,true);
txt(s,'Real consented video tasks, end-to-end measurements and independent human ratings before claiming editing quality.',64,498,1120,122,37,C.fg);
s=slide('Live demonstration','Open the local workbench at http://127.0.0.1:8765. Run sample edit, inspect source-linked clips and Checks, then revise to put solution first and inspect the cached-transcript event. Demonstrate a manual trim only if time permits and inspect evidence again. Download the four artifacts. If processing takes longer than the slot, open an existing completed job and clearly identify it as prepared. Source: app.py, web/app.js and README.md.');
txt(s,'01   Run the prepared sample edit',64,185,1130,62,36,C.fg);
txt(s,'02   Inspect source evidence and export checks',64,280,1130,62,36,C.fg);
txt(s,'03   Revise: “Put solution first”',64,375,1130,62,36,C.fg);
txt(s,'04   Download the video and supporting artifacts',64,470,1130,62,36,C.fg);
txt(s,'localhost:8765',64,585,1100,61,39,C.cyan,true);
// Scientific mechanism figures remain editable native shapes and connectors.
const figures=JSON.parse(await fs.readFile(path.join(root,'docs/figures/figures.json'),'utf8'));
for(const f of figures){
  const a=p.slides.add();a.background.fill='#FFFFFF';
  txt(a,f.title,64,48,1150,80,42,'#152C46',true);
  txt(a,'ClipAgent  /  Mechanisms and evaluation',64,674,1000,24,16,'#516477');
  txt(a,String(p.slides.items.length),1160,674,50,24,16,'#245FA5');
  a.speakerNotes.text=f.caption+'\nSource: '+f.source;
  for(const o of f.items){
    if(o.kind==='text')txt(a,o.text,64+o.x,145+o.y-o.size,1120-o.x,o.size+15,o.size,o.color);
    else if(o.kind==='rect')a.shapes.add({geometry:'rect',position:{left:64+o.x,top:145+o.y,width:o.w,height:o.h},fill:o.fill,line:{fill:o.stroke,width:1.3}});
    else {
      const point=(x,y)=>a.shapes.add({geometry:'rect',position:{left:64+x-1,top:145+y-1,width:2,height:2},fill:'none',line:{fill:'none',width:0}});
      a.shapes.connect(point(o.x1,o.y1),point(o.x2,o.y2),{kind:'straight',line:{fill:o.color,width:2},tail:{type:'arrow',width:'med',length:'med'}});
    }
  }
}
await fs.writeFile(path.join(build,'evidence-snapshot.json'),JSON.stringify(evidence,null,2));
for(const [i,s] of p.slides.items.entries()){await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await (await p.export({slide:s,format:'png',scale:1})).arrayBuffer()));}
const candidate=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
const finalPath=path.join(root,'deliverables',process.env.PRESENTATION_NAME||'ClipAgent_Academic.pptx');
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,pythonExecutable:path.join(runtime,'python/bin/python3'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','7'],explicitTotalSlideCount:16,requiredNativeTableOwnerSlides:[7],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation-academic.json')});
// PDF companion uses scripts/build_slide_pdf.py because this runtime lacks a standard-font module.
console.log(JSON.stringify({finalPath,result},null,2));

"""Builds the DreamDesk web apps: small, local, stateful single pages (no network, nothing stored).
Each app is a JS body using _lib.js (S = state, R() = redraw). Run: python3 dreamdesk/webapps/build.py
"""
from pathlib import Path

HERE = Path(__file__).parent
HEAD = (HERE / "_head.html").read_text()

APPS = {}

APPS["todo"] = ("Tasks", r"""
app({items:[{t:"Buy milk",d:false},{t:"Call Sam",d:true}], f:"All", dlg:null, n:""}, () => {
  const vis = S.items.filter(i => S.f=="All" || (S.f=="Done")==i.d);
  return `<h1>Tasks</h1>${tabs("f",["All","Open","Done"])}
  <ul>${vis.map((i,k)=>`<li>${i.d?"Done":"Open"}: ${i.t} <button onclick="S.items[${S.items.indexOf(i)}].d=!S.items[${S.items.indexOf(i)}].d;R()">${i.d?"Reopen":"Complete"} ${i.t}</button> <button onclick="S.items.splice(${S.items.indexOf(i)},1);R()">Delete ${i.t}</button></li>`).join("")}</ul>
  <p>${S.items.filter(i=>!i.d).length} open</p>
  <button onclick="set('dlg','add')">New task</button> <button onclick="S.items=S.items.filter(i=>!i.d);R()">Clear completed</button>
  ${S.dlg=="add"?dialog("New task", field("Title","n")+`<button onclick="S.items.push({t:S.n||'Untitled',d:false});S.n='';S.dlg=null;R()">Add</button>`):""}`;
});""")

APPS["notes"] = ("Notes", r"""
app({notes:["Groceries","Ideas"], open:null, body:{Groceries:"eggs",Ideas:""}, pin:{}, m:false, dlg:null, q:""}, () => {
  if (S.open!=null) { const n=S.open; return `<h1>${n}</h1><button onclick="set('open',null)">Back</button>
    <textarea aria-label="Note body" oninput="S.body['${n}']=this.value">${esc(S.body[n]||"")}</textarea>
    ${menu("m","Note options",[["Pin",`S.pin['${n}']=true`],["Unpin",`S.pin['${n}']=false`],["Delete note",`S.notes=S.notes.filter(x=>x!='${n}');S.open=null`]])}
    <p>${S.pin[n]?"Pinned":"Not pinned"}</p>`; }
  return `<h1>Notes</h1>${field("Search notes","q")}<button onclick="R()">Search</button>
  <ul>${S.notes.filter(n=>n.toLowerCase().includes((S.q||"").toLowerCase())).map(n=>`<li><button onclick="set('open','${n}')">${S.pin[n]?"📌 ":""}${n}</button></li>`).join("")}</ul>
  <button onclick="S.notes.push('Note '+(S.notes.length+1));R()">New note</button><p>${S.notes.length} notes</p>`;
});""")

APPS["shop"] = ("Shop", r"""
const P={Lamp:20,Mug:8,Chair:45,Plant:12};
app({page:"Catalog", cart:{}, ship:"Standard", done:false}, () => {
  const n=Object.values(S.cart).reduce((a,b)=>a+b,0), tot=Object.entries(S.cart).reduce((a,[k,v])=>a+P[k]*v,0)+(S.ship=="Express"?10:0);
  let body="";
  if (S.page=="Catalog") body=`<ul>${Object.keys(P).map(k=>`<li>${k} $${P[k]} <button onclick="S.cart['${k}']=(S.cart['${k}']||0)+1;R()">Add ${k} to cart</button></li>`).join("")}</ul>`;
  if (S.page=="Cart") body=n?`<ul>${Object.entries(S.cart).filter(([k,v])=>v).map(([k,v])=>`<li>${k} × ${v} <button onclick="S.cart['${k}']--;R()">Remove one ${k}</button></li>`).join("")}</ul><p>Total $${tot}</p><button onclick="set('page','Checkout')">Checkout</button>`:"<p>Your cart is empty</p>";
  if (S.page=="Checkout") body=S.done?"<h2>Order placed</h2><button onclick=\"S.cart={};S.done=false;set('page','Catalog')\">Continue shopping</button>":
    `<fieldset><legend>Shipping</legend>${["Standard","Express"].map(s=>`<label><input type="radio" name="s" ${S.ship==s?"checked":""} onchange="set('ship','${s}')">${s}</label>`).join("")}</fieldset><p>Total $${tot}</p><button onclick="set('done',true)">Place order</button>`;
  return `<h1>Shop</h1>${tabs("page",["Catalog","Cart","Checkout"])}<p>Cart (${n})</p>${body}`;
});""")

APPS["settings"] = ("Settings", r"""
app({sec:"General", dark:false, notif:true, sound:true, vol:"Medium", lang:"English", adv:false, dlg:null}, () => {
  let b="";
  if (S.sec=="General") b=`${check("Dark mode","dark")}<label>Language <select aria-label="Language" onchange="set('lang',this.value)">${["English","Español","Deutsch"].map(l=>`<option ${S.lang==l?"selected":""}>${l}</option>`).join("")}</select></label>`;
  if (S.sec=="Notifications") b=`${check("Allow notifications","notif")}${S.notif?check("Play sound","sound"):"<p>Notifications are off</p>"}`;
  if (S.sec=="Sound") b=`<p>Volume: ${S.vol}</p>${["Low","Medium","High"].map(v=>`<button aria-pressed="${S.vol==v}" onclick="set('vol','${v}')">${v}</button>`).join("")}`;
  if (S.sec=="About") b=`<p>Version 2.1</p><button onclick="tog('adv')">${S.adv?"Hide":"Show"} advanced</button>${S.adv?`<button onclick="set('dlg','reset')">Reset all settings</button>`:""}`;
  return `<h1>Settings</h1><nav aria-label="Sections">${["General","Notifications","Sound","About"].map(s=>`<button aria-current="${S.sec==s}" onclick="set('sec','${s}')">${s}</button>`).join("")}</nav><h2>${S.sec}</h2>${b}
  ${S.dlg?dialog("Reset settings?",`<button onclick="S.dark=false;S.notif=true;S.sound=true;S.vol='Medium';S.lang='English';S.dlg=null;R()">Reset</button>`):""}`;
});""")

APPS["calendar"] = ("Calendar", r"""
const M=["January","February","March","April"];
app({m:0, view:"Month", sel:null, ev:{"0-3":["Dentist"],"1-14":["Party"]}, dlg:null, t:""}, () => {
  const days=[...Array(28).keys()].map(d=>d+1), key=d=>`${S.m}-${d}`;
  const grid=S.view=="Month"?`<table aria-label="${M[S.m]}"><tr>${days.map(d=>`<td><button aria-pressed="${S.sel==d}" onclick="set('sel',${d})">${d}${(S.ev[key(d)]||[]).length?" •":""}</button></td>`).join("")}</tr></table>`:
    `<ul>${Object.entries(S.ev).filter(([k])=>k.startsWith(S.m+"-")).map(([k,v])=>`<li>${M[S.m]} ${k.split("-")[1]}: ${v.join(", ")}</li>`).join("")||"<li>No events</li>"}</ul>`;
  return `<h1>Calendar</h1><button onclick="set('m',Math.max(0,S.m-1))">Previous month</button><h2>${M[S.m]}</h2><button onclick="set('m',Math.min(3,S.m+1))">Next month</button>
  ${tabs("view",["Month","Agenda"])}${grid}
  ${S.sel?`<p>Selected ${M[S.m]} ${S.sel}: ${(S.ev[key(S.sel)]||["nothing"]).join(", ")}</p><button onclick="set('dlg','new')">Add event</button>`:""}
  ${S.dlg?dialog("New event",field("Event name","t")+`<button onclick="(S.ev['${S.m}-${S.sel}']=S.ev['${S.m}-${S.sel}']||[]).push(S.t||'Event');S.t='';S.dlg=null;R()">Save event</button>`):""}`;
});""")

APPS["kanban"] = ("Board", r"""
const COLS=["To do","Doing","Done"];
app({cards:[{t:"Design",c:0},{t:"Build",c:0},{t:"Test",c:1}], open:null, dlg:null, n:""}, () => {
  const card=(x,i)=>`<li><button onclick="set('open',${i})">${x.t}</button>${S.open===i?`<div role="group" aria-label="Move ${x.t}">${x.c>0?`<button onclick="S.cards[${i}].c--;S.open=null;R()">Move left</button>`:""}${x.c<2?`<button onclick="S.cards[${i}].c++;S.open=null;R()">Move right</button>`:""}<button onclick="S.cards.splice(${i},1);S.open=null;R()">Archive</button></div>`:""}</li>`;
  return `<h1>Board</h1><div style="display:flex;gap:20px">${COLS.map((c,k)=>`<section aria-label="${c}"><h2>${c} (${S.cards.filter(x=>x.c==k).length})</h2><ul>${S.cards.map((x,i)=>x.c==k?card(x,i):"").join("")}</ul></section>`).join("")}</div>
  <button onclick="set('dlg','add')">Add card</button>${S.dlg?dialog("New card",field("Card title","n")+`<button onclick="S.cards.push({t:S.n||'Card',c:0});S.n='';S.dlg=null;R()">Create</button>`):""}`;
});""")

APPS["contacts"] = ("Contacts", r"""
app({people:[{n:"Ana",p:"555-0101",f:false},{n:"Ben",p:"555-0102",f:true},{n:"Cleo",p:"555-0103",f:false}], sel:null, edit:false, tab:"All", np:""}, () => {
  if (S.sel!=null) { const x=S.people[S.sel]; return `<button onclick="S.sel=null;S.edit=false;R()">All contacts</button><h1>${x.n}</h1>
    ${S.edit?field("Phone","np")+`<button onclick="S.people[${S.sel}].p=S.np||S.people[${S.sel}].p;S.edit=false;R()">Save</button><button onclick="set('edit',false)">Cancel</button>`:
    `<p>Phone ${x.p}</p><button onclick="S.np='';set('edit',true)">Edit</button><button onclick="S.people[${S.sel}].f=!S.people[${S.sel}].f;R()">${x.f?"Remove from favourites":"Add to favourites"}</button>`}`; }
  return `<h1>Contacts</h1>${tabs("tab",["All","Favourites"])}<ul>${S.people.map((x,i)=>(S.tab=="All"||x.f)?`<li><button onclick="set('sel',${i})">${x.n}</button></li>`:"").join("")}</ul>`;
});""")

APPS["photos"] = ("Photos", r"""
const A={Holiday:["Beach","Hotel","Sunset"],Family:["Dinner","Garden"],Pets:["Cat","Dog","Fish","Bird"]};
app({album:null, i:0, fav:{}, info:false, grid:true}, () => {
  if (!S.album) return `<h1>Albums</h1><button onclick="tog('grid')">${S.grid?"List view":"Grid view"}</button><ul>${Object.keys(A).map(a=>`<li><button onclick="S.album='${a}';S.i=0;R()">${a} (${A[a].length})</button></li>`).join("")}</ul>`;
  const ph=A[S.album][S.i];
  return `<button onclick="set('album',null)">Albums</button><h1>${S.album}</h1><figure><figcaption>${ph} — ${S.i+1} of ${A[S.album].length}</figcaption></figure>
  <button onclick="set('i',Math.max(0,S.i-1))" ${S.i==0?"disabled":""}>Previous photo</button><button onclick="set('i',Math.min(A[S.album].length-1,S.i+1))" ${S.i==A[S.album].length-1?"disabled":""}>Next photo</button>
  <button onclick="S.fav[S.album+S.i]=!S.fav[S.album+S.i];R()">${S.fav[S.album+S.i]?"Unfavourite":"Favourite"}</button><button onclick="tog('info')">Info</button>
  ${S.info?`<aside aria-label="Details"><p>Taken 2025</p><p>Album ${S.album}</p></aside>`:""}`;
});""")

APPS["chat"] = ("Messages", r"""
const BOT={Hello:"Hi there!","How are you?":"Great, thanks.",Bye:"See you!"};
app({th:null, log:{Mia:["Mia: Lunch?"],Leo:[],Team:["Leo: Standup at 10"]}, mute:{}, m:false}, () => {
  if (!S.th) return `<h1>Messages</h1><ul>${Object.keys(S.log).map(t=>`<li><button onclick="set('th','${t}')">${t}${S.mute[t]?" (muted)":""} — ${S.log[t].length} messages</button></li>`).join("")}</ul>`;
  const t=S.th;
  return `<button onclick="set('th',null)">Back</button><h1>${t}</h1>${menu("m","Conversation options",[[S.mute[t]?"Unmute":"Mute",`S.mute['${t}']=!S.mute['${t}']`],["Clear history",`S.log['${t}']=[]`]])}
  <ol aria-label="Messages">${S.log[t].map(m=>`<li>${esc(m)}</li>`).join("")||"<li>No messages yet</li>"}</ol>
  <div role="group" aria-label="Quick replies">${Object.keys(BOT).map(q=>`<button onclick="S.log['${t}'].push('You: ${q}','${t}: ${BOT[q]}');R()">${q}</button>`).join("")}</div>`;
});""")

APPS["quiz"] = ("Quiz", r"""
const Q=[["2 + 2?",["3","4","5"],1],["Capital of France?",["Paris","Rome","Oslo"],0],["Largest planet?",["Mars","Earth","Jupiter"],2]];
app({q:-1, pick:null, score:0, checked:false}, () => {
  if (S.q<0) return `<h1>Quiz</h1><p>3 questions</p><button onclick="set('q',0)">Start quiz</button>`;
  if (S.q>=Q.length) return `<h1>Finished</h1><p>Score ${S.score} of ${Q.length}</p><button onclick="S.q=-1;S.score=0;R()">Play again</button>`;
  const [t,o,a]=Q[S.q];
  return `<h1>Question ${S.q+1}</h1><p>${t}</p><div role="radiogroup">${o.map((x,i)=>`<label><input type="radio" name="a" ${S.pick===i?"checked":""} ${S.checked?"disabled":""} onchange="set('pick',${i})">${x}</label>`).join("")}</div>
  ${S.checked?`<p>${S.pick===a?"Correct":"Wrong, it was "+o[a]}</p><button onclick="S.q++;S.pick=null;S.checked=false;R()">Next question</button>`:
    `<button ${S.pick===null?"disabled":""} onclick="S.score+=S.pick===${a}?1:0;set('checked',true)">Check answer</button>`}<p>Score ${S.score}</p>`;
});""")

APPS["converter"] = ("Converter", r"""
const U={Length:{m:1,km:1000,ft:0.3048},Weight:{kg:1,g:0.001,lb:0.4536},Time:{s:1,min:60,h:3600}};
app({kind:"Length", from:"m", to:"km", v:"1", out:null, hist:[]}, () => {
  const u=Object.keys(U[S.kind]);
  const sel=(k)=>`<select aria-label="${k=="from"?"From unit":"To unit"}" onchange="set('${k}',this.value)">${u.map(x=>`<option ${S[k]==x?"selected":""}>${x}</option>`).join("")}</select>`;
  return `<h1>Converter</h1>${tabs("kind",Object.keys(U)).replace(/set\('kind','(\w+)'\)/g,"S.kind='$1';S.from=Object.keys(U['$1'])[0];S.to=Object.keys(U['$1'])[1];S.out=null;R()")}
  ${field("Value","v")}${sel("from")} to ${sel("to")}<button onclick="const r=(+S.v||0)*U[S.kind][S.from]/U[S.kind][S.to];S.out=r.toPrecision(4);S.hist.unshift(S.v+' '+S.from+' = '+S.out+' '+S.to);R()">Convert</button>
  <button onclick="const a=S.from;S.from=S.to;S.to=a;S.out=null;R()">Swap units</button>${S.out!==null?`<p>Result ${S.out} ${S.to}</p>`:""}
  ${S.hist.length?`<h2>History</h2><ul>${S.hist.slice(0,3).map(h=>`<li>${h}</li>`).join("")}</ul><button onclick="set('hist',[])">Clear history</button>`:""}`;
});""")

APPS["signup"] = ("Sign up", r"""
app({step:1, name:"", plan:"Free", terms:false, news:false, err:""}, () => {
  const steps=["Account","Plan","Confirm"];
  let b="";
  if (S.step==1) b=field("Full name","name")+`<button onclick="if(!S.name){S.err='Name is required'}else{S.err='';S.step=2}R()">Continue</button>`;
  if (S.step==2) b=`${["Free","Pro","Team"].map(p=>`<button aria-pressed="${S.plan==p}" onclick="set('plan','${p}')">${p} plan</button>`).join("")}<p>Chosen ${S.plan}</p><button onclick="set('step',1)">Back</button><button onclick="set('step',3)">Continue</button>`;
  if (S.step==3) b=`<p>${esc(S.name)}, ${S.plan} plan</p>${check("I accept the terms","terms")}${check("Send me news","news")}<button onclick="set('step',2)">Back</button><button onclick="if(!S.terms){S.err='Accept the terms first'}else{S.err='';S.step=4}R()">Create account</button>`;
  if (S.step==4) b=`<h2>Welcome, ${esc(S.name)}!</h2><button onclick="S.step=1;S.name='';S.terms=false;R()">Start over</button>`;
  return `<h1>Sign up</h1>${S.step<4?`<ol aria-label="Progress">${steps.map((s,i)=>`<li>${i+1==S.step?"Current: ":""}${s}</li>`).join("")}</ol>`:""}${S.err?`<p role="alert">${S.err}</p>`:""}${b}`;
});""")

APPS["filetree"] = ("Explorer", r"""
const T={Documents:{Work:{"report.txt":1,"plan.txt":1},"cv.txt":1},Music:{"song.mp3":1},Pictures:{Trips:{"rome.jpg":1},"me.jpg":1}};
app({path:[], sel:null, sort:"Name", dlg:null, hidden:false}, () => {
  let d=T; S.path.forEach(p=>d=d[p]);
  let names=Object.keys(d); if (S.sort=="Type") names.sort((a,b)=>(typeof d[a]).localeCompare(typeof d[b])); else names.sort();
  return `<h1>Explorer</h1><nav aria-label="Path"><button onclick="S.path=[];S.sel=null;R()">Home</button>${S.path.map((p,i)=>`<button onclick="S.path=S.path.slice(0,${i+1});S.sel=null;R()">${p}</button>`).join("")}</nav>
  ${menu("m","Sort by",[["Name","S.sort='Name'"],["Type","S.sort='Type'"]])}<p>${names.length} items, sorted by ${S.sort}</p>
  <ul>${names.map(n=>typeof d[n]=="object"?`<li><button onclick="S.path.push('${n}');S.sel=null;R()">Folder ${n}</button></li>`:`<li><button aria-pressed="${S.sel==n}" onclick="set('sel','${n}')">File ${n}</button></li>`).join("")}</ul>
  ${S.sel?`<p>Selected ${S.sel}</p><button onclick="set('dlg','props')">Properties</button>`:""}${S.dlg?dialog("Properties of "+S.sel,`<p>Size 4 KB</p><p>Folder ${S.path.join("/")||"Home"}</p>`):""}`;
});""")

APPS["music"] = ("Player", r"""
const L={"Morning Mix":["Sunrise","Coffee","Commute"],"Focus":["Deep","Flow"],"Party":["Jump","Lights","Late","Home"]};
app({pl:"Morning Mix", i:0, play:false, shuf:false, rep:"Off", queue:false}, () => {
  const s=L[S.pl];
  return `<h1>Player</h1><nav aria-label="Playlists">${Object.keys(L).map(p=>`<button aria-current="${S.pl==p}" onclick="S.pl='${p}';S.i=0;S.play=false;R()">${p}</button>`).join("")}</nav>
  <p>${S.play?"Playing":"Paused"}: ${s[S.i]} (${S.i+1}/${s.length})</p>
  <button onclick="set('i',(S.i-1+L[S.pl].length)%L[S.pl].length)">Previous track</button><button onclick="tog('play')">${S.play?"Pause":"Play"}</button><button onclick="set('i',(S.i+1)%L[S.pl].length)">Next track</button>
  <button aria-pressed="${S.shuf}" onclick="tog('shuf')">Shuffle</button><button onclick="set('rep',{Off:'All',All:'One',One:'Off'}[S.rep])">Repeat ${S.rep}</button><button onclick="tog('queue')">${S.queue?"Hide":"Show"} queue</button>
  ${S.queue?`<ol aria-label="Queue">${s.map((t,k)=>`<li><button onclick="S.i=${k};S.play=true;R()">${t}</button></li>`).join("")}</ol>`:""}`;
});""")

APPS["booking"] = ("Rooms", r"""
const H={"Lake Inn":[80,"Lake view"],"City Hotel":[120,"Central"],"Hill Lodge":[60,"Quiet"]};
app({h:null, nights:1, guests:1, br:false, booked:[], tab:"Search"}, () => {
  if (S.tab=="My trips") return `<h1>Rooms</h1>${tabs("tab",["Search","My trips"])}<ul>${S.booked.map((b,i)=>`<li>${b} <button onclick="S.booked.splice(${i},1);R()">Cancel booking</button></li>`).join("")||"<li>No trips</li>"}</ul>`;
  if (!S.h) return `<h1>Rooms</h1>${tabs("tab",["Search","My trips"])}<ul>${Object.keys(H).map(h=>`<li><button onclick="set('h','${h}')">${h} $${H[h][0]}</button></li>`).join("")}</ul>`;
  const total=H[S.h][0]*S.nights+(S.br?10*S.nights*S.guests:0);
  return `<button onclick="set('h',null)">Back to hotels</button><h1>${S.h}</h1><p>${H[S.h][1]}</p>
  <p>Nights ${S.nights}</p><button onclick="set('nights',Math.max(1,S.nights-1))">Fewer nights</button><button onclick="set('nights',Math.min(7,S.nights+1))">More nights</button>
  <p>Guests ${S.guests}</p><button onclick="set('guests',Math.max(1,S.guests-1))">Fewer guests</button><button onclick="set('guests',Math.min(4,S.guests+1))">More guests</button>
  ${check("Add breakfast","br")}<p>Total $${total}</p><button onclick="S.booked.push(S.h+', '+S.nights+' nights');S.h=null;S.tab='My trips';R()">Book now</button>`;
});""")

APPS["recipes"] = ("Recipes", r"""
const RC={Pancakes:{t:"Breakfast",ing:["Flour","Milk","Egg"],st:["Mix","Rest","Fry"]},Salad:{t:"Lunch",ing:["Lettuce","Tomato"],st:["Chop","Toss"]},Curry:{t:"Dinner",ing:["Rice","Spice","Veg"],st:["Boil","Cook","Serve"]}};
app({r:null, f:"Any", serv:2, step:0, saved:{}, tab:"Ingredients"}, () => {
  if (!S.r) return `<h1>Recipes</h1>${tabs("f",["Any","Breakfast","Lunch","Dinner"])}<ul>${Object.keys(RC).filter(k=>S.f=="Any"||RC[k].t==S.f).map(k=>`<li><button onclick="S.r='${k}';S.step=0;R()">${S.saved[k]?"★ ":""}${k}</button></li>`).join("")}</ul>`;
  const x=RC[S.r];
  return `<button onclick="set('r',null)">All recipes</button><h1>${S.r}</h1><button onclick="S.saved['${S.r}']=!S.saved['${S.r}'];R()">${S.saved[S.r]?"Unsave":"Save recipe"}</button>
  ${tabs("tab",["Ingredients","Steps"])}${S.tab=="Ingredients"?`<p>Serves ${S.serv}</p><button onclick="set('serv',Math.max(1,S.serv-1))">Fewer servings</button><button onclick="set('serv',Math.min(8,S.serv+1))">More servings</button><ul>${x.ing.map(i=>`<li>${i} × ${S.serv}</li>`).join("")}</ul>`:
  `<p>Step ${S.step+1} of ${x.st.length}: ${x.st[S.step]}</p><button ${S.step==0?"disabled":""} onclick="set('step',S.step-1)">Previous step</button><button ${S.step==x.st.length-1?"disabled":""} onclick="set('step',S.step+1)">Next step</button>`}`;
});""")

APPS["fitness"] = ("Workouts", r"""
app({log:[{a:"Run",m:30}], a:"Run", m:20, tab:"Today", goal:150, dlg:null}, () => {
  const tot=S.log.reduce((s,x)=>s+x.m,0);
  let b="";
  if (S.tab=="Today") b=`<p>${tot} of ${S.goal} minutes</p><progress aria-label="Weekly goal" value="${tot}" max="${S.goal}"></progress>${["Run","Swim","Bike","Yoga"].map(a=>`<button aria-pressed="${S.a==a}" onclick="set('a','${a}')">${a}</button>`).join("")}
    <p>${S.m} minutes</p><button onclick="set('m',Math.max(5,S.m-5))">Less time</button><button onclick="set('m',Math.min(90,S.m+5))">More time</button><button onclick="S.log.push({a:S.a,m:S.m});R()">Log workout</button>`;
  if (S.tab=="History") b=`<ul>${S.log.map((x,i)=>`<li>${x.a} ${x.m} min <button onclick="S.log.splice(${i},1);R()">Delete ${x.a} ${x.m}</button></li>`).join("")}</ul>`;
  if (S.tab=="Goal") b=`<p>Weekly goal ${S.goal} minutes</p><button onclick="set('dlg','g')">Change goal</button>`;
  return `<h1>Workouts</h1>${tabs("tab",["Today","History","Goal"])}${b}${S.dlg?dialog("Weekly goal",[100,150,200].map(g=>`<button onclick="S.goal=${g};S.dlg=null;R()">${g} minutes</button>`).join("")):""}`;
});""")

APPS["library"] = ("Library", r"""
const B={Dune:"Sci-fi",Emma:"Classic",Dracula:"Horror","Neuromancer":"Sci-fi","Jane Eyre":"Classic"};
app({g:"All", sel:null, loans:[], hold:{}, tab:"Catalog", sort:false}, () => {
  if (S.tab=="My loans") return `<h1>Library</h1>${tabs("tab",["Catalog","My loans"])}<ul>${S.loans.map(b=>`<li>${b} <button onclick="S.loans=S.loans.filter(x=>x!='${b}');R()">Return ${b}</button></li>`).join("")||"<li>No loans</li>"}</ul>`;
  let names=Object.keys(B).filter(b=>S.g=="All"||B[b]==S.g); if (S.sort) names.sort();
  return `<h1>Library</h1>${tabs("tab",["Catalog","My loans"])}${tabs("g",["All","Sci-fi","Classic","Horror"])}<button onclick="tog('sort')">${S.sort?"Original order":"Sort A to Z"}</button>
  <ul>${names.map(b=>`<li><button onclick="set('sel','${b}')">${b}</button></li>`).join("")}</ul>
  ${S.sel?`<section aria-label="Book"><h2>${S.sel}</h2><p>${B[S.sel]}</p>${S.loans.includes(S.sel)?"<p>On loan to you</p>":`<button onclick="S.loans.push(S.sel);R()">Borrow</button>`}<button onclick="S.hold[S.sel]=!S.hold[S.sel];R()">${S.hold[S.sel]?"Cancel hold":"Place hold"}</button></section>`:""}`;
});""")

APPS["tracker"] = ("Issues", r"""
app({is:[{t:"Login fails",s:"Open",p:"High"},{t:"Typo on page",s:"Open",p:"Low"},{t:"Slow search",s:"Closed",p:"Medium"}], f:"Open", sel:null, m:false}, () => {
  if (S.sel!=null) { const x=S.is[S.sel]; return `<button onclick="set('sel',null)">All issues</button><h1>${x.t}</h1><p>Status ${x.s}, priority ${x.p}</p>
    <button onclick="S.is[${S.sel}].s=S.is[${S.sel}].s=='Open'?'Closed':'Open';R()">${x.s=="Open"?"Close issue":"Reopen issue"}</button>
    ${menu("m","Set priority",["Low","Medium","High"].map(p=>[p,`S.is[${S.sel}].p='${p}'`]))}`; }
  return `<h1>Issues</h1>${tabs("f",["Open","Closed","All"])}<ul>${S.is.map((x,i)=>(S.f=="All"||x.s==S.f)?`<li><button onclick="set('sel',${i})">${x.t} (${x.p})</button></li>`:"").join("")}</ul>
  <button onclick="S.is.push({t:'New issue '+S.is.length,s:'Open',p:'Medium'});R()">New issue</button>`;
});""")

APPS["faq"] = ("Help center", r"""
const F={Account:[["Reset password","Use the link on the sign-in page."],["Delete account","Go to settings, then privacy."]],Billing:[["Refunds","Within 30 days."],["Invoices","Sent monthly."]],Shipping:[["Delivery time","3 to 5 days."]]};
app({c:"Account", open:{}, helpful:{}, q:"", dlg:null}, () => `<h1>Help center</h1>${field("Search help","q")}<button onclick="set('dlg','search')">Search</button>
  <nav aria-label="Topics">${Object.keys(F).map(c=>`<button aria-current="${S.c==c}" onclick="set('c','${c}')">${c}</button>`).join("")}</nav>
  ${F[S.c].map(([q,a])=>`<div><button aria-expanded="${!!S.open[q]}" onclick="S.open['${q}']=!S.open['${q}'];R()">${q}</button>${S.open[q]?`<p>${a}</p>${S.helpful[q]?"<p>Thanks for your feedback</p>":`<button onclick="S.helpful['${q}']=1;R()">Helpful</button><button onclick="S.helpful['${q}']=1;R()">Not helpful</button>`}`:""}</div>`).join("")}
  ${S.dlg?dialog("Search results",`<p>${Object.values(F).flat().filter(([q])=>q.toLowerCase().includes((S.q||"").toLowerCase())).length} articles found</p>`):""}`);""")

APPS["weather"] = ("Weather", r"""
const W={Oslo:[["Mon",-2,"Snow"],["Tue",0,"Cloudy"],["Wed",1,"Sunny"]],Lima:[["Mon",22,"Sunny"],["Tue",21,"Cloudy"],["Wed",23,"Sunny"]],Pune:[["Mon",30,"Sunny"],["Tue",28,"Rain"],["Wed",29,"Cloudy"]]};
app({city:"Oslo", unit:"C", day:null, saved:["Oslo"], dlg:null}, () => {
  const t=c=>S.unit=="C"?c+"°C":Math.round(c*9/5+32)+"°F";
  return `<h1>Weather</h1><nav aria-label="Saved cities">${S.saved.map(c=>`<button aria-current="${S.city==c}" onclick="S.city='${c}';S.day=null;R()">${c}</button>`).join("")}</nav>
  <button onclick="set('dlg','add')">Add city</button><button onclick="set('unit',S.unit=='C'?'F':'C')">Show °${S.unit=="C"?"F":"C"}</button>
  <h2>${S.city}</h2><ul>${W[S.city].map(([d,c,s],i)=>`<li><button aria-pressed="${S.day===i}" onclick="set('day',${i})">${d} ${t(c)}</button></li>`).join("")}</ul>
  ${S.day!==null?`<p>${W[S.city][S.day][0]}: ${W[S.city][S.day][2]}, ${t(W[S.city][S.day][1])}</p>`:""}
  ${S.saved.length>1?`<button onclick="S.saved=S.saved.filter(c=>c!=S.city);S.city=S.saved[0];S.day=null;R()">Remove ${S.city}</button>`:""}
  ${S.dlg?dialog("Add city",Object.keys(W).filter(c=>!S.saved.includes(c)).map(c=>`<button onclick="S.saved.push('${c}');S.city='${c}';S.dlg=null;S.day=null;R()">${c}</button>`).join("")||"<p>All cities added</p>"):""}`;
});""")

for name, (title, js) in APPS.items():
    page = (f'<!doctype html><html lang="en"><head><title>{title}</title>{HEAD}</head>'
            f'<body><main id="app"></main><script>{js}</script></body></html>\n')
    (HERE / f"{name}.html").write_text(page)
print(len(APPS), "apps:", " ".join(APPS))

"use strict";(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[6009],{1255:function(e,a,i){var l=i(5893),r=i(1232),t=i(61),o=i(7841),n=i(5117),s=i(7294),d=i(4012),c=i(1830),p=i(8034);a.Z=e=>{let{form:a,fieldName:i="link",shareIdLength:u,appUrl:m,defaultAppUrl:x,pathPrefix:h="/s/"}=e,g=(0,c.Z)(),v=a.values[i]||"",j=!!a.errors[i],[f,w]=(0,s.useState)(!1);(0,s.useEffect)(()=>{w(!0)},[]);let b=m!==x?m:f?window.location.origin:"";return(0,l.jsxs)(l.Fragment,{children:[(0,l.jsxs)(r.Z,{align:j?"center":"flex-end",noWrap:!0,children:[(0,l.jsx)(t.o,{style:{flex:"1"},variant:"filled",label:g("upload.modal.link.label"),placeholder:"myAwesomeShare",...a.getInputProps(i)}),(0,l.jsx)(o.z,{style:{flex:"0 0 auto"},variant:"outline",onClick:()=>a.setFieldValue(i,(0,p.v)(u)),children:(0,l.jsx)(d.Z,{id:"common.button.generate"})})]}),(0,l.jsx)(n.x,{italic:!0,size:"xs",sx:e=>({color:e.colors.gray[6],wordBreak:"break-all"}),children:"".concat(b).concat(h).concat(v)})]})}},6009:function(e,a,i){let l;i.r(a),i.d(a,{default:function(){return es}});var r=i(5893),t=i(3523),o=i(7564),n=i(9236),s=i(5117),d=i(8818),c=i(7841),p=i(1232),u=i(8276),m=i(4922),x=i(9204),h=i(2720),g=i(1664),v=i.n(g),j=i(7294),f=i(856),w=i(4012),b=i(8001),y=i(1690),Z=i(5123),k=i(1003),S=i(381),_=i.n(S),U=i(1163),E=i(1830),z=i(9674),I=i(503);let C=e=>{let{share:a,appUrl:i,defaultAppUrl:l}=e,t=(0,u.o)(),n=(0,U.useRouter)(),d=(0,E.Z)(),[p,m]=(0,j.useState)(!1),x=!!n.query.reverseShareToken,h="".concat(i!==l?i:window.location.origin,"/s/").concat(a.id);return(0,r.jsxs)(o.K,{align:"stretch",children:[(0,r.jsx)(z.Z,{link:h,toggleQR:()=>{m(!p)}}),(0,r.jsx)(k.U,{in:p,children:(0,r.jsx)(I.Z,{link:h})}),!0===a.notifyReverseShareCreator&&(0,r.jsx)(s.x,{size:"sm",sx:e=>({color:"dark"===e.colorScheme?e.colors.gray[3]:e.colors.dark[4]}),children:d("upload.modal.completed.notified-reverse-share-creator")}),(0,r.jsx)(s.x,{size:"xs",sx:e=>({color:e.colors.gray[6]}),children:0===_()(a.expiration).unix()?d("upload.modal.completed.never-expires"):d("upload.modal.completed.expires-on",{expiration:_()(a.expiration).format("LLL")})}),(0,r.jsx)(c.z,{onClick:()=>{t.closeAll(),x?n.reload():n.push("/upload")},children:(0,r.jsx)(w.Z,{id:"common.button.done"})})]})};var R=(e,a,i,l)=>{let t=(0,E.w)();return e.openModal({closeOnClickOutside:!1,withCloseButton:!1,closeOnEscape:!1,title:t("upload.modal.completed.share-ready"),children:(0,r.jsx)(C,{share:a,appUrl:i,defaultAppUrl:l})})},P=i(4403),F=i(2679),A=i(9408),V=i(6176),L=i(8855),T=i(8078),K=i(9542),M=i(61),B=i(2615),D=i(1194),N=i(3193),X=i(7248),O=i(3898),q=i(6310),H=i(9165),J=i(7126),W=i(3861),Y=i(8034),$=i(1255);let Q=async function(e){let a=arguments.length>1&&void 0!==arguments[1]?arguments[1]:10;if(a<=0)throw Error("Could not generate available link");let i=(0,Y.v)(e);return await H.Z.isShareIdAvailable(i)?i:await Q(e,a-1)},G=e=>{let{uploadCallback:a,files:i,options:l}=e,t=(0,u.o)(),n=(0,E.Z)(),d=(0,Y.v)(l.shareIdLength),[p,m]=(0,j.useState)(!0),[x,h]=(0,j.useState)(""),g=q.Ry().shape({link:q.Z_().required(n("common.error.field-required")).min(3,n("common.error.too-short",{length:3})).max(50,n("common.error.too-long",{length:50})).matches(RegExp("^[a-zA-Z0-9_-]*$"),{message:n("upload.modal.link.error.invalid")}),name:q.Z_().transform(e=>e||void 0).min(3,n("common.error.too-short",{length:3})).max(30,n("common.error.too-long",{length:30})),password:q.Z_().transform(e=>e||void 0).min(3,n("common.error.too-short",{length:3})).max(30,n("common.error.too-long",{length:30})),maxViews:q.Rx().transform(e=>e||void 0).min(1),description:q.Z_().optional().max(512,n("common.error.too-long",{length:512}))}),v=l.defaultExpiration?l.defaultExpiration:{value:7,unit:"days"},b=(0,X.c)({initialValues:{name:void 0,link:d,recipients:[],password:void 0,maxViews:void 0,description:void 0,expiration_num:v.value,expiration_unit:"-".concat(v.unit),never_expires:!1,restrictToRecipients:!1},validate:(0,O.X)(g)}),y=e=>{b.setFieldValue("restrictToRecipients",e),e&&b.setFieldValue("password",void 0)},Z=b.onSubmit(async e=>{if(await H.Z.isShareIdAvailable(e.link)){let r=b.values.never_expires?"never":b.values.expiration_num+b.values.expiration_unit,o=_()().add(b.values.expiration_num,b.values.expiration_unit.replace("-",""));if(0!=l.maxExpiration.value&&(b.values.never_expires||o.isAfter(_()().add(l.maxExpiration.value,l.maxExpiration.unit)))){b.setFieldError("expiration_num",n("upload.modal.expires.error.too-long",{max:_().duration(l.maxExpiration.value,l.maxExpiration.unit).humanize()}));return}a({id:e.link,name:e.name,expiration:r,recipients:e.recipients,description:e.description,security:{password:e.restrictToRecipients?void 0:e.password||void 0,maxViews:e.maxViews||void 0,restrictToRecipients:e.restrictToRecipients||void 0}},i),t.closeAll()}else b.setFieldError("link",n("upload.modal.link.error.taken"))});return(0,r.jsxs)(r.Fragment,{children:[p&&!l.isUserSignedIn&&(0,r.jsx)(P.b,{withCloseButton:!0,onClose:()=>m(!1),icon:(0,r.jsx)(f.HtX,{size:16}),title:n("upload.modal.not-signed-in"),color:"yellow",children:(0,r.jsx)(w.Z,{id:"upload.modal.not-signed-in-description"})}),(0,r.jsx)("form",{onSubmit:Z,children:(0,r.jsxs)(o.K,{align:"stretch",children:[(0,r.jsx)($.Z,{form:b,fieldName:"link",shareIdLength:l.shareIdLength,appUrl:l.appUrl,defaultAppUrl:l.defaultAppUrl,pathPrefix:"/s/"}),!l.isReverseShare&&(0,r.jsxs)(r.Fragment,{children:[(0,r.jsxs)(F.r,{align:b.errors.expiration_num?"center":"flex-end",children:[(0,r.jsx)(A.J,{xs:6,children:(0,r.jsx)(V.Y,{min:1,max:99999,precision:0,variant:"filled",label:n("upload.modal.expires.label"),disabled:b.values.never_expires,...b.getInputProps("expiration_num")})}),(0,r.jsx)(A.J,{xs:6,children:(0,r.jsx)(L.Ph,{disabled:b.values.never_expires,...b.getInputProps("expiration_unit"),data:[{value:"-minutes",label:1==b.values.expiration_num?n("upload.modal.expires.minute-singular"):n("upload.modal.expires.minute-plural")},{value:"-hours",label:1==b.values.expiration_num?n("upload.modal.expires.hour-singular"):n("upload.modal.expires.hour-plural")},{value:"-days",label:1==b.values.expiration_num?n("upload.modal.expires.day-singular"):n("upload.modal.expires.day-plural")},{value:"-weeks",label:1==b.values.expiration_num?n("upload.modal.expires.week-singular"):n("upload.modal.expires.week-plural")},{value:"-months",label:1==b.values.expiration_num?n("upload.modal.expires.month-singular"):n("upload.modal.expires.month-plural")},{value:"-years",label:1==b.values.expiration_num?n("upload.modal.expires.year-singular"):n("upload.modal.expires.year-plural")}]})})]}),0==l.maxExpiration.value&&(0,r.jsx)(T.X,{label:n("upload.modal.expires.never-long"),...b.getInputProps("never_expires")}),(0,r.jsx)(s.x,{italic:!0,size:"xs",sx:e=>({color:e.colors.gray[6]}),children:(0,J.de)({neverExpires:n("upload.modal.completed.never-expires"),expiresOn:n("upload.modal.completed.expires-on")},b)})]}),(0,r.jsxs)(K.U,{children:[(0,r.jsxs)(K.U.Item,{value:"description",sx:{borderBottom:"none"},children:[(0,r.jsx)(K.U.Control,{children:(0,r.jsx)(w.Z,{id:"upload.modal.accordion.name-and-description.title"})}),(0,r.jsx)(K.U.Panel,{children:(0,r.jsxs)(o.K,{align:"stretch",children:[(0,r.jsx)(M.o,{variant:"filled",placeholder:n("upload.modal.accordion.name-and-description.name.placeholder"),...b.getInputProps("name")}),(0,r.jsx)(B.g,{variant:"filled",placeholder:n("upload.modal.accordion.name-and-description.description.placeholder"),...b.getInputProps("description")})]})})]}),l.enableEmailRecepients&&(0,r.jsxs)(K.U.Item,{value:"recipients",sx:{borderBottom:"none"},children:[(0,r.jsx)(K.U.Control,{children:(0,r.jsx)(w.Z,{id:"upload.modal.accordion.email.title"})}),(0,r.jsxs)(K.U.Panel,{children:[(0,r.jsx)(D.NU,{data:b.values.recipients,placeholder:n("upload.modal.accordion.email.placeholder"),searchable:!0,creatable:!0,id:"recipient-emails",inputMode:"email",searchValue:x,onSearchChange:h,getCreateLabel:e=>"+ ".concat(e),onCreate:e=>{if(!e.match(/^\S+@\S+\.\S+$/)){b.setFieldError("recipients",n("upload.modal.accordion.email.invalid-email"));return}b.setFieldError("recipients",null);let a=b.values.recipients.includes(e)?b.values.recipients:[...b.values.recipients,e];return b.setFieldValue("recipients",a),e},...b.getInputProps("recipients"),onChange:e=>{b.setFieldValue("recipients",e)},onKeyDown:e=>{if("Enter"===e.key||","===e.key||";"===e.key){e.preventDefault();let a=x.trim();if(a.match(/^\S+@\S+\.\S+$/)&&!b.values.recipients.includes(a)){let e=[...b.values.recipients,a];b.setFieldValue("recipients",e)}h("")}else" "===e.key&&(e.preventDefault(),h(""))}}),l.enableUserRecipients&&(0,r.jsx)(T.X,{mt:"sm",label:n("upload.modal.accordion.email.restrict-to-recipients"),checked:b.values.restrictToRecipients,onChange:e=>y(e.currentTarget.checked)})]})]}),(0,r.jsxs)(K.U.Item,{value:"security",sx:{borderBottom:"none"},children:[(0,r.jsx)(K.U.Control,{children:(0,r.jsx)(w.Z,{id:"upload.modal.accordion.security.title"})}),(0,r.jsx)(K.U.Panel,{children:(0,r.jsxs)(o.K,{align:"stretch",children:[!b.values.restrictToRecipients&&(0,r.jsx)(N.W,{variant:"filled",placeholder:n("upload.modal.accordion.security.password.placeholder"),label:n("upload.modal.accordion.security.password.label"),autoComplete:"new-password",...b.getInputProps("password")}),(0,r.jsx)(V.Y,{min:1,type:"number",variant:"filled",placeholder:n("upload.modal.accordion.security.max-views.placeholder"),label:n("upload.modal.accordion.security.max-views.label"),...b.getInputProps("maxViews")})]})})]})]}),(0,r.jsx)(c.z,{type:"submit","data-autofocus":!0,children:(0,r.jsx)(w.Z,{id:"common.button.share"})})]})})]})},ee=e=>{let{uploadCallback:a,files:i,options:l}=e,t=(0,u.o)(),n=(0,E.Z)(),[s,d]=(0,j.useState)(!0),p=q.Ry().shape({name:q.Z_().transform(e=>e||void 0).min(3,n("common.error.too-short",{length:3})).max(30,n("common.error.too-long",{length:30}))}),m=(0,X.c)({initialValues:{name:void 0,description:void 0},validate:(0,O.X)(p)}),x=m.onSubmit(async e=>{let r=await Q(l.shareIdLength).catch(()=>{W.Z.error(n("upload.modal.link.error.taken"))});r&&(a({id:r,name:e.name||(function(){var f=(i&&i[0]&&i[0].name)||"文件",b=f.replace(/\.[^.]+$/,"")||f,c=(i&&i.length>1)?"等"+i.length+"个文件":"" ,n=(b.slice(0,Math.max(1,30-c.length))+c).slice(0,30);return n.length<3?"上传的文件":n})(),expiration:"never",recipients:[],description:(window.__hcNote?window.__hcNote():"")||e.description,security:{password:void 0,maxViews:void 0}},i),t.closeAll())});(0,j.useEffect)(function(){var _n=0,_iv=setInterval(function(){if(window.__hcNoteReady||_n++>30){clearInterval(_iv);try{if(!window.__hcNeedNote)x({preventDefault:function(){}})}catch(e){}}},50);},[]);return(0,r.jsxs)(o.K,{children:[s&&!l.isUserSignedIn&&(0,r.jsx)(P.b,{withCloseButton:!0,onClose:()=>d(!1),icon:(0,r.jsx)(f.HtX,{size:16}),title:n("upload.modal.not-signed-in"),color:"yellow",children:(0,r.jsx)(w.Z,{id:"upload.modal.not-signed-in-description"})}),(0,r.jsx)("form",{onSubmit:x,children:(0,r.jsxs)(o.K,{align:"stretch",children:[(0,r.jsxs)(o.K,{align:"stretch",children:l.simplified?null:[(0,r.jsx)(M.o,{variant:"filled",placeholder:n("upload.modal.accordion.name-and-description.name.placeholder"),...m.getInputProps("name")}),(0,r.jsx)(B.g,{variant:"filled",placeholder:n("upload.modal.accordion.name-and-description.description.placeholder"),...m.getInputProps("description")})]}),(0,r.jsx)(c.z,{type:"submit","data-autofocus":!0,children:(0,r.jsx)(w.Z,{id:"common.button.share"})})]})})]})};var ea=(e,a,i,l)=>{let t=(0,E.w)();return a.simplified?e.openModal({title:t("upload.modal.title"),children:(0,r.jsx)(ee,{options:a,files:i,uploadCallback:l})}):e.openModal({title:t("upload.modal.title"),children:(0,r.jsx)(G,{options:a,files:i,uploadCallback:l})})},ei=i(4347),el=i(1312),er=i(7811),et=i(8226);let eo=(0,h.Z)(12),en=!1;var es=e=>{let{maxShareSize:a,isReverseShare:i=!1,simplified:h}=e,g=(0,u.o)(),k=(0,U.useRouter)(),S=(0,E.Z)(),{user:_}=(0,er.Z)(),z=(0,ei.Z)(),[I,C]=(0,j.useState)([]),[P,F]=(0,j.useState)(!1);(0,el.Z)({message:S("upload.notify.confirm-leave"),enabled:P});let A=(0,j.useRef)(parseInt(z.get("share.chunkSize")));null!=a||(a=(null==_?void 0:_.shareSizeLimit)?parseInt(_.shareSizeLimit):parseInt(z.get("share.maxSize")));let V=(0,j.useMemo)(()=>I.reduce((e,a)=>e+a.size,0),[I]),L=z.get("share.autoOpenShareModal"),T=async(e,a)=>{F(!0);try{let i="/upload"!=k.pathname,r=a.reduce((e,a)=>e+a.size,0);l=await H.Z.create({...e,size:r},i)}catch(e){W.Z.axiosError(e),F(!1);return}Promise.all(a.map(async(e,a)=>eo(async()=>{let i;let r=e=>{C(i=>i.map((i,l)=>(a==l&&(i.uploadingProgress=e),i)))};r(1);let t=Math.ceil(e.size/A.current);0==t&&t++;for(let a=0;a<t;a++){let n=a*A.current,s=n+A.current,d=e.slice(n,s);try{await H.Z.uploadFile(l.id,d,{id:i,name:(0,et.r)(e)},a,t,i=>{if(i.total&&e.size>0){let l=i.loaded/i.total,t=a*A.current,o=d.size*l,n=(t+o)/e.size*100;r(Math.min(n,99.9))}}).then(e=>{i=e.id}),r((a+1)/t*100)}catch(e){var o;if(e instanceof x.d7&&(null===(o=e.response)||void 0===o?void 0:o.data.error)=="unexpected_chunk_index"){a=e.response.data.expectedChunkIndex-1;continue}r(-1),await new Promise(e=>setTimeout(e,5e3)),a=-1;continue}}})))},K=e=>{ea(g,{isUserSignedIn:!!_,isReverseShare:i,appUrl:z.get("general.appUrl"),defaultAppUrl:z.get("general.appUrl",!0),allowUnauthenticatedShares:z.get("security.allowUnauthenticatedShares"),enableEmailRecepients:z.get("share.enableShareEmailRecipients"),enableUserRecipients:z.get("share.enableUserRecipients"),maxExpiration:(null==_?void 0:_.isAdmin)?{value:0,unit:"days"}:z.get("share.maxExpiration"),defaultExpiration:z.get("share.defaultExpiration"),shareIdLength:z.get("share.shareIdLength"),simplified:h},e,T)};return((0,j.useEffect)(()=>{let e=e=>{if(g.modals.length>0)return;let a=e.clipboardData;if(a&&(null==a?void 0:a.getData("text/plain"))){let e=a.getData("text/plain");if(!e)return;let i=e.substring(0,50).replace(/[^a-zA-Z0-9 ]/g,"").trim(),l=new File([e],"".concat(i||"clipboard_paste",".txt"),{type:"text/plain"});l.uploadingProgress=0;let r=(0,et.n)([l],I,e=>W.Z.error(S("upload.notify.duplicate-skipped",{name:e})));if(0===r.length)return;L?(C(r),K(r)):C(e=>[...e,...r])}};return window.addEventListener("paste",e),()=>{window.removeEventListener("paste",e)}},[L,g.modals.length]),(0,j.useEffect)(()=>{let e=I.filter(e=>-1==e.uploadingProgress).length;e>0?(en||W.Z.error(S("upload.notify.count-failed",{count:e}),{withCloseButton:!1,autoClose:!1}),en=!0):((0,m.HN)(),en=!1),I.length>0&&I.every(e=>e.uploadingProgress>=100)&&0==e&&H.Z.completeShare(l.id).then(e=>{F(!1),R(g,e,z.get("general.appUrl"),z.get("general.appUrl",!0)),C([])}).catch(()=>W.Z.error(S("upload.notify.generic-error")))},[I]),_&&!1===_.allowShare&&!i)?(0,r.jsxs)(r.Fragment,{children:[(0,r.jsx)(b.Z,{title:S("upload.title")}),(0,r.jsx)(t.M,{style:{height:"70vh"},children:(0,r.jsxs)(o.K,{align:"center",spacing:10,children:[(0,r.jsx)(f._AN,{size:48,color:"gray"}),(0,r.jsx)(n.D,{order:3,children:(0,r.jsx)(w.Z,{id:"upload.error.not-allowed.title"})}),(0,r.jsx)(s.x,{color:"dimmed",align:"center",children:(0,r.jsx)(w.Z,{id:"upload.error.not-allowed.description"})}),(0,r.jsx)(d.T,{h:5}),(0,r.jsx)(c.z,{component:v(),href:"/account/shares",variant:"light",children:(0,r.jsx)(w.Z,{id:"account.shares.title"})})]})})]}):(0,r.jsxs)(r.Fragment,{children:[(0,r.jsx)(b.Z,{title:S("upload.title")}),(0,r.jsx)(p.Z,{position:"right",mb:20,children:(0,r.jsx)(c.z,{loading:P,disabled:I.length<=0,onClick:()=>K(I),children:(0,r.jsx)(w.Z,{id:"common.button.share"})})}),(0,r.jsx)(y.Z,{title:!L&&I.length>0?S("share.edit.append-upload"):void 0,maxShareSize:a,currentFilesSize:V,onFilesChanged:e=>{let a=(0,et.n)(e,I,e=>W.Z.error(S("upload.notify.duplicate-skipped",{name:e})));0!==a.length&&(L?(C(a),K(a)):C(e=>[...e,...a]))},isUploading:P}),I.length>0&&(0,r.jsx)(Z.Z,{files:I,setFiles:C})]})}},8034:function(e,a,i){i.d(a,{v:function(){return l}});let l=function(){let e=arguments.length>0&&void 0!==arguments[0]?arguments[0]:16,a="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",i="",l=new Uint8Array(e>=3?e:3);return crypto.getRandomValues(l),l.forEach(e=>{i+=a[e%a.length]}),i}}}]);

/* ===== 上传页：链接要求备注时，上传者必须填一次备注 ===== */
(function () {
  if (window.__hcNoteInit) return;
  window.__hcNoteInit = 1;

  var m = location.pathname.match(/\/upload\/([A-Za-z0-9_-]{3,50})/);
  if (!m) { window.__hcNoteReady = true; return; }   // 不在上传页，放行
  var token = m[1], need = false, ta = null, errEl = null;

  window.__hcNote = function () { return ta ? (ta.value || "").trim() : ""; };

  function mk(t, txt) {
    var e = document.createElement(t);
    if (txt != null) e.textContent = txt;
    return e;
  }

  function inject(form) {
    if (form.querySelector("[data-hcn]")) return;
    var ref = form.querySelector("textarea") || form.querySelector("input");
    var cs = null;
    try { cs = ref ? getComputedStyle(ref) : null; } catch (e) { cs = null; }

    var wrap = mk("div");
    wrap.setAttribute("data-hcn", "1");
    wrap.style.cssText = "display:flex;flex-direction:column;gap:6px;width:100%;";

    var lab = mk("label", "备注");
    lab.style.cssText = "font-size:14px;font-weight:600;";
    if (cs) lab.style.color = cs.color;

    var box = mk("textarea");
    box.rows = 3;
    box.placeholder = "请填写备注，例如：张三 / 姥爷的手机 / 三班李老师";
    if (ref) box.className = ref.className;
    box.style.cssText = "width:100%;box-sizing:border-box;resize:vertical;min-height:78px;";
    if (cs) {
      box.style.background = cs.backgroundColor;
      box.style.color = cs.color;
      box.style.border = cs.border;
      box.style.borderRadius = cs.borderRadius;
      box.style.font = cs.font;
      box.style.padding = cs.padding;
    }

    errEl = mk("div", "请先填写备注再上传");
    errEl.style.cssText = "color:#fa5252;font-size:12.5px;display:none;";

    wrap.appendChild(lab);
    wrap.appendChild(box);
    wrap.appendChild(errEl);
    var btn = form.querySelector('button[type="submit"]');
    if (btn && btn.parentNode) btn.parentNode.insertBefore(wrap, btn);
    else form.appendChild(wrap);

    ta = box;
    box.addEventListener("input", function () { errEl.style.display = "none"; });

    /* 拦住提交：stopPropagation 是为了不让事件冒泡到 React 挂载的根节点，
       否则 React 的 onSubmit 照样会跑，preventDefault 挡不住 */
    function guard(ev) {
      if (!need) return;
      if (ta && (ta.value || "").trim()) return;
      ev.preventDefault();
      ev.stopPropagation();
      if (errEl) errEl.style.display = "";
      if (ta) ta.focus();
    }
    form.addEventListener("submit", guard, false);
    form.addEventListener("click", function (ev) {
      var b = ev.target && ev.target.closest && ev.target.closest('button[type="submit"]');
      if (b) guard(ev);
    }, false);
  }

  function scan() {
    try {
      var ds = document.querySelectorAll('[role="dialog"]');
      for (var i = 0; i < ds.length; i++) {
        var f = ds[i].querySelector("form");
        if (f) inject(f);
      }
    } catch (e) {}
  }

  fetch("/inbox/collect/note.json?token=" + encodeURIComponent(token),
        { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (j) {
      need = !!(j && j.need);
      window.__hcNeedNote = need;
      window.__hcNoteReady = true;
      if (!need) return;
      try {
        new MutationObserver(function () { setTimeout(scan, 60); })
          .observe(document.body, { childList: true, subtree: true });
      } catch (e) {}
      scan();
    })
    .catch(function () { window.__hcNoteReady = true; });
})();

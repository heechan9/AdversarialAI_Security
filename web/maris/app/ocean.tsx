"use client";
import {useEffect,useRef,useState} from "react";
import * as THREE from "three";
import {SVGRenderer} from "three/addons/renderers/SVGRenderer.js";
import {createShipControls,resetShipControls,setShipView,type ShipCommand} from "@/lib/ship-controls";

import {createCadDisplay,type SceneMode,type CadSelection,type ShipPart} from "@/lib/ship-cad";

export default function Ocean({playing,command,mode,selection,onInteract,onZoom}:{playing:boolean,mode:SceneMode,selection:CadSelection,command:{id:number;kind:ShipCommand},onInteract:()=>void,onZoom:(zoom:number)=>void}){
 const displayRef=useRef({mode,selection});
 useEffect(()=>{displayRef.current={mode,selection}},[mode,selection]);
 const host=useRef<HTMLDivElement>(null),active=useRef(playing),commandRef=useRef(command),callbacks=useRef({onInteract,onZoom});const [failed,setFailed]=useState(false);
 useEffect(()=>{active.current=playing},[playing]);useEffect(()=>{commandRef.current=command},[command]);useEffect(()=>{callbacks.current={onInteract,onZoom}},[onInteract,onZoom]);
 useEffect(()=>{
  const el=host.current!;let renderer:THREE.WebGLRenderer|SVGRenderer;let software=false;
  const compact=matchMedia("(max-width:700px), (pointer:coarse)").matches;
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:"low-power"});renderer.setPixelRatio(Math.min(devicePixelRatio,compact?1.25:1.6));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.18;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.shadowMap.autoUpdate=false;renderer.shadowMap.needsUpdate=true}catch{renderer=new SVGRenderer();renderer.setPrecision(2);software=true}
  renderer.setClearColor(new THREE.Color(0x0a2233),1);el.appendChild(renderer.domElement);
  renderer.domElement.setAttribute("aria-label","설명용 입체 선박과 바다. 드래그 회전, 휠 또는 두 손가락으로 확대·축소.");renderer.domElement.setAttribute("role","img");
  const scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x0a2333,.007);const camera=new THREE.PerspectiveCamera(37,1,.1,900);
  const hemisphere=new THREE.HemisphereLight(0xc3dfeb,0x172b38,2);scene.add(hemisphere);const cadAmbient=new THREE.AmbientLight(0xffffff,0);scene.add(cadAmbient);const sun=new THREE.DirectionalLight(0xffedcf,3);sun.position.set(15,30,-18);scene.add(sun);const rim=new THREE.DirectionalLight(0x84c6df,1.8);rim.position.set(-22,12,20);scene.add(rim);
  // The model is static. Cache one small shadow map; camera movement needs no shadow rerender.
  sun.castShadow=!software;sun.shadow.mapSize.setScalar(compact?512:1024);Object.assign(sun.shadow.camera,{left:-20,right:20,top:20,bottom:-20,near:1,far:80});sun.shadow.camera.updateProjectionMatrix();sun.shadow.normalBias=.04;sun.shadow.bias=-.0003;
  const water=new THREE.ShaderMaterial({uniforms:{time:{value:0}},vertexShader:`
    varying vec3 world; uniform float time;
    void main(){vec4 w=modelMatrix*vec4(position,1.);
      w.y+=.14*sin(w.x*.24+time*.36)*cos(w.z*.18-time*.2);
      world=w.xyz;gl_Position=projectionMatrix*viewMatrix*w;
    }`,fragmentShader:`
    varying vec3 world; uniform float time;
    void main(){
      float a=world.x*.24+time*.36;float b=world.z*.18-time*.2;
      float r=world.x*1.6+world.z*.9+time*.55;
      vec3 n=normalize(vec3(-.0336*cos(a)*cos(b)-.035*cos(r),1.,.0252*sin(a)*sin(b)-.02*cos(r)));
      vec3 view=normalize(cameraPosition-world);vec3 light=normalize(vec3(15.,30.,-18.));
      float fresnel=pow(1.-max(dot(n,view),0.),4.);
      float glint=pow(max(dot(n,normalize(light+view)),0.),110.);
      vec3 sea=mix(vec3(.018,.085,.12),vec3(.12,.23,.29),fresnel*.65);
      sea+=vec3(.40,.49,.48)*glint*.32;
      // Static contact shading grounds the explanatory hull; this is not an attack footprint.
      float contact=exp(-pow(abs(world.x)/14.,6.)-pow(abs(world.z)/3.2,4.));sea*=1.-contact*.3;
      sea=mix(vec3(.033,.105,.15),sea,exp(-length(world.xz)*.008));
      gl_FragColor=vec4(sea,1.);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`});
  const segments=compact?64:96;
  const ocean=new THREE.Mesh(new THREE.PlaneGeometry(450,450,segments,segments),water);ocean.rotation.x=-Math.PI/2;ocean.position.y=-.18;ocean.visible=!software;scene.add(ocean);
  const waves:THREE.Line[]=[];
  if(software){for(let z=-75;z<76;z+=3){const points=[];for(let x=-100;x<101;x+=4)points.push(new THREE.Vector3(x,-.4+Math.sin(x*.4+z*.3)*.06,z));const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:0x205165,transparent:true,opacity:.32}));scene.add(line);waves.push(line)}}
  const ship=new THREE.Group();scene.add(ship);let part:ShipPart="deck";
  const tag=<T extends THREE.Object3D,>(object:T,group:ShipPart=part):T=>{object.userData.shipPart=group;return object};
  const materials:THREE.Material[]=[];function mat(color:number,metal=.15,rough=.56){const m=new THREE.MeshStandardMaterial({color,roughness:rough,metalness:metal});materials.push(m);return m;}
  const hullMat=mat(0x657f8c,.42,.36),deckMat=mat(0x394e59,.12,.87),lightMat=mat(0x9fadb0,.25,.48),darkMat=mat(0x102735,.45,.24),lineMat=mat(0xcac7b3,.05,.8),accentMat=mat(0x92b3bd,.5,.32);
  function box(w:number,h:number,d:number,x:number,y:number,z:number,m:THREE.Material){const o=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),m);o.position.set(x,y,z);o.castShadow=h>.3;o.receiveShadow=true;ship.add(tag(o));return o}
  const outline=[[-13,-2.1],[-13,2.1],[8.8,2.3],[12.2,1.35],[14,0],[12.2,-1.35],[8.8,-2.3]];
  const verts:number[]=[],idx:number[]=[];for(const [x,z]of outline)verts.push(x,.0,z*.67);for(const [x,z]of outline)verts.push(x,1.45,z);
  const count=outline.length;for(let i=0;i<count;i++){const j=(i+1)%count;idx.push(i,j,j+count,i,j+count,i+count)}
  const geo=new THREE.BufferGeometry();geo.setAttribute("position",new THREE.Float32BufferAttribute(verts,3));geo.setIndex(idx);geo.computeVertexNormals();hullMat.side=THREE.DoubleSide;const hull=new THREE.Mesh(geo,hullMat);hull.castShadow=true;hull.receiveShadow=true;ship.add(tag(hull,"hull"));
  const shape=new THREE.Shape();outline.forEach(([x,z],i)=>i?shape.lineTo(x,-z):shape.moveTo(x,-z));shape.closePath();const deck=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:.18,bevelEnabled:true,bevelThickness:.025,bevelSize:.025,bevelSegments:1}),deckMat);deck.rotation.x=-Math.PI/2;deck.position.y=1.44;deck.receiveShadow=true;ship.add(tag(deck,"deck"));
  // Batched deck joints and tie-down marks add scale without textures or many draw calls.
  const detailPoints:THREE.Vector3[]=[];
  for(let x=-12;x<9;x+=2){detailPoints.push(new THREE.Vector3(x,1.651,-1.85),new THREE.Vector3(x,1.651,1.85));for(const z of [-1.05,.1]){detailPoints.push(new THREE.Vector3(x-.045,1.653,z),new THREE.Vector3(x+.045,1.653,z),new THREE.Vector3(x,1.653,z-.045),new THREE.Vector3(x,1.653,z+.045))}}
  const detailMat=new THREE.LineBasicMaterial({color:0x8aa4ad,transparent:true,opacity:.28});materials.push(detailMat);ship.add(tag(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(detailPoints),detailMat),"deck"));
  const seamPoints:THREE.Vector3[]=[];for(const y of [.45,1.12]){const scale=.67+.33*y/1.45;outline.forEach(([x,z],i)=>{const next=outline[(i+1)%outline.length];seamPoints.push(new THREE.Vector3(x,y,z*scale*1.005),new THREE.Vector3(next[0],y,next[1]*scale*1.005))})}
  ship.add(tag(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(seamPoints),detailMat),"hull"));
  box(17,.035,.065,-1,1.67,-1.45,lineMat);box(17,.035,.065,-1,1.67,.75,lineMat);
  for(let x=-11;x<10;x+=1.5)box(.65,.03,.055,x,1.675,-.37,lineMat);
  // Railings follow the hull perimeter, including the tapered bow.
  const rails:THREE.Vector3[]=[];
  outline.forEach(([x,z],i)=>{const [nx,nz]=outline[(i+1)%outline.length];
   const length=Math.hypot(nx-x,nz-z),steps=Math.ceil(length/.9);
   for(const height of [1.86,2.07])rails.push(new THREE.Vector3(x*.97,height,z*.96),new THREE.Vector3(nx*.97,height,nz*.96));
   for(let j=0;j<steps;j++){const t=j/steps;const px=(x+(nx-x)*t)*.97,pz=(z+(nz-z)*t)*.96;rails.push(new THREE.Vector3(px,1.65,pz),new THREE.Vector3(px,2.07,pz))}
  });
  const railMaterial=new THREE.LineBasicMaterial({color:0xa4bac4});materials.push(railMaterial);
  ship.add(tag(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(rails),railMaterial),"deck"));
  function cylinder(radius:number,height:number,x:number,y:number,z:number,m:THREE.Material){const mesh=new THREE.Mesh(new THREE.CylinderGeometry(radius,radius,height,12),m);mesh.position.set(x,y,z);mesh.castShadow=true;ship.add(tag(mesh));return mesh;}
  // Mooring fittings and service hatches give the illustrative model a readable scale.
  for(const x of [-11.5,8.3])for(const z of [-1.5,1.5]){box(.75,.09,.42,x,1.7,z,darkMat);for(const dx of [-.23,.23]){cylinder(.085,.26,x+dx,1.84,z,lightMat);cylinder(.13,.05,x+dx,1.98,z,lightMat)}}
  for(const x of [1.5,4,6.5]){box(1.5,.06,.8,x,1.7,1.25,hullMat);box(.38,.035,.05,x,1.75,1.25,accentMat)}
  for(let x=-11;x<8;x+=1.35){const port=cylinder(.11,.025,x,1.05,-2.13,darkMat);port.rotation.x=Math.PI/2;port.userData.shipPart="hull";}
  // Boarding stair treads and the bridge service platform remain static.
  for(let i=0;i<7;i++)box(.4,.10,.54,-5.8+i*.24,1.78+i*.22,1.25,lightMat);
  part="upper";
  box(4.8,.12,1.65,-3,3.35,1.23,lightMat);
  box(4.4,1.9,1.2,-3,2.5,1.28,hullMat);box(3.5,.72,1.35,-2.6,3.68,1.28,lightMat);box(2.8,.5,1.5,-2.3,4.24,1.28,darkMat);box(3.1,.12,1.68,-2.3,4.56,1.28,lightMat);box(1.5,.85,.9,-3.4,4.2,1.28,hullMat);
  for(let x=-3.55;x<-.9;x+=.38)box(.045,.48,1.54,x,4.24,1.28,lightMat);
  box(.15,3.1,.15,-3.6,5.45,1.28,accentMat);box(2,.08,.08,-3.6,6.1,1.28,accentMat);box(.08,.08,1.5,-3.6,6.6,1.28,accentMat);box(.08,1.4,.08,-1.7,5.27,1.28,accentMat);
  const radar=new THREE.Mesh(new THREE.SphereGeometry(.32,16,12),lightMat);radar.position.set(-3.6,7.13,1.28);ship.add(tag(radar));part="deck";
  // Small deck service structures, not weapon or attack effects.
  for(let x=-10;x<-5;x+=2){box(.8,.28,.55,x,1.8,1.25,lightMat);box(.5,.2,.45,x+.05,2.02,1.25,darkMat)}
  const glows=new THREE.MeshBasicMaterial({color:0xa1e5d4});materials.push(glows);
  for(let x=-12;x<13;x+=2.2)box(.09,.035,.09,x,1.72,-1.96,glows);
  // Ocean guides denote the illustrative workspace, not sensed targets or a route.
  const guides:THREE.Line[]=[];
  for(const radius of [22,33]){const points=[];for(let i=0;i<=100;i++){const a=i/100*Math.PI*2;points.push(new THREE.Vector3(Math.cos(a)*radius,-.05,Math.sin(a)*radius))}const m=new THREE.LineBasicMaterial({color:0x56828f,transparent:true,opacity:.13});materials.push(m);const guide=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),m);scene.add(guide);guides.push(guide)}
  const cad=createCadDisplay(ship);
  const grid=new THREE.GridHelper(64,32,0x9ba5ab,0xc2cace);if(software){const gridMaterials=Array.isArray(grid.material)?grid.material:[grid.material];gridMaterials.forEach(m=>{m.vertexColors=false;m.color.setHex(0xa4afb5)})}(Array.isArray(grid.material)?grid.material:[grid.material]).forEach(m=>{m.transparent=true;m.opacity=.45});grid.position.y=-.4;grid.visible=false;scene.add(grid);
  let lastMode:SceneMode|undefined,lastSelection:CadSelection|undefined;
  let needsRender=true;
  const resize=()=>{const width=el.clientWidth,height=el.clientHeight;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();needsRender=true};const ro=new ResizeObserver(resize);ro.observe(el);resize();
  const controls=createShipControls(camera,el),initialDistance=controls.getDistance();
  const start=()=>{active.current=false;controls.autoRotate=false;callbacks.current.onInteract()};
  const change=()=>{needsRender=true;callbacks.current.onZoom(Math.round(initialDistance/controls.getDistance()*10)/10)};
  controls.addEventListener("start",start);controls.addEventListener("change",change);
  let frame=0,time=0,last=performance.now(),lastCommand=commandRef.current.id;
  const loss=(e:Event)=>{e.preventDefault();setFailed(true);cancelAnimationFrame(frame)};renderer.domElement.addEventListener("webglcontextlost",loss);
  const draw=(now:number)=>{frame=requestAnimationFrame(draw);if(now-last<(software?65:compact?32:0))return;const dt=Math.min((now-last)/1000,.1);last=now;
   if(lastCommand!==commandRef.current.id){start();if(commandRef.current.kind==="reset"){resetShipControls(controls);}else if(["bow","side","deck"].includes(commandRef.current.kind)){setShipView(controls,camera,commandRef.current.kind as "bow"|"side"|"deck");}else{const distance=THREE.MathUtils.clamp(controls.getDistance()*(commandRef.current.kind==="in"?.8:1.25),controls.minDistance,controls.maxDistance);camera.position.sub(controls.target).setLength(distance).add(controls.target)}lastCommand=commandRef.current.id;change()}
   const display=displayRef.current;
   if(display.mode!==lastMode||display.selection!==lastSelection){
    const isCad=display.mode==="cad";cad.set(display.mode,display.selection);grid.visible=isCad;
    scene.fog=isCad?null:new THREE.FogExp2(0x0a2333,.007);sun.intensity=isCad?1.7:3;rim.intensity=isCad?.65:1.8;sun.color.setHex(isCad?0xffffff:0xffedcf);rim.color.setHex(isCad?0xffffff:0x84c6df);hemisphere.color.setHex(isCad?0xffffff:0xc3dfeb);hemisphere.groundColor.setHex(isCad?0x6b7378:0x172b38);cadAmbient.intensity=isCad?.65:0;
    ocean.visible=!isCad&&!software;waves.forEach(line=>{line.visible=!isCad});guides.forEach(line=>{line.visible=!isCad});
    renderer.setClearColor(new THREE.Color(isCad?0xdde3e6:0x0a2233),1);
    renderer.domElement.setAttribute("aria-label",isCad?"설명용 선박 CAD 구조 보기. 치수가 없는 모형이며 실제 설계도가 아닙니다.":"설명용 입체 선박과 바다. 드래그 회전, 휠 또는 두 손가락으로 확대·축소.");
    // Materials change but the actual geometry and cached shadow map are untouched.
    lastMode=display.mode;lastSelection=display.selection;needsRender=true;
   }
   controls.autoRotate=active.current&&!document.hidden;controls.update(dt);
   if(active.current&&!document.hidden){time+=dt;water.uniforms.time.value=time;waves.forEach((line,i)=>{line.position.y=Math.sin(time*.35+i*.7)*.08});needsRender=true}if(needsRender){renderer.render(scene,camera);needsRender=false}};frame=requestAnimationFrame(draw);
  return()=>{cancelAnimationFrame(frame);ro.disconnect();controls.removeEventListener("start",start);controls.removeEventListener("change",change);controls.dispose();renderer.domElement.removeEventListener("webglcontextlost",loss);cad.dispose();(Array.isArray(grid.material)?grid.material:[grid.material]).forEach(m=>m.dispose());scene.traverse(o=>{if((o as THREE.Mesh).geometry)(o as THREE.Mesh).geometry.dispose()});materials.forEach(m=>m.dispose());waves.forEach(w=>(w.material as THREE.Material).dispose());water.dispose();sun.shadow.dispose();if(renderer instanceof THREE.WebGLRenderer)renderer.dispose();renderer.domElement.remove()};
 },[]);
 return <div className="ocean-host" ref={host} aria-label="선박 조작 영역">{failed&&<div className="ocean-fallback" role="status">이 기기에서는 3D 장면을 표시할 수 없습니다.<br/>아래 실제 이미지와 결과 비교는 계속 이용할 수 있습니다.</div>}</div>;
}

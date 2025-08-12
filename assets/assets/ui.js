// assets/ui.js
// Retro cursor + small helpers; shared by all pages
(function(){
  const cursor=document.createElement('div');
  cursor.className='crt-cursor';
  document.body.appendChild(cursor);

  const hotspotX=2, hotspotY=2;
  let x=innerWidth/2,y=innerHeight/2,tx=x,ty=y; const speed=.35;
  function move(e){tx=e.clientX-hotspotX;ty=e.clientY-hotspotY;}
  function loop(){x+=(tx-x)*speed;y+=(ty-y)*speed;cursor.style.left=x+'px';cursor.style.top=y+'px';requestAnimationFrame(loop);}
  addEventListener('mousemove',move,{passive:true});
  addEventListener('mousedown',()=>cursor.classList.add('click'));
  addEventListener('mouseup',()=>cursor.classList.remove('click'));
  loop();

  // Show a normal cursor when focusing inputs/links for usability
  document.querySelectorAll('input,textarea,select,button,a').forEach(el=>{
    el.addEventListener('mouseenter',()=>{document.body.style.cursor='default';});
    el.addEventListener('mouseleave',()=>{document.body.style.cursor='none';});
  });
})();

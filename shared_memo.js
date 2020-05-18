//
// shared_memo.js
//
var VERSION_shared_memo = "0.0.1"; // Time-stamp: <2020-05-18T01:12:30Z>

//
// Author:
//
//   JRF ( http://jrf.cocolog-nifty.com/statuses/ )
//
// Repository:
//
//   https://github.com/JRF-2018/shared_memo
//
// License:
//
//   The author is a Japanese.
//
//   I intended this program to be public-domain, but you can treat
//   this program under the (new) BSD-License or under the Artistic
//   License, if it is convenient for you.
//
//   Within three months after the release of this program, I
//   especially admit responsibility of efforts for rational requests
//   of correction to this program.
//
//   I often have bouts of schizophrenia, but I believe that my
//   intention is legitimately fulfilled.
//

var MEMO_MAX = 2000;
var CLIENT_HEIGHT = 0;
var IFRAME_ID;

function add_event_listener(obj, ev, func) {
  if (window["addEventListener"]) { //for W3C DOM
    obj.addEventListener(ev, func, false);
  } else if (window["attachEvent"]) { //for IE
    obj.attachEvent("on" + ev, func);
  } else  {
    obj["on" + ev] = func;
  }
}

// 参考: 《iframeの高さを判別して自動的に調整する(JavaScript) | 己で解決！泣かぬなら己で鳴こうホトトギス》  
// https://onoredekaiketsu.com/iframe-height-adjust-javascript/

function sendHeight() {
  var h = document.getElementsByTagName('body')[0].clientHeight;
  if (CLIENT_HEIGHT != h) {
    parent.postMessage({id: IFRAME_ID, height: h + 20}, "*");
  }
  CLIENT_HEIGHT = h;
}

function limit_char() {
  var t = document.getElementById('txt');
  var c = document.getElementById('char-count');
  var b = document.getElementById('write');
  l = t.value.length;
  c.innerHTML = l + "/" + MEMO_MAX;
  if (l > MEMO_MAX) {
    c.style.color = "red";
    b.disabled = true;
  } else {
    c.style.color = "gray";
    b.disabled = false;
  }
}

function init(child) {
  var txt = document.getElementById('txt');
  if (child != '') {
    IFRAME_ID = child;
    setTimeout(sendHeight, 100);
    add_event_listener(window, 'resize', function () {
      setTimeout(sendHeight, 500);
    });
    add_event_listener(window, 'mouseup', function () {
      setTimeout(sendHeight, 100);
    });
  }
  if (txt) {
    limit_char();
    add_event_listener(txt, 'keyup', limit_char);
    add_event_listener(txt, 'change', limit_char);
  }
}

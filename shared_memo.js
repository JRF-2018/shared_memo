//
// shared_memo.js
//
var VERSION_shared_memo = "0.0.9"; // Time-stamp: <2020-08-10T17:11:38Z>

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
var MEMO_MAX_LINE = 100;
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
  var l = t.value.length;
  var ln = t.value.match(/\n/g);
  ln = ((ln)? ln.length : 0) + ((t.value.match(/\n$/))? 0 : 1);
  c.innerHTML = l + "/" + MEMO_MAX;
  if (l > MEMO_MAX || ln > MEMO_MAX_LINE) {
    c.style.color = "red";
    b.disabled = true;
  } else {
    c.style.color = "gray";
    if (! WRITE_DISABLED) {
      b.disabled = false;
    }
  }
}

function verifyCallback(response) {
  if (response) {
    document.getElementById("write-form").submit();
  }
}

function checkSubmit() {
  if (! USE_RECAPTCHA) {
    return true;
  }

  document.getElementById('write-main').style.display = 'none';
  grecaptcha.render(document.getElementById('captcha'), {
    'sitekey' : RECAPTCHA_SITE_KEY,
    'size': 'compact' /*'normal'*/,
    'callback': verifyCallback
  });

  return false;
}

function init(child) {
  document.getElementById('write').disabled = true;
  var txt = document.getElementById('txt');
  if (txt) {
    setTimeout(limit_char, 500);
    add_event_listener(txt, 'keyup', limit_char);
    add_event_listener(txt, 'change', limit_char);
  }

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
}

//
// shared_memo_log.js
//
var VERSION_shared_memo = "0.0.8"; // Time-stamp: <2020-06-25T13:52:54Z>

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

function selectReason(i) {
  var reason = document.getElementById('select-' + i).value;
  if (reason == "none") {
    document.getElementById('button-' + i).disabled = true;
  } else {
    document.getElementById('button-' + i).disabled = false;
//    document.getElementById('delete-form-' + i).submit();
  }
}

function verifyCallback(response) {
  if (response) {
    document.getElementById("delete-form-" + this.i).submit();
  }
}

function verifySignCallback(response) {
  if (response) {
    document.getElementById("sign-form").submit();
  }
}

function checkSubmit(i) {
  if (document.getElementById('select-' + i).value != "none") {
    if (! USE_RECAPTCHA) {
      return true;
    }

    document.getElementById('button-' + i).disabled = true;
    grecaptcha.render(document.getElementById('captcha-' + i), {
      'sitekey' : RECAPTCHA_SITE_KEY,
      'size': /* 'compact' */ 'normal',
      'callback': verifyCallback.bind({i: i})
    });
    return false;
  }
  document.getElementById('button-' + i).disabled = true;
  document.getElementById('select-' + i).style.display = 'inline';
  return false;
}

function checkSignSubmit() {
  if (! USE_RECAPTCHA) {
    return true;
  }
  
  document.getElementById('sign-button').disabled = true;
  grecaptcha.render(document.getElementById('captcha-sign'), {
    'sitekey' : RECAPTCHA_SITE_KEY,
    'size': /* 'compact' */ 'normal',
    'callback': verifySignCallback
  });
  return false;
}

function init() {
  var i;
  var l = document.getElementsByTagName('select');
  for (i = 0; i < l.length; i++) {
    l[i].style.display = 'none';
  }
//  l = document.getElementsByTagName('pre');
//  for (i = 0; i < l.length; i++) {
//    l[i].innerHTML = l[i].innerHTML.replace(/　/g, "<span style=\"background: #f7ffff\">　</span>");
//  }
}

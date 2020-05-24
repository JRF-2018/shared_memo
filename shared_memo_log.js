//
// shared_memo_log.js
//
var VERSION_shared_memo = "0.0.3"; // Time-stamp: <2020-05-23T05:21:46Z>

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

function checkSelect(i) {
  if (document.getElementById('select-' + i).value != "none") {
    return true;
  }
  document.getElementById('button-' + i).disabled = true;
  document.getElementById('select-' + i).style.display = 'inline';
  return false;
}

function selectReason(i) {
  var reason = document.getElementById('select-' + i).value;
  if (reason == "none") {
    document.getElementById('button-' + i).disabled = true;
  } else {
    document.getElementById('button-' + i).disabled = false;
//    document.getElementById('delete-form-' + i).submit();
  }
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

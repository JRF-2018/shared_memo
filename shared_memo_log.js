//
// shared_memo_log.js
//
var VERSION_shared_memo = "0.1.1"; // Time-stamp: <2020-12-02T09:10:43Z>

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

var SEARCH_URL = "https://www.google.com/search?hl=en&safe=off&lr=lang_ja&pws=0&q=";
//var ARTICLE_ID_SEARCHER = "http://jrf.cocolog-nifty.com/statuses/jumpbytitle.html?q=";
var ARTICLE_ID_SEARCHER = SEARCH_URL;
var LOCAL_LINK = {};

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

function is_kanji(c){ // c:判別したい文字
    var unicode = c.charCodeAt(0);
    if ( (unicode>=0x3005  && unicode<=0x3006)  || //「々」と「〆」
         (unicode>=0x4e00  && unicode<=0x9fcf)  || // CJK統合漢字
         (unicode>=0x3400  && unicode<=0x4dbf)  || // CJK統合漢字拡張A
         (unicode>=0x20000 && unicode<=0x2a6df) || // CJK統合漢字拡張B
         (unicode>=0xf900  && unicode<=0xfadf)  || // CJK互換漢字
         (unicode>=0x2f800 && unicode<=0x2fa1f) )  // CJK互換漢字補助
//	 (unicode>=0x3190 && unicode<=0x319f) ) // 漢文用の記号

        return true;
    return false;
}

function format_url_string(html) {
  var s;

  for (s = html, html = ""; s.match(/(?:https?|ftp)(?::\/\/[-_.!~*\'()a-zA-Z0-9;\/?:\@&=+\$,%#]+)/m);) {
    html += RegExp.leftContext;
    s = RegExp.rightContext;
    var href = RegExp.lastMatch;
    if (html.match(/<[^<>]*$/)) {
      html += href;
      continue;
    }

    if (href.match(/[\.\!\'\?\:\;\,]+$/)) {
      href = RegExp.leftContext;
      s = RegExp.lastMatch + s;
    }
    
    if (href.match(/\)$/)) {
      if (! href.match(/\(/)) {
	s = href.substring(href.length - 1) + s;
	href = href.substring(0, href.length - 1);
      }
    }

    html += "<a class=\"decorated url\" href=\"" + href + "\">" + href + "</a>";
  }
  html += s;

  return html;
}

function format_escape_bracket(s) {
  var html = "";
  while (s.match(/\[([^\[\]]*)\]/m)) {
    var l = RegExp.leftContext;
    s = RegExp.rightContext;
    var c = RegExp.$1;
    if ((html + l).match(/<[^<>]*$/)) {
      html += l + "[" + c + "]";
      continue;
    }
    var done = false;
    if (! c.match(/^\w+\:/) && l.match(/(\S+)$/)) {
      l = RegExp.leftContext;
      var k = RegExp.$1;
      var i = k.length;
      while (i > 0 && is_kanji(k.charAt(i - 1))) {
	i--;
      }
      l += k.substring(0, i);
      if (i < k.length) {
	k = k.substring(i, k.length);
	l += "<ruby><rb>" + k + "</rb><rp>[</rp>"
	  + "<rt>" + c + "</rt><rp>]</rp></ruby>";
	done = true;
      }
    }
    html += l;
    if (! done) {
      if (c.match(/^ruby\:(.*):(.*)$/)) {
	html += "<ruby><rp>[ruby:</rp><rb>" + RegExp.$1 + "</rb><rp>:</rp>"
	  + "<rt>" + RegExp.$2 + "</rt><rp>]</rp></ruby>";
      } else if (c.match(/^(?:cocolog|aboutme)\:(.*)$/)) {
	html += "[<a class=\"decorated article-id\" href=\""
	  + ARTICLE_ID_SEARCHER + encodeURIComponent(c) + "\">" + c + "</a>]";
      } else if (c.match(/^google\:(.*)$/)) {
	html += "[google:<a class=\"decorated google\" href=\""
	  + SEARCH_URL + encodeURIComponent(RegExp.$1)
	  + "\">" +  RegExp.$1 + "</a>]";
      } else if (c.match(/^wikipedia\:(.*)$/)) {
	var x = RegExp.$1;
	var reg = "ja";
	var regs = "";
	if (x.match(/^([a-z01-9_\-]+)\:/)) {
	  reg = RegExp.$1;
	  regs = reg + ":";
	  x = RegExp.rightContext;
	}
	html += "[wikipedia:" + regs
	  + "<a class=\"decorated wikipedia\" href=\""
	  + "http://" + reg + ".wikipedia.org/wiki/:Search?search="
	  + encodeURIComponent(x) + "\">" + x + "</a>]";
      } else {
	html += "[" + c + "]";
      }
    }
  }
  html += s;

  return html;
}

function format_local_link(s) {
  var html = "";
  while (s.match(/(\&gt;\&gt;)/)) {
    html += RegExp.leftContext;
    s = RegExp.rightContext;
    var m = RegExp.$1;
    var l = "";
    if (s.match(/^( ?([01-9]+-[01-9]+-[01-9]+T[01-9]+:[01-9]+:[01-9]+Z [A-Za-z01-9\+\/]+))/)) {
      m += RegExp.$1;
      l = RegExp.$2;
      s = RegExp.rightContext;
    } else if (s.match(/^( ?([01-9]+-[01-9]+-[01-9]+T[01-9]+:[01-9]+:[01-9]+Z))/)) {
      m += RegExp.$1;
      l = RegExp.$2;
      s = RegExp.rightContext;
    } else if (s.match(/^( ?([A-Za-z01-9\+\/]+))/)) {
      m += RegExp.$1;
      l = RegExp.$2;
      s = RegExp.rightContext;
    }
    if (l == "") {
      html += m;
    } else {
      if (LOCAL_LINK[l]) {
	html += "<a class=\"decorated local\" href=\"" + LOCAL_LINK[l]
	  + "\">"+ m +"</a>";
      } else {
	html += m;
      }
    }
  }
  html += s;
  return html;
}

function format_memo() {
  var i;
  var l = document.querySelectorAll("div.memo");
  for (i = 0; i < l.length; i++) {
    var div = l[i];
    var id = "#" + div.id;
    var datetime = div.querySelector(".datetime");
    datetime = datetime.textContent || datetime.innerText;
    var hash = div.querySelector(".hash");
    hash = hash.textContent || hash.innerText;
    var dh = datetime + " " + hash;
    if (! LOCAL_LINK[datetime]) {
      LOCAL_LINK[datetime] = id;
    }
    if (! LOCAL_LINK[hash]) {
      LOCAL_LINK[hash] = id;
    }
    if (! LOCAL_LINK[dh]) {
      LOCAL_LINK[dh] = id;
    }
  }

  for (i = 0; i < l.length; i++) {
    var div = l[i];
    var pre = div.querySelector("pre");
    var s = pre.innerHTML;
    s = format_url_string(s);
    s = format_escape_bracket(s);
    s = format_local_link(s);
    pre.innerHTML = s;
  }
}

function init() {
  var i;
  var l = document.getElementsByTagName('select');
  for (i = 0; i < l.length; i++) {
    l[i].style.display = 'none';
  }
  format_memo();
//  l = document.getElementsByTagName('pre');
//  for (i = 0; i < l.length; i++) {
//    l[i].innerHTML = l[i].innerHTML.replace(/　/g, "<span style=\"background: #f7ffff\">　</span>");
//  }
}


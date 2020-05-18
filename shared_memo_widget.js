//
// shared_memo_widget.js
//
var VERSION_shared_memo_widget = "0.0.1"; // Time-stamp: <2020-05-18T01:28:19Z>

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


(function () {
  var CGI = "http://jrockford.s1010.xrea.com/demo/shared_memo.cgi";

  var origin = CGI.replace(/^(https?:\/\/[^\/]+)\/.*/, "$1");
  
  var auto_width = 1;
  var width = 200;
  var rows = 8;
  var id;
  var i = 0;

  while (1) {
    if (! document.getElementById("shared_memo_widget_" + i)) {
      id = "shared_memo_widget_" + i;
      break;
    }
    i++;
  }

  if (window["SHARED_MEMO_WIDGET_WIDTH"]
      && typeof SHARED_MEMO_WIDGET_WIDTH == 'number') {
    width = SHARED_MEMO_WIDGET_WIDTH;
    auto_width = 0;
  }

  if (window["SHARED_MEMO_WIDGET_ROWS"]
      && typeof SHARED_MEMO_WIDGET_ROWS == 'number') {
    rows = SHARED_MEMO_WIDGET_ROWS;
  }

  var resize;
  var resize_w;
  if ((function () {})["bind"]) {
    resize = (function () {
      var x = document.getElementById(this.id);
      x.width = Math.floor(x.parentNode.clientWidth * 0.95);
    }).bind({id: id});

    resize_w = (function () {
      setTimeout(this.resize, 500);
    }).bind({resize: resize});
  }

  if (window["addEventListener"]) {
    window.addEventListener('message', (function (e) {
      if (e.origin == this.origin
	 && e.data.id == this.id) {
	document.getElementById(this.id).height = e.data.height;
      }
    }).bind({id: id, origin: origin}));

    if (auto_width && resize) {
      window.addEventListener('load', resize, false);
      window.addEventListener('resize', resize_w, false);
    }
  }

  document.write('<iframe class="shared-memo-widget" '
		 + 'height="250" width="' + width
		 + '" id="' + id
		 + '" src="' + CGI + '?child='
		 + id + '&amp;rows=' + rows
		 + '" frameborder="no"></iframe>\n');
})();

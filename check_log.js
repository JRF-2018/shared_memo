//
// check_log.js
//
var VERSION_shared_memo = "0.0.8"; // Time-stamp: <2020-06-29T21:21:48Z>

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

function verifyCallback(response) {
  if (response) {
    document.getElementById(this.id + "-form").submit();
  }
}

function checkSubmit(id) {
  if (! USE_RECAPTCHA) {
    return true;
  }

  document.getElementById(id + '-submit').disabled = true;
  grecaptcha.render(document.getElementById(id + '-captcha'), {
    'sitekey' : RECAPTCHA_SITE_KEY,
    'size': 'normal' /*'compact'*/,
    'callback': verifyCallback.bind({id: id})
  });

  return false;
}

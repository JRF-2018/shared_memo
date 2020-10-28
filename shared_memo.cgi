#!/usr/bin/perl
our $VERSION = "0.1.0"; # Time-stamp: <2020-10-23T00:45:16Z>";

##
## Author:
##
##   JRF ( http://jrf.cocolog-nifty.com/statuses/ )
##
## Repository:
##
##   https://github.com/JRF-2018/shared_memo
##
## License:
##
##   The author is a Japanese.
##
##   I intended this program to be public-domain, but you can treat
##   this program under the (new) BSD-License or under the Artistic
##   License, if it is convenient for you.
##
##   Within three months after the release of this program, I
##   especially admit responsibility of efforts for rational requests
##   of correction to this program.
##
##   I often have bouts of schizophrenia, but I believe that my
##   intention is legitimately fulfilled.
##

use strict;
use warnings;
use utf8; # Japanese

use CGI;
use Encode qw(encode decode);
use Fcntl qw(:DEFAULT :flock :seek);
use URI::Escape qw(uri_escape uri_unescape);
use Digest::SHA1;
use Digest::HMAC_SHA1;
use JSON qw(decode_json);
use Time::Piece;

our $TITLE = "グローバル共有メモ"; ## or "街角白板１号"
our $DEFAULT_ROWS = 8;
our $DELETABLE_HOUR = 18;
our @WRITABLE_IP = ();
our @HIDE_IP_IP = ();
our @DISABLE_SIGN_IP = ();
our $MEMO_XML = "shared_memo.xml";
our $LOG = "shared_memo.log";
our $JS = "shared_memo.js";
our $LOG_JS = "shared_memo_log.js";
our $LOG_QR = "shared_memo_log.png";
our $CSS = "shared_memo.css";
our $PROGRAM = "shared_memo.cgi";
our $KEY_FILE = "shared_memo_key.xml";
our $MEMO_MAX = 2000;
our $MEMO_MAX_LINE = 100;
our $MEMO_NUM = 200;
our $LOG_MAX = 10000000;
our $LOG_TRUNCATE = 7000000;
our $COOKIE_SID = "shared_memo_cgi__session_id";
our $COOKIE_NICKNAME = "shared_memo_cgi__nickname";
our $COOKIE_PATH = "/";
our $HASH_VERSION = "0.0.8.3";

our $USE_RECAPTCHA = 0;
our $RECAPTCHA_API = "https://www.google.com/recaptcha/api/siteverify";
our $RECAPTCHA_SECRET_KEY = "__Your_Secret_Key__";
our $RECAPTCHA_SITE_KEY = "__Your_Site_Key__";

our $DATETIME = datetime();
our $DATETIME_PIECE = Time::Piece->strptime($DATETIME, '%Y-%m-%dT%H:%M:%SZ');
our $REMOTE_ADDR = remote_addr();
our $KEY;
our $NICKNAME;
our $SESSION_ID;
our $SUM_HASH;

our $CGI = CGI->new;
binmode(STDOUT, ":utf8");

$SIG{__DIE__} = sub {
  my $message = shift;
  print $CGI->header(-type => 'text/html',
		     -charset => 'utf-8',
		     -status => '500 Internal Server Error');
  print <<"EOT";
<\!DOCTYPE html>
<html>
<head>
<title>ERROR</title>
</head>
<body>
<p>Die: $message</p>
</body>
</html>
EOT
  exit(1);
};

sub datetime { # ISO 8601 extended format.
  my ($sec, $min, $hour, $mday, $mon, $year, $wday) = gmtime(time);
  $year += 1900;
  $mon ++;
  return sprintf("%d-%02d-%02dT%02d:%02d:%02dZ",
		 $year, $mon, $mday, $hour, $min, $sec);
}

sub remote_addr {
  my $r;
  $r = $ENV{REMOTE_ADDR} if exists $ENV{REMOTE_ADDR};
  $r = ($r || '') . "($ENV{HTTP_X_FORWARDED_FOR})"
    if exists $ENV{HTTP_X_FORWARDED_FOR};
  $r = ($r || '') . "($ENV{HTTP_CLIENT_IP})"
    if exists $ENV{HTTP_CLIENT_IP};
  if (defined $r) {
    $r =~ s/[\s\&\"<>]/_/sg;
    $r = substr($r, 0, 128) if length($r) > 128;
  }
  return $r;
}

sub allot_magic {
  return substr(sprintf("%1.5f", rand(1)), 2, 4);
}

sub escape {
  my ($s) = @_;
  return uri_escape(encode('utf-8', $s), '^\w.~-');
}

sub unescape {
  my ($s) = @_;
  return decode('utf-8', uri_unescape($s, '^\w.~-'));
}

sub escape_html {
  my ($s) = @_;
  $s =~ s/\&/\&amp\;/sg;
  $s =~ s/</\&lt\;/sg;
  $s =~ s/>/\&gt\;/sg;
#  $s =~ s/\'/\&apos\;/sg;
  $s =~ s/\"/\&quot\;/sg;
  return $s;
}

sub unescape_html {
  my ($s) = @_;
  $s =~ s/\&quot\;/\"/sg;
#  $s =~ s/\&apos\;/\'/sg;
  $s =~ s/\&gt\;/>/sg;
  $s =~ s/\&lt\;/</sg;
  $s =~ s/\&amp\;/\&/sg;
  return $s;
}

## $SESSION_ID に日時を含めるのは、更新の10日前後以前に遡って攻撃がで
## きないように。
sub new_session_id {
  my @x;
  for (my $i = 0; $i < 16; $i++) {
    push(@x, int(rand(256)))
  }
  return unpack("H*", pack("C*", @x)) . ":" . $DATETIME;
}

sub gen_key {
  my $file = $KEY_FILE;
  my @x;
  for (my $i = 0; $i < 64; $i++) {
    push(@x, int(rand(256)))
  }
  $KEY = pack("C*", @x);
  my $s = unpack("H*", $KEY);
  sysopen(my $fh, $file, O_WRONLY | O_EXCL | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_EX)
    or die "Cannot lock $file: $!";
  binmode($fh);
  print $fh <<"EOT";
<keyinfo>
<key>$s</key>
<generated>$DATETIME</generated>
</keyinfo>
EOT
  flock($fh, LOCK_UN);
  close($fh);
  chmod(0600, $file);
}

sub read_key {
  my $file = $KEY_FILE;

  sysopen(my $fh, $file, O_RDONLY)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_SH)
    or die "Cannot lock $file: $!";
  binmode($fh);
  my $s = join("", <$fh>);
  flock($fh, LOCK_UN);
  close($fh);

  if ($s !~ /<key>([^<]+)<\/key>/s) {
    die "Key file is broken.";
  }
  $KEY = pack("H*", $1);
}

sub get_hash {
  my ($text, $ip) = @_;
  $text = encode('UTF-8', $text);
  $ip = encode('UTF-8', $ip);

  read_key() if ! defined $KEY;
  my $sha1 = Digest::SHA1->new;
  $sha1->add($text);
  my $a = substr($sha1->b64digest, 0, 2);
  my $hmac = Digest::HMAC_SHA1->new($KEY);
  $hmac->add($text);
  my $b = substr($hmac->b64digest, 0, 4);
  $hmac = Digest::HMAC_SHA1->new($KEY);
  $hmac->add($ip);
  my $c = substr($hmac->b64digest, 0, 4);
  return $a . $b . $c;
}

sub memo_read {
  my $file = $MEMO_XML;
  sysopen(my $fh, $file, O_RDONLY | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_SH)
    or die "Cannot lock $file: $!";
  my $memo;
  binmode($fh);
  my $mode = 0;
  while (my $s = <$fh>) {
    if ($s =~ /^<memo>/) {
      if ($mode == 0) {
	$mode = 1;
	$memo = "";
      } else {
	last;
      }
    } elsif ($mode) {
      $memo .= $s;
    }
  }
  flock($fh, LOCK_UN);
  close($fh);
  return "" if ! defined $memo;
  $memo = decode('UTF-8', $memo);
  return "" if $memo !~ /<text>([^<]*)<\/text>/s;
  return unescape_html($1);
}

sub parse_memo {
  my ($c) = @_;
  my $r = {};
  foreach my $n (qw(ip time magic hash text session_id deleted deleted_by)) {
    $r->{$n} = undef;
  }

  $c =~ s/<memo>//s;
  $c =~ s/<\/memo>//s;
  while ($c =~ s/<([^\/>]+)>([^<]*)<\/\1>//s) {
    if ($1 eq "text") {
      $r->{$1} = unescape_html($2);
    } else {
      $r->{$1} = $2;
    }
  }
  if (defined $r->{ip} && defined $r->{time} && defined $r->{magic}) {
    return $r;
  }
  return undef;
}

sub memo_read_all {
  my $file = $MEMO_XML;
  sysopen(my $fh, $file, O_RDONLY | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_SH)
    or die "Cannot lock $file: $!";
  binmode($fh);
  my $s = decode('UTF-8', join("", <$fh>));
  flock($fh, LOCK_UN);
  close($fh);
  my @memo;
  if ($s =~ /<\/top_info>\s*/s) {
    my $c = $` . $&;
    $s = $';
    if ($c =~ /<sum_hash>([^<]+)<\/sum_hash>\s*/s) {
      $SUM_HASH = $1;
    }
  }
  while ($s =~ /<\/memo>\s+/) {
    my $c = $` . $&;
    $s = $';
    my $x = parse_memo($c);
    push(@memo, $x) if defined $x;
  }
  return @memo;
}

sub memo_write {
  my ($text) = @_;

  my $time = $DATETIME;
  my $ip = $REMOTE_ADDR || '';
  my $magic = allot_magic();
  my $hash = get_hash($time . $text, $time . $ip);
  my $hmac = Digest::HMAC_SHA1->new($KEY);
  my $file = $MEMO_XML;
  sysopen(my $fh, $file, O_RDWR | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_EX)
    or die "Cannot lock $file: $!";
  binmode($fh);
  my $s = decode('UTF-8', join("", <$fh>));
  my @memo;
  $text = escape_html($text);
  $hmac->add($time . encode('UTF-8', $text) . $hash);
  push(@memo, "<memo>\n<ip>$ip</ip>\n"
       . "<time>$time</time>\n"
       . "<magic>$magic</magic>\n"
       . "<hash>$hash</hash>\n"
       . "<session_id>$SESSION_ID</session_id>\n"
       . "<text>$text</text>\n</memo>\n");
  while ($s =~ /<\/memo>\s+/) {
    my $c = $` . $&;
    $s = $';
    push(@memo, $c);
    my $dt;
    if ($c =~ /<time>([^<]*)<\/time>/) {
      $dt = $1;
    }
    my $text = "";
    if ($c =~ /<text>([^<]*)<\/text>/s) {
      $text = $1;
      $text =~ s/\x0d\x0a/\x0a/sg; # for old memo.
    }
    my $hash = "";
    if ($c =~ /<hash>([^<]*)<\/hash>/s) {
      $hash = $1;
    }
    $hmac->add($dt . encode('UTF-8', $text) . $hash);
  }
  $s = "";
  my $i = 0;
  foreach my $c (@memo) {
    $s .= $c;
    last if ++$i >= $MEMO_NUM;
  }
  $SUM_HASH = substr($hmac->b64digest, 0, 16);
  $s = "<top_info>\n"
    . "<sum_hash>$SUM_HASH</sum_hash>\n"
    . "</top_info>\n" . $s;

  seek($fh, 0, SEEK_SET)
    or die "Cannot seek $file: $!";
  print $fh encode('UTF-8', $s)
      or die "Cannot write $file: $!";
  truncate($fh, tell($fh))
      or die "Cannot truncate $file: $!";
  flock($fh, LOCK_UN);
  close($fh);

  return $magic;
}

sub memo_delete {
  my ($reason, $time, $magic) = @_;
  my $ip = $REMOTE_ADDR || "";
  my $hash = substr(get_hash($time . $reason, $time . $ip), 6);
  my $hmac = Digest::HMAC_SHA1->new($KEY);

  my $file = $MEMO_XML;
  sysopen(my $fh, $file, O_RDWR | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_EX)
    or die "Cannot lock $file: $!";
  binmode($fh);
  my $s = decode('UTF-8', join("", <$fh>));
  my @memo;
  while ($s =~ /<\/memo>\s+/) {
    my $c = $` . $&;
    $s = $';
    push(@memo, $c);
  }
  $s = "";
  my $i = 0;
  my $success = 0;
  foreach my $c (@memo) {
    if ($c =~ /<time>\Q$time\E<\/time>\s*<magic>\Q$magic\E<\/magic>/s) {
      my $deletable = 0;
      if ($c =~ /<session_id>([^<]*)<\/session_id>/) {
	my $session_id = $1;
	if ($SESSION_ID eq $session_id
	    || check_deletable_date($time)) {
	  $deletable = 1;
	}
      } else {
	$deletable = 1;
      }
      if ($deletable) {
	if ($c =~ s/<text>[^<]*<\/text>\s*/<deleted>$reason<\/deleted>\n<deleted_by>$SESSION_ID\@$ip<\/deleted_by>\n/s) {
	  if ($c =~ /<hash>([^<]*)<\/hash>\s*/) {
	    my $h1 = (length($1) >= 2)? substr($1, 0, 2) : "";
	    $c = $` . "<hash>$h1$hash</hash>\n" . $';
	  }
	  $success = 1;
	}
      }
    }
    my $dt;
    if ($c =~ /<time>([^<]*)<\/time>/) {
      $dt = $1;
    }
    my $text = "";
    if ($c =~ /<text>([^<]*)<\/text>/s) {
      $text = $1;
      $text =~ s/\x0d\x0a/\x0a/sg; # for old memo.
    }
    my $hash = "";
    if ($c =~ /<hash>([^<]*)<\/hash>/s) {
      $hash = $1;
    }
    $hmac->add($dt . encode('UTF-8', $text) . $hash);
    $s .= $c;
    last if ++$i >= $MEMO_NUM;
  }
  $SUM_HASH = substr($hmac->b64digest, 0, 16);
  $s = "<top_info>\n"
    . "<sum_hash>$SUM_HASH</sum_hash>\n"
    . "</top_info>\n" . $s;
  seek($fh, 0, SEEK_SET)
    or die "Cannot seek $file: $!";
  print $fh encode('UTF-8', $s)
      or die "Cannot write $file: $!";
  truncate($fh, tell($fh))
      or die "Cannot truncate $file: $!";
  flock($fh, LOCK_UN);
  close($fh);

  my @r;
  foreach my $c (@memo) {
    my $x = parse_memo($c);
    push(@r, $x) if defined $x;
  }

  return ($success, @r);
}

sub log_append {
  my ($text) = @_;
  my $file = $LOG;
  sysopen(my $fh, $file, O_RDWR | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_EX)
    or die "Cannot lock $file: $!";
  binmode($fh);
  seek($fh, 0, SEEK_END);
  print $fh encode('UTF-8', $text);
  if (tell($fh) > $LOG_MAX) {
    seek($fh, 0, SEEK_SET);
    my $s = join("", <$fh>);
    $s = substr($s, - $LOG_TRUNCATE);
    $s =~ s/^[^\n]*\n//s;
    seek($fh, 0, SEEK_SET);
    print $fh $s;
    truncate($fh, tell($fh));
  }
  flock($fh, LOCK_UN);
  close($fh);
  close($fh);
}

sub check_recaptcha {
  require LWP::UserAgent;

  my $response = $CGI->param('g-recaptcha-response');
  die "No g-recaptcha-response. You need JavaScript to post."
    if ! defined $response;
  my $ua = LWP::UserAgent->new();
  my $remoteip = $ENV{REMOTE_ADDR};
  my $greply = $ua->post($RECAPTCHA_API,
			 {
			  remoteip => $remoteip,
			  response => $response,
			  secret => $RECAPTCHA_SECRET_KEY,
			 });
  if ($greply->is_success()) {
    my $result = decode_json($greply->decoded_content());
    if ($result->{success}) {
      return 1;
    }
  }
  return 0;
}

sub print_log_page {
  my ($memo_array, %opt) = @_;
  my @memo = @{$memo_array};
  my $hmac;
  if (exists $opt{nickname}) {
    $NICKNAME = $opt{nickname};
    read_key() if ! defined $KEY;
    $hmac = Digest::HMAC_SHA1->new($KEY);
  }

  my $recaptcha_script = "";
  $recaptcha_script = "<script type=\"text/javascript\" src=\"https://www.google.com/recaptcha/api.js?render=explicit\" async defer></script>"
    if $USE_RECAPTCHA;
  my $this_user = "$SESSION_ID\@" . ($REMOTE_ADDR || '');

  my $scookie = $CGI->cookie(-name => $COOKIE_SID,
			     -path => $COOKIE_PATH,
			     -value => $SESSION_ID,
			     -expires => '+7d');
  my $ncookie = $CGI->cookie(-name => $COOKIE_NICKNAME,
			     -path => $COOKIE_PATH,
			     -value => encode('UTF-8', $NICKNAME),
			     -expires => '+1y');

  print $CGI->header(-type => 'text/html',
		     -charset => 'utf-8',
		     -cookie => [$scookie, $ncookie]);
  print <<"EOT";
<!DOCTYPE html>
<html lang="ja">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta http-equiv="Content-Language" content="ja">
<meta name="robots" content="nofollow" />
<meta name="viewport" content="width=device-width,initial-scale=1" />

<title>$TITLE: ログ</title>
<!-- shared_memo.cgi version $VERSION .
     You can get it from https://github.com/JRF-2018/shared_memo . -->
<link rel="stylesheet" href="$CSS" type="text/css" />
<script type="text/javascript">
USE_RECAPTCHA=$USE_RECAPTCHA;
RECAPTCHA_SITE_KEY="$RECAPTCHA_SITE_KEY";
</script>
<script type="text/javascript" src="$LOG_JS"></script>
$recaptcha_script
</head>
<body onLoad="init()">
<div class="container" id="log-container">
<img id="qr" src="$LOG_QR"/><h1>$TITLE: ログ</h1>
<p class="back">[<a href="$PROGRAM" rel="nofollow">メモに戻る</a>]
<!-- [<a href="$PROGRAM?cmd=log" rel="nofollow">リロード</a>] -->
[<a href="#bottom">末尾</a>]
</p>
<p class="alert">※ここにはたくさんのフィクション・自作自演が含まれてます。<br/>
※${DELETABLE_HOUR}時間待てば誰でも削除できます。無用な削除・連投はおやめください。<br/>
※ログ署名で確証できるメモの著者は十分な補償のないメモの再配布を禁止できるとします。
</p>
EOT

  print "<p class=\"nolog\">まだログはありません。</p>\n" if ! @memo;

  my $wrote = 0;
  my $id = 0;
  my $dels = 0;
  foreach my $x (@memo) {
    $id++;
    my $ip = $x->{ip};
    my $time = $x->{time};
    my $magic = $x->{magic};
    my $hash = $x->{hash} || "";
    my $session_id = $x->{session_id} || "";
    my $user = "$session_id\@$ip";
    my $etime = escape($time);
    my $text = $x->{text};
    my $ipmark = ($SESSION_ID eq $session_id)? "●" : "○";
    $wrote = 1 if $SESSION_ID eq $session_id;
    my $delmark = "";
    my $memo_id = "memo_${time}_$magic";
    $memo_id =~ s/[\:\-]//g;

    if (defined $text) {
      $text = escape_html($text);
      my $deldisabled = ($SESSION_ID eq $session_id
			 || check_deletable_date($time))?
			   "" : " disabled";

      print <<"EOT";
<div class="memo" id="$memo_id">
<form class="delete-form" id="delete-form-$id" action="$PROGRAM" method="post"
 onSubmit="return checkSubmit($id)">
<div class="info">
<span class="ipmark">$ipmark</span>
<span class="datetime"><a href="$PROGRAM?cmd=log#$memo_id" rel="nofollow">$time</a></span>
<span class="hash">$hash</span>
<select id="select-$id" name="reason" onChange="selectReason($id)">
<option value="none" selected>削除理由を選んでください</option>
<option value="hate">ムカついたから・憎悪が見てられないから</option>
<option value="privacy">恥ずかしいから・プライバシーの侵害があるから</option>
<option value="copyright">著作権・猥褻の問題があるから</option>
<option value="rewrite">修正したから・書き直したから</option>
<option value="other">その他の理由で</option>
</select>
<input type="submit" id="button-$id" value="削除" $deldisabled />
</div>
<div id="captcha-$id" class="captcha delete-captcha"></div>
<input type="hidden" name="cmd" value="delete" />
<input type="hidden" name="time" value="$time" />
<input type="hidden" name="magic" value="$magic" />
</form>
<pre>$text</pre>
</div>
EOT
    } else {
      $dels++;
      my $deleted = $x->{deleted};
      my $deleted_by = $x->{deleted_by} || "";
      my $delses = $deleted_by;
      $delses =~ s/\@.*$//s;
      my $class = ($SESSION_ID eq $delses)? " deleted-by-me"
	: " deleted-by-other";
      $delmark = ($SESSION_ID eq $delses)? "●" : "○";
      if (defined $deleted) {
	my %reason = ('other' => 'その他の理由で',
		      'rewrite' => '修正したから・書き直したから',
		      'copyright' => '著作権・猥褻の問題があるから',
		      'privacy' =>
		      '恥ずかしいから・プライバシーの侵害があるから',
		      'hate' => 'ムカついたから・憎悪が見てられないから',
		     );
	$deleted = (exists $reason{$deleted})? $reason{$deleted}
	  : $reason{'other'};
      }
      if (defined $deleted) {
	$deleted = " (" . escape_html($deleted) . ")";
      } else {
	$deleted = "";
      }
      print <<"EOT";
<div class="memo">
<form class="deleted-form" id="delete-form-$id" action="?" method="post">
<div class="info">
<span class="ipmark$class">$ipmark</span>
<span class="datetime"><a href="$PROGRAM?cmd=log#$memo_id">$time</a></span>
<span class="hash">$hash</span>
</div>
<input type="hidden" name="cmd" value="log" />
</form>
<pre class="deleted">削除$deleted</pre>
</div>
EOT
    }
    $hmac->add($time . encode('UTF-8', $ipmark . $delmark))
      if defined $hmac;
  }
  if (@memo) {
    my $x = $memo[-1];
    my $time = $x->{time};
    print <<"EOT";
<div class="post-info">
<p class="last">$time より前のものは残っていません。</p>
EOT
  }
  my $you = "あなた";
  my $your_ip = $REMOTE_ADDR || "不明";
  my $sum_hash = $opt{sum_hash} || "";
  my $need_ip = ! grep {$REMOTE_ADDR eq $_} @HIDE_IP_IP;
  $need_ip = $opt{need_ip} if exists $opt{need_ip};
  if (defined $hmac) {
    if ($need_ip) {
      $hmac->add(encode('UTF-8',
			"datetime: $DATETIME"
			. " person: 署名者"
			. " nickname: $NICKNAME"
			. " ip: $your_ip"
			. " sum_hash: $sum_hash"));
    } else {
      $hmac->add(encode('UTF-8',
			"datetime: $DATETIME"
			. " person: 署名者"
			. " nickname: $NICKNAME"
			. " sum_hash: $sum_hash"));
    }

    my $sign_hash = substr($hmac->b64digest, 0, 20);
    my $nickname = escape_html($NICKNAME);
    $you = "署名者";
    print <<"EOT";
<p class="signed-by">ログ署名者: ${nickname}</p>
<p class="sign-hash">Sign Hash: $sign_hash</p>
EOT
  } elsif ($wrote && ! grep {$REMOTE_ADDR eq $_} @DISABLE_SIGN_IP) {
    my $nickname = escape_html($NICKNAME);
    print <<"EOT";
<form id="sign-form" action="$PROGRAM" method="post"
 onSubmit="return checkSignSubmit()">
<div class="sign-div">
<label>名前:<input type="text" name="nickname" id="nickname" value="$nickname" size="8"/></label>
<label><input type="checkbox" name="need_ip" id="need_ip" value="1" checked/>IP有</label>
<label><input type="checkbox" name="public" id="public" value="1" checked/>公表</label>
<input type="submit" id="sign-button" value="ログ署名" />
</div>
<div id="captcha-sign" class="captcha sign-captcha"></div>
<input type="hidden" name="cmd" value="slog" />
</form>
EOT
  }
  print <<"EOT";
<p class="sum-hash">Sum Hash: $HASH_VERSION:$sum_hash (${id}個中${dels}個削除)</p>
EOT
  if ($need_ip) {
    print <<"EOT";
<p class="your-ip">■ ${you}は $DATETIME に IPアドレス $your_ip からアクセスしています。</p>
EOT
  } else {
    print <<"EOT";
<p class="your-ip">■ ${you}は $DATETIME にアクセスしています。</p>
EOT
  }
  print <<"EOT"
</div>
<div id="page-top"><a href="#"></a></div>
<div id="bottom"></div>
</div>
</body>
</html>
EOT
}

sub print_page {
  my ($memo) = @_;
  $memo = escape_html($memo);

  my $child = $CGI->param('child') || '';
  if ($child !~ /^[\-01-9A-Za-z_]+$/s){
    $child = '';
  }
  my $rows = $CGI->param('rows') || $DEFAULT_ROWS;
  if ($rows !~ /^[01-9]+$/s) {
    $rows = $DEFAULT_ROWS;
  }
  my $ip = $REMOTE_ADDR || 'unknown';
  my $write_disabled = (@WRITABLE_IP && ! (grep {$_ eq $ip} @WRITABLE_IP))? 1 : 0;
  my $write_disabled_disabled = ($write_disabled)? " disabled" : "";
  my $recaptcha_script = "";
  $recaptcha_script = "<script type=\"text/javascript\" src=\"https://www.google.com/recaptcha/api.js?render=explicit\" async defer></script>"
    if $USE_RECAPTCHA;
  my $childcss = ($child)? "font-size: small; margin:0; padding: 0; " : "";
  my $hidden = "<input type=\"hidden\" name=\"rows\" value=\"$rows\" />";
  $hidden .= "<input type=\"hidden\" name=\"child\" value=\"$child\" />\n"
    if $child;

  my $scookie = $CGI->cookie(-name => $COOKIE_SID,
			     -path => $COOKIE_PATH,
			     -value => $SESSION_ID,
			     -expires => '+7d');
  my $ncookie = $CGI->cookie(-name => $COOKIE_NICKNAME,
			     -path => $COOKIE_PATH,
			     -value => encode('UTF-8', $NICKNAME),
			     -expires => '+1y');

  print $CGI->header(-type => 'text/html',
		     -charset => 'utf-8',
		     -cookie => [$scookie, $ncookie]);
  print <<"EOT";
<!DOCTYPE html>
<html lang="ja">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta http-equiv="Content-Language" content="ja">
<meta name="robots" content="noindex,nofollow" />
<meta name="viewport" content="width=device-width,initial-scale=1" />

<title>$TITLE</title>
<!-- shared_memo.cgi version $VERSION .
     You can get it from https://github.com/JRF-2018/shared_memo . -->
<link rel="stylesheet" href="$CSS" type="text/css" />
<style type="text/css">
body { background: transparent; $childcss}
</style>
<script type="text/javascript">
USE_RECAPTCHA=$USE_RECAPTCHA;
RECAPTCHA_SITE_KEY="$RECAPTCHA_SITE_KEY";
WRITE_DISABLED=$write_disabled;
</script>
<script type="text/javascript" src="$JS"></script>
$recaptcha_script
</head>
<body onLoad="init('$child')">
<div class="container" id="write-container">
<div class="title">$TITLE</div>
<form id="write-form" action="$PROGRAM" method="post"
 onSubmit="return checkSubmit()">
<div id="write-main">
<textarea id="txt" name="txt" cols="20" rows="$rows">$memo</textarea>
<br />
<span id="char-count">---/$MEMO_MAX</span>
<input type="submit" id="write" value="書き換え"$write_disabled_disabled/>
<input type="hidden" name="cmd" value="write" />
<a href="$PROGRAM?cmd=log" target="_top">ログ</a>
</div>
<div id="captcha" class="captcha write-captcha"></div>
$hidden
</form>
</div>
</body>
</html>
EOT
}

sub check_deletable_date {
  my ($date) = @_;
  return 1 if ! defined $date || ! $date;
  my $sig = $SIG{__DIE__};
  delete $SIG{__DIE__};
  my $dt1 = eval {Time::Piece->strptime($date, '%Y-%m-%dT%H:%M:%SZ')};
  $SIG{__DIE__} = $sig;
  return 1 if $@ || ! defined $dt1;
  return $DATETIME_PIECE >= $dt1 + $DELETABLE_HOUR * 60 * 60;
}

sub check_session_date {
  my ($date) = @_;
  return 0 if $date !~ /^(\d+)-(\d+)-(\d+)T/;
  my $y1 = $1;
  my $m1 = $2;
  my $d1 = $3;
  return 0 if $DATETIME !~ /^(\d+)-(\d+)-(\d+)T/;
  my $y2 = $1;
  my $m2 = $2;
  my $d2 = $3;
  return 0 if $y1 != $y2 || $m1 != $m2;
  $d1 = "29" if $d1 > 29;
  $d2 = "29" if $d2 > 29;
  return substr($d1, 0, 1) eq substr($d2, 0, 1);
}

sub main {
  gen_key() if ! -f $KEY_FILE;

  $SESSION_ID = $CGI->cookie($COOKIE_SID);
  if (defined $SESSION_ID
      && $SESSION_ID =~ /^[A-Fa-f01-9]{32}\:(\d+-\d\d-\d\dT\d\d:\d\d:\d\dZ)$/s
      && check_session_date($1)) {
    ## pass
  } else {
    $SESSION_ID = new_session_id();
  }
  $NICKNAME = decode('UTF-8', $CGI->cookie($COOKIE_NICKNAME) || "");
  if (length($NICKNAME) > 128) {
    $NICKNAME = substr($NICKNAME, 0, 128);
  }

  my $cmd = $CGI->param('cmd') || 'read';
  if ($cmd eq 'write') {
    my $ip = $REMOTE_ADDR || 'unknown';
    my $agent = $ENV{HTTP_USER_AGENT} || 'unknown';
    if (@WRITABLE_IP && ! (grep {$_ eq $ip} @WRITABLE_IP)) {
      die "Your IP is not allowed to write.";
    }
    if ($USE_RECAPTCHA) {
      check_recaptcha() or die "reCAPTCHA failed.";
    }
    my $txt = decode('UTF-8', $CGI->param('txt') || "");
    if (length($txt) > $MEMO_MAX) {
      $txt = substr($txt, 0, $MEMO_MAX);
    }
    my $line = 1;
    my $tmp = "";
    while ($txt =~ /^(.*)$/mg && $line <= $MEMO_MAX_LINE) {
      $line++;
      $tmp .= $1 . "\n";
    }
    $txt = $tmp if length($txt) > length($tmp);
    $txt =~ s/\x0d\x0a/\x0a/sg;
    $txt =~ s/\x0d/\x0a/sg;
    my $magic = memo_write($txt);
    print_page($txt);
    log_append("$DATETIME write ($SESSION_ID) $magic $ip $agent\n");
  } elsif ($cmd eq 'delete') {
    if ($USE_RECAPTCHA) {
      check_recaptcha() or die "reCAPTCHA failed.";
    }
    my $reason = decode('UTF-8', $CGI->param('reason') || "none");
    if (length($reason) > 64 || $reason !~ /^[01-9A-Za-z_]+$/s) {
      $reason = "none";
    }
    my $time = decode('UTF-8', $CGI->param('time') || "");
    my $magic = decode('UTF-8', $CGI->param('magic') || "");
    if ($reason eq "none") {
      print_log_page([memo_read_all()], sum_hash => $SUM_HASH);
    } else {
      my ($success, @r) = memo_delete($reason, $time, $magic);
      print_log_page([@r], sum_hash => $SUM_HASH);
      my $ip = $REMOTE_ADDR || 'unknown';
      my $agent = $ENV{HTTP_USER_AGENT} || 'unknown';
      log_append("$DATETIME delete ($SESSION_ID) $time $magic $ip $agent\n") if $success;
    }
  } elsif ($cmd eq 'log') {
    print_log_page([memo_read_all()], sum_hash => $SUM_HASH);
  } elsif ($cmd eq 'slog') {
    if ($USE_RECAPTCHA) {
      check_recaptcha() or die "reCAPTCHA failed.";
    }
    my $need_ip = !! ($CGI->param('need_ip') || 0);
    my $nickname = decode('UTF-8', $CGI->param('nickname') || "");
    if (length($nickname) >= 128) {
      $nickname = substr($nickname, 0, 128);
    }
    $nickname =~ s/\x0d\x0a/\x0a/sg;
    $nickname =~ s/[\x0d\x0a]/ /sg;
    print_log_page([memo_read_all()], sum_hash => $SUM_HASH,
		   nickname => $nickname, need_ip => $need_ip);
    my $ip = $REMOTE_ADDR || 'unknown';
    my $agent = $ENV{HTTP_USER_AGENT} || 'unknown';
    $nickname = escape_html($nickname);
    my $closed = "";
    $closed = "c" if ! $CGI->param('public');
    log_append("$DATETIME slog ($SESSION_ID) $closed\"$nickname\" $ip $agent\n");
  } else {
    my $txt = memo_read();
    print_page($txt);
  }
}

main();
exit(0);

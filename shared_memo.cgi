#!/usr/bin/perl
our $VERSION = "0.0.1"; # Time-stamp: <2020-05-18T03:05:59Z>";

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

our $MEMO_XML = "shared_memo.xml";
our $LOG = "shared_memo.log";
our $JS = "shared_memo.js";
our $LOG_QR = "shared_memo_log.png";
our $CSS = "shared_memo.css";
our $PROGRAM = "shared_memo.cgi";
our $MEMO_MAX = 2000;
our $MEMO_NUM = 200;
our $LOG_MAX = 30000000;
our $LOG_TRUNCATE = 2000000;
our $DATETIME = datetime();

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
  return sprintf("%d-%02d-%02dT%02d:%02d%02dZ",
		 $year, $mon, $mday, $hour, $min, $sec);
}

sub allot_magic {
  my ($text) = @_;
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

sub memo_read {
  my $file = $MEMO_XML;
  sysopen(my $fh, $file, O_RDWR | O_CREAT)
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

sub memo_read_all {
  my $file = $MEMO_XML;
  sysopen(my $fh, $file, O_RDWR | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_SH)
    or die "Cannot lock $file: $!";
  binmode($fh);
  my $s = decode('UTF-8', join("", <$fh>));
  flock($fh, LOCK_UN);
  close($fh);
  my @memo;
  while ($s =~ /<\/memo>\s+/) {
    my $c = $` . $&;
    $s = $';
    if ($c =~ /<ip>([^<]*)<\/ip>\s*<time>([^<]*)<\/time>\s*<magic>([^<]*)<\/magic>/s) {
      my $ip = $1;
      my $time = $2;
      my $magic = $3;
      my $text;
      if ($c =~ /<text>([^<]*)<\/text>/s) {
	$text = unescape_html($1);
      }
      push(@memo, {ip => $ip, time => $time, magic => $magic,
		   text => $text});
    }
  }
  return @memo;
}

sub memo_write {
  my ($text) = @_;
  my $time = $DATETIME;
  my $ip = $ENV{REMOTE_ADDR} || '';
  my $magic = allot_magic($text);
  my $file = $MEMO_XML;
  sysopen(my $fh, $file, O_RDWR | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_EX)
    or die "Cannot lock $file: $!";
  binmode($fh);
  my $s = decode('UTF-8', join("", <$fh>));
  my @memo;
  $text = escape_html($text);
  push(@memo, "<memo>\n<ip>$ip</ip>\n"
       . "<time>$time</time>\n"
       . "<magic>$magic</magic>\n"
       . "<text>$text</text>\n</memo>\n");
  while ($s =~ /<\/memo>\s+/) {
    my $c = $` . $&;
    $s = $';
    push(@memo, $c);
  }
  $s = "";
  my $i = 0;
  foreach my $c (@memo) {
    $s .= $c;
    last if ++$i >= $MEMO_NUM;
  }
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
  my ($time, $magic) = @_;
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
      if ($c =~ s/<text>[^<]*<\/text>\s*//s) {
	$success = 1;
      }
    }
    $s .= $c;
    last if ++$i >= $MEMO_NUM;
  }
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
    if ($c =~ /<ip>([^<]*)<\/ip>\s*<time>([^<]*)<\/time>\s*<magic>([^<]*)<\/magic>/s) {
      my $ip = $1;
      my $time = $2;
      my $magic = $3;
      my $text;
      if ($c =~ /<text>([^<]*)<\/text>/s) {
	$text = unescape_html($1);
      }
      push(@r, {ip => $ip, time => $time, magic => $magic,
		   text => $text});
    }
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

sub print_log_page {
  my (@memo) = @_;
  print $CGI->header(-type => 'text/html',
		     -charset => 'utf-8');
  print <<"EOT";
<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta http-equiv="Content-Language" content="ja">
<meta name="robots" content="noindex,nofollow" />
<meta name="viewport" content="width=device-width,initial-scale=1" />

<title>グローバル共有メモ: ログ</title>
<!-- shared_memo.cgi version $VERSION .
     You can get it from https://github.com/JRF-2018/shared_memo . -->
<link rel="stylesheet" href="$CSS" type="text/css" />
</head>
<body>
<img id="qr" src="$LOG_QR"/><h1>グローバル共有メモ: ログ</h1>
<p class="back">[<a href="$PROGRAM">メモに戻る</a>]</p>
EOT

  print "<p class=\"nolog\">まだログはありません。</p>\n" if ! @memo;

  foreach my $x (@memo) {
    my $ip = $x->{ip};
    my $time = $x->{time};
    my $magic = $x->{magic};
    my $etime = escape($time);
    my $text = $x->{text};
    if (defined $text) {
      print <<"EOT";
<div class="memo">
<div class="info"><span class="datetime">$time</span> <a rel="nofollow" href="$PROGRAM?cmd=delete&amp;time=$etime&amp;magic=$magic">削除</a></div>
<pre>$text</pre>
</div>
EOT
    } else {
      print <<"EOT";
<div class="memo">
<div class="info"><span class="datetime">$time</span></div>
<pre class="deleted">削除</pre>
</div>
EOT
    }
  }
  if (@memo) {
    my $x = $memo[-1];
    my $time = $x->{time};
    print <<"EOT";
<p class="last">$time より前のものは残っていません。</p>
EOT
  }
  print <<"EOT";
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
  my $rows = $CGI->param('rows') || 8;
  if ($rows !~ /^[01-9]+$/s) {
    $rows = 8;
  }
  my $childcss = ($child)? "font-size: small; margin:0; padding: 0; " : "";
  my $hidden = "<input type=\"hidden\" name=\"rows\" value=\"$rows\" />";
  $hidden .= "<input type=\"hidden\" name=\"child\" value=\"$child\" />\n"
    if $child;

  print $CGI->header(-type => 'text/html',
		     -charset => 'utf-8');
  print <<"EOT";
<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta http-equiv="Content-Language" content="ja">
<meta name="robots" content="noindex,nofollow" />
<meta name="viewport" content="width=device-width,initial-scale=1" />

<title>グローバル共有メモ</title>
<!-- shared_memo.cgi version $VERSION .
     You can get it from https://github.com/JRF-2018/shared_memo . -->
<link rel="stylesheet" href="$CSS" type="text/css" />
<style type="text/css">
body { background: transparent; $childcss}
</style>
<script type="text/javascript" src="$JS"></script>
</head>
<body onLoad="init('$child')">
<div class="title">グローバル共有メモ</div>
<form action="$PROGRAM" method="post">
<textarea id="txt" name="txt" cols="20" rows="$rows">$memo</textarea>
<br />
<span id="char-count">---/$MEMO_MAX</span>
<button type="submit" id="write" name="cmd" value="write">書き換え</button>
<a href="$PROGRAM?cmd=log" target="_top">ログ</a>
$hidden
</form>
</body>
</html>
EOT
}

sub main {
  my $cmd = $CGI->param('cmd') || 'read';
  if ($cmd eq 'write') {
    my $txt = decode('UTF-8', $CGI->param('txt') || "");
    if (length($txt) > $MEMO_MAX) {
      $txt = substr($txt, 0, $MEMO_MAX);
    }
    my $magic = memo_write($txt);
    print_page($txt);
    my $ip = $ENV{REMOTE_ADDR} || 'unknown';
    my $agent = $ENV{HTTP_USER_AGENT} || 'unknown';
    log_append("$DATETIME write $magic $ip $agent\n");
  } elsif ($cmd eq 'delete') {
    my $time = decode('UTF-8', $CGI->param('time') || "");
    my $magic = decode('UTF-8', $CGI->param('magic') || "");
    my ($success, @r) = memo_delete($time, $magic);
    print_log_page(@r);
    my $ip = $ENV{REMOTE_ADDR} || 'unknown';
    my $agent = $ENV{HTTP_USER_AGENT} || 'unknown';
    log_append("$DATETIME delete $time $magic $ip $agent\n") if $success;
  } elsif ($cmd eq 'log') {
    print_log_page(memo_read_all());
  } else {
    my $txt = memo_read();
    print_page($txt);
  }
}

main();
exit(0);

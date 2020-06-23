#!/usr/bin/perl
our $VERSION = "0.0.7"; # Time-stamp: <2020-06-23T18:57:54Z>";

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

use Encode qw(encode decode);
use Fcntl qw(:DEFAULT :flock :seek);
use Digest::SHA1;
use Digest::HMAC_SHA1;
use Time::Piece;
use CGI;

our $LIMIT = 5000000;
our $CSS = "shared_memo.css";
our $PROGRAM = "check_log.cgi";
our $KEY_FILE = "shared_memo_key.xml";
our $IP = "";
our $KEY;

our $CHECK_BEGIN = "2020-05-24T07:39:09Z";
our $CHECK_BEGIN_TP = Time::Piece->strptime($CHECK_BEGIN, '%Y-%m-%dT%H:%M:%SZ');

our $CGI = CGI->new;
binmode(STDOUT, ":utf8");

our $DIE_1 = sub {
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

our $DIE_2 = sub {
  my $message = shift;
  print <<"EOT";
Die: $message
</pre>
</body>
</html>
EOT
  exit(1);
};

$SIG{__DIE__} = $DIE_1;

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

sub check_version_type {
  my ($s) = @_;
  return $s =~ /^(?:\d+\.)*\d+$/s;
}

sub version_compare {
  my ($a, $b) = @_;
  my @a = split(/\./, $a);
  my @b = split(/\./, $b);
  while (@a < @b) {push(@a, "0")}
  while (@b < @a) {push(@b, "0")}
  for (my $i = 0; $i < @a; $i++) {
    my $x = int($a[$i]) - int($b[$i]);
    return $x if $x != 0;
  }
  return 0;
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

sub parse_date {
  my ($date) = @_;

  my $sig = $SIG{__DIE__};
  delete $SIG{__DIE__};
  my $dt1 = eval {Time::Piece->strptime($date, '%Y-%m-%dT%H:%M:%SZ')};
  $SIG{__DIE__} = $sig;
  return undef if $@ || ! defined $dt1;
  return $dt1;
}

sub parse_html {
  my ($s) = @_;

  $s =~ s/\x0d\x0a/\x0a/sg;

  read_key() if ! defined $KEY;
  my $hmac = Digest::HMAC_SHA1->new($KEY);

  my $SUM_HASH;
  my $N;
  my $DELS;
  my $hash_version;

  my $r = "";

  if ($s =~ /<p class=\"sum-hash\">Sum Hash: ([^: ]+):([^ ]+) \((\d+)個中(\d+)個削除\)/) {
    $hash_version = $1;
    $SUM_HASH = $2;
    $N = $3;
    $DELS = $4;
  }

  my $memos = 0;
  my $dels = 0;
  my $green = 1;
  my $greens = 0;
  my $easyerr = 0;
  while ($s =~ /<pre( [^>]*)?>([^<]*)/s) {
    my $p = $`;
    $s = $';
    my $text = unescape_html($2);
    my $class = $1 || "";
    next if $class =~ /result/;
    $memos++;
    my $deleted = ($class =~ /deleted/);
    if ($p !~ /<span\s+class=\"datetime\">\s*<a[^>]+>([^<]+)/s) {
      die "日時がありません。\n";
    }
    my $datetime = $1;
    my $hash = get_hash($datetime . $text, $datetime . ($IP || ""));
    if ($deleted) {
      $dels ++;
      my $h1a = substr($hash, 0, 2);
      my $h1b = substr($hash, 2, 4);
      my $h1c = substr($hash, 6);
      my $hash2 = "          ";
      if ($p !~ /<span\s+class=\"hash\">([^<]*)/s) {
	die "$datetime - ハッシュがありません。\n";
      }
      $hash2 = $1;
      $hmac->add(encode('UTF-8', $datetime . $1));
      $datetime = escape_html($datetime);
      $hash2 = escape_html($hash2);
      $r .= <<"EOT";
<div class="memo">
<form class="deleted-form">
<div class="info">
<span class="ipmark">○</span>
<span class="datetime"><a href="#">$datetime</a></span>
<span class="hash">$hash2<span>
</div>
</form>
<pre class="deleted">削除</pre>
</div>
EOT
    } else {
      my $h1a = substr($hash, 0, 2);
      my $h1b = substr($hash, 2, 4);
      my $h1c = substr($hash, 6);
      my $hash2 = "          ";
      if ($p !~ /<span\s+class=\"hash\">([^<]*)/s) {
	die "$datetime - ハッシュがありません。\n";
      }
      $hash2 = $1;
      my $origtext = escape_html($text);
      $hmac->add(encode('UTF-8', $datetime . $origtext . $1));
      my $h2a = (length($hash2) >= 2)? substr($hash2, 0, 2) : "  ";
      my $h2b = (length($hash2) >= 6)? substr($hash2, 2, 4) : "    ";
      my $h2c = (length($hash2) >= 10)? substr($hash2, 6) : "    ";
      my $pdatetime = $datetime;
      if ($pdatetime =~ /T(\d\d):(\d\d)(\d\d)Z$/s) {
	$pdatetime = $` . "T$1:$2:$3Z";
      }
      my $tp = parse_date($pdatetime);
      $datetime = escape_html($datetime);
      $hash2 = escape_html($hash2);
      $r .= <<"EOT";
<div class="memo">
<form class="delete-form">
<div class="info">
<span class="ipmark">○</span>
<span class="datetime"><a href="#">$datetime</a></span>
<span class="hash">$hash2<span>
</div>
</form>
<pre>$origtext</pre>
</div>
EOT
      if ($h1a ne $h2a) {
	if (! defined $tp || $tp >= $CHECK_BEGIN_TP) {
	  print "$datetime - 簡易チェックに失敗しました。\n";
	  $easyerr++;
	} else {
	  print "$datetime - 簡易チェックに失敗しました。が、古いため無視します。\n";
	}
      } elsif ($h1b ne $h2b) {
	if (! defined $tp || $tp >= $CHECK_BEGIN_TP) {
	  $green = 0;
	}
      } else {
	$greens++;
      }
    }
  }
  print "----\n";
  my $sum_hash = substr($hmac->b64digest, 0, 16);
  if (! defined $SUM_HASH) {
    print "NG: Sum Hash がありません。古い形式です。\n";
  } elsif ($memos - $dels < 1) {
    print "NG: メモがすべて削除されています。\n";
  } elsif ($memos != $N || $dels != $DELS) {
    print "NG: メモの数・削除の数が記録と合っていません。偽造が疑われます。\n";
  } elsif ($easyerr) {
    print "NG: 簡易チェックの失敗がありました。文字コード(utf-8)や改行(lf)コードをチェックしてください。特定のものにのみ失敗がある場合は、偽造が疑われます。\n";
  } elsif ($greens < 1) {
    print "NG: 有効なメモがありません。\n";
  } elsif ($SUM_HASH ne $sum_hash || ! $green) {
    print "NG: 合わないハッシュがありました。偽造が疑われます。\n";
  } else {
    print "OK: メモには偽造がないと思われます。が、CSS や JavaScript、HTML 形式の偽装まではチェックしていませんのでご注意を。\n";
    $r .= <<"EOT";
<div class="post-info">
<p class="sum-hash">Sum Hash: $SUM_HASH (${N}個中${DELS}個削除)</p>
</div>
EOT
    return $r;
  }
  return undef;
}

sub print_parse_html {
  my ($s) = @_;

  $SIG{__DIE__} = $DIE_2;

  print $CGI->header(-type => 'text/html',
		     -charset => 'utf-8');
  print <<"EOT";
<!DOCTYPE html>
<html lang="ja">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta http-equiv="Content-Language" content="ja">
<meta name="robots" content="noindex,nofollow" />
<meta name="viewport" content="width=device-width,initial-scale=1" />

<title>check_log.cgi Result</title>
<!-- check_log.cgi version $VERSION .
     You can get it from https://github.com/JRF-2018/shared_memo . -->
<link rel="stylesheet" href="$CSS" type="text/css" />
</head>
<body>
<h1>check_log.cgi: Result</h1>
<pre class="result">
EOT

  my $r = parse_html($s);

  print <<"EOT";
</pre>
EOT
  print <<"EOT" if defined $r;
<hr/>
<h1>チェック済みのメモ</h1>
<div class="container" id="log-container">
$r
</div>
EOT
  print <<"EOT";
</body>
</html>
EOT
}

sub print_page {
  print $CGI->header(-type => 'text/html',
		     -charset => 'utf-8');
  print <<"EOT";
<!DOCTYPE html>
<html lang="ja">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta http-equiv="Content-Language" content="ja">
<meta name="robots" content="noindex,nofollow" />
<meta name="viewport" content="width=device-width,initial-scale=1" />

<title>check_log.cgi</title>
<!-- check_log.cgi version $VERSION .
     You can get it from https://github.com/JRF-2018/shared_memo . -->
<link rel="stylesheet" href="$CSS" type="text/css" />
</head>
<body>
<h1>log.html に偽造がないか調べます</h1>

<form id="parse_html_form" action="$PROGRAM" method="post" enctype="multipart/form-data">
<label>log.html: <input type="file" name="log-html" accept="text/html" />
</label>
<br/>
<input type="submit" value="送信" />
<input type="hidden" name="cmd" value="parse_html">
</form>
</body>
</html>
EOT
}

sub main {
  my $cmd = $CGI->param('cmd') || 'read';

  if ($cmd eq 'parse_html') {
    my $fh = $CGI->upload('log-html');
    if (! defined $fh) {
      my $err = $CGI->cgi_error;
      die "No file: $err";
    }
    binmode($fh);
    die "Th file is too large." if -s $fh > $LIMIT;
    my $s = join("", <$fh>);
    print_parse_html(decode('UTF-8', $s));
  } else {
    print_page();
  }
}

main();
exit(0);

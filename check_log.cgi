#!/usr/bin/perl
our $VERSION = "0.1.1"; # Time-stamp: <2020-12-01T03:10:25Z>";

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
use JSON qw(decode_json);
use Time::Piece;
use CGI;

our $CHECK_SLOG = 1;
our $LIMIT = 5000000;
our $LOG = "shared_memo.log";
our $JS = "check_log.js";
our $CSS = "shared_memo.css";
our $PROGRAM = "check_log.cgi";
our $KEY_FILE = "shared_memo_key.xml";
our @DENY_NICKNAME = (); # may be regexp.
our @ALLOW_DENIED_NICKNAME = (); # may be regexp.
our $HASH_VERSION = "0.0.8.3";
our $IP = "";
our $KEY;

#our $CHECK_BEGIN = "2020-05-24T07:39:09Z";
our $CHECK_BEGIN = "2020-10-23T00:00:00Z";
our $CHECK_BEGIN_TP = Time::Piece->strptime($CHECK_BEGIN, '%Y-%m-%dT%H:%M:%SZ');

our $USE_RECAPTCHA = 0;
our $RECAPTCHA_API = "https://www.google.com/recaptcha/api/siteverify";
our $RECAPTCHA_SECRET_KEY = "__Your_Secret_Key__";
our $RECAPTCHA_SITE_KEY = "__Your_Site_Key__";

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

sub uniq {
  my %tmp;
  my @r;
  foreach my $x (@_) {
    push(@r, $x) if ! exists $tmp{$x};
    $tmp{$x} = 1;
  }
  return @r;
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

sub parse_html {
  my ($s, %opt) = @_;

  $s =~ s/\x0d\x0a/\x0a/sg;

  read_key() if ! defined $KEY;
  my $hmac = Digest::HMAC_SHA1->new($KEY);
  my $shmac = Digest::HMAC_SHA1->new($KEY);

  my $SUM_HASH;
  my $N;
  my $DELS;
  my $hash_version;

  if ($s =~ /<p class=\"sum-hash\">Sum Hash: ([^: ]+):([^ ]+) \((\d+)個中(\d+)個削除\)/s) {
    $hash_version = $1;
    $SUM_HASH = $2;
    $N = $3;
    $DELS = $4;
  }

  my $hmac2;
  my $shmac2;
  my $sign_hash;
  my $sign_person;
  my $sign_datetime;
  my $sign_ip;
  my $sign_nickname;
  my $sign_error = 0;
  if ($s =~ /<p class=\"sign-hash\">Sign Hash: ([^<]+)/s) {
    $sign_hash = $1;
    if ($s =~ /<p class=\"your-ip\"[^>]*>■ (署名者|作者)は ([^ ]+) に IPアドレス ([^ ]+) からアクセス/s) {
      $sign_person = $1;
      $sign_datetime = $2;
      $sign_ip = $3;
      $IP = $sign_ip;
    } elsif ($s =~ /<p class=\"your-ip\"[^>]*>■ (署名者|作者)は ([^ ]+) にアクセス/s) {
      $sign_person = $1;
      $sign_datetime = $2;
    }
    if ($s =~ /<p class=\"signed-by\">[^:]+: ([^<]*)/s) {
      $sign_nickname = unescape_html($1);
    }
    if (defined $sign_datetime) {
      $hmac2 = Digest::HMAC_SHA1->new($KEY);
      $shmac2 = Digest::HMAC_SHA1->new($KEY);
    } else {
      $sign_error = 1;
    }
  }

  my $need_pickup = 0;
  my %pickup;
  if (exists $opt{pickup} && @{$opt{pickup}}) {
    $need_pickup = 1;
    foreach my $c (@{$opt{pickup}}) {
      $pickup{$c} = 0;
    }
  }

  my $r = "";
  my $memos = 0;
  my $dels = 0;
  my $smemos = 0;
  my $sdels = 0;
  my $green = 1;
  my $greens = 0;
  my $easyerr = 0;
  my @marked;
  my %same_date;
  while ($s =~ /<pre( [^>]*)?>/s) {
    my $p = $`;
    my $class = $1 || "";
    $s = $';
    if ($s !~ /<\/pre>/s) {
      die "&lt;/pre&gt; がありません。\n";
    }
    $s = $';
    my $text = $`;
    $text =~ s/<[^>]+>//g;
    $text = unescape_html($text);
    next if $class =~ /result/;
    $memos++;
    my $deleted = ($class =~ /deleted/);
    if ($p !~ /<span\s+class=\"datetime\">\s*<a[^>]+>([^<]+)/s) {
      die "日時がありません。\n";
    }
    my $datetime = $1;
    my $edatetime = escape_html($1);
    $same_date{$datetime} = 0 if ! exists $same_date{$datetime};
    $same_date{$datetime}++;
    my $hash = get_hash($datetime . $text, $datetime . ($IP || ""));
    my $ipmark = "○";
    my $ipmarkline = "<span class=\"ipmark\">○</span>";
    my $pickup_id;
    $pickup_id = $datetime if exists $pickup{$datetime};
    $pickup_id = $datetime . "(" . $same_date{$datetime} . ")"
      if exists $pickup{$datetime . "(" . $same_date{$datetime} . ")"};
    $pickup{$pickup_id} = 1 if defined $pickup_id;
    if (defined $hmac2) {
      if ($p !~ /<span\s+class=\"ipmark([^\"]*)\">([^<]+)/s) {
	die "先頭のマークがありません。\n";
      }
      $ipmark = $2;
      my $delclass = $1;
      my $delmark = "";
      if ($delclass =~ /deleted-by-me/) {
	$delmark = "●";
	$delclass = " deleted-by-me";
      } elsif ($delclass =~ /deleted-by-other/) {
	$delmark = "○";
	$delclass = " deleted-by-other";
      } else {
	$delclass = "";
      }
      $hmac2->add(encode('UTF-8', $datetime . $ipmark . $delmark));
      if (! $need_pickup || defined $pickup_id) {
	$shmac2->add(encode('UTF-8', $datetime . $ipmark . $delmark));
      }
      $ipmarkline = "<span class=\"ipmark$delclass\">$ipmark</span>";
    }
    if ($deleted) {
      $dels ++;
      my $h1a = substr($hash, 0, 2);
      my $h1b = substr($hash, 2, 4);
      my $h1c = substr($hash, 6);
      my $hash2 = "          ";
      if ($p !~ /<span\s+class=\"hash\">([^<]*)/s) {
	die "$edatetime - ハッシュがありません。\n";
      }
      $hash2 = $1;
      $hmac->add(encode('UTF-8', $datetime . $hash2));
      $datetime = escape_html($datetime);
      $hash2 = escape_html($hash2);
      if (! $need_pickup || defined $pickup_id) {
	$shmac->add(encode('UTF-8', $datetime . $hash2));
	$smemos++;
	$sdels++;
	$r .= <<"EOT";
<div class="memo">
<form class="deleted-form">
<div class="info">
$ipmarkline
<span class="datetime"><a href="#">$datetime</a></span>
<span class="hash">$hash2<span>
</div>
</form>
<pre class="deleted">削除</pre>
</div>
EOT
      }
    } else {
      my $h1a = substr($hash, 0, 2);
      my $h1b = substr($hash, 2, 4);
      my $h1c = substr($hash, 6);
      my $hash2 = "          ";
      if ($p !~ /<span\s+class=\"hash\">([^<]*)/s) {
	die "$edatetime - ハッシュがありません。\n";
      }
      $hash2 = $1;
      my $origtext = escape_html($text);
      $hmac->add(encode('UTF-8', $datetime . $origtext . $hash2));
      my $h2a = (length($hash2) >= 2)? substr($hash2, 0, 2) : "  ";
      my $h2b = (length($hash2) >= 6)? substr($hash2, 2, 4) : "    ";
      my $h2c = (length($hash2) >= 10)? substr($hash2, 6) : "    ";
      my $pdatetime = $datetime;
      if ($pdatetime =~ /T(\d\d):(\d\d)(\d\d)Z$/s) {
	$pdatetime = $` . "T$1:$2:$3Z";
      }
      my $tp = parse_date($pdatetime);
      $hash2 = escape_html($hash2);
      if (! $need_pickup || defined $pickup_id) {
	$shmac->add(encode('UTF-8', $datetime . $origtext . $hash2));
	$smemos++;
	$r .= <<"EOT";
<div class="memo">
<form class="delete-form">
<div class="info">
$ipmarkline
<span class="datetime"><a href="#">$edatetime</a></span>
<span class="hash">$hash2<span>
</div>
</form>
<pre>$origtext</pre>
</div>
EOT
      }
      if ($h1a ne $h2a) {
	if (! defined $tp || $tp >= $CHECK_BEGIN_TP) {
	  print "$edatetime - 簡易チェックに失敗しました。\n";
	  $easyerr++;
	} else {
	  print "$edatetime - 簡易チェックに失敗しました。が、古いため無視します。\n";
	}
      } elsif ($h1b ne $h2b) {
	if (! defined $tp || $tp >= $CHECK_BEGIN_TP) {
	  $green = 0;
	}
      } else {
	$greens++;
      }
      if (defined $hmac2 && defined $sign_ip && $ipmark eq "●") {
	push(@marked, [$edatetime, $h1c eq $h2c]);
      }
    }
  }
  print "----\n";

  my $sum_hash = substr($hmac->b64digest, 0, 16);
  my $ssum_hash = substr($shmac->b64digest, 0, 16);
  my $ssign_hash;
  my $sign_check = 0;
  if (defined $hmac2) {
    if (defined $sign_ip) {
      $hmac2->add(encode('UTF-8',
			 "datetime: $sign_datetime"
			 . " person: $sign_person"
			 . " nickname: $sign_nickname"
			 . " ip: $sign_ip"
			 . " sum_hash: $sum_hash"));
      $shmac2->add(encode('UTF-8',
			 "datetime: $sign_datetime"
			 . " person: $sign_person"
			 . " nickname: $sign_nickname"
			 . " ip: $sign_ip"
			 . " sum_hash: $ssum_hash"));
    } else {
      $hmac2->add(encode('UTF-8',
			 "datetime: $sign_datetime"
			 . " person: $sign_person"
			 . " nickname: $sign_nickname"
			 . " sum_hash: $sum_hash"));
      $shmac2->add(encode('UTF-8',
			 "datetime: $sign_datetime"
			 . " person: $sign_person"
			 . " nickname: $sign_nickname"
			 . " sum_hash: $ssum_hash"));
    }
    $sign_check = 1 if $sign_hash eq substr($hmac2->b64digest, 0, 20);
    $ssign_hash = substr($shmac2->b64digest, 0, 20);
  }
  my $all_pickup = 1;
  if ($need_pickup) {
    foreach my $c (@{$opt{pickup}}) {
      if (! $pickup{$c}) {
	$all_pickup = 0;
	last;
      }
    }
  }

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
  } elsif ($sign_error == 1) {
    print "NG: ログ署名の形式が正しくありません。\n";
  } elsif ($SUM_HASH ne $sum_hash || ! $green) {
    print "NG: 合わないハッシュがありました。偽造が疑われます。\n";
  } elsif (defined $hmac2 && ! $sign_check) {
    print "NG: ログ署名が正しくありません。偽造が疑われます。\n";
  } elsif ($need_pickup && ! $all_pickup) {
    print "NG: 抽出するよう指定されたメモが見つかりません。\n";
    foreach my $c (@{$opt{pickup}}) {
      my $ec = escape_html($c);
      print "$ec が見つかりません。\n" if ! $pickup{$c};
    }
  } else {
    if (! defined $hmac2) {
      print "OK: メモには偽造がないと思われます。が、CSS や JavaScript、HTML 形式の偽装まではチェックしていませんのでご注意を。\n";
      $r .= <<"EOT";
<div class="post-info">
<p class="sum-hash">Sum Hash: $HASH_VERSION:$ssum_hash (${smemos}個中${sdels}個削除)</p>
</div>
EOT
    } elsif (! defined $sign_ip) {
      print "OK: メモには偽造がないと思われます。が、CSS や JavaScript、HTML 形式の偽装まではチェックしていませんのでご注意を。\n";
      my $nickname = escape_html($sign_nickname);
      my $datetime = escape_html($sign_datetime);
      $r .= <<"EOT";
<div class="post-info">
<p class="signed-by">ログ署名者: ${nickname}</p>
<p class="sign-hash">Sign Hash: $ssign_hash</p>
<p class="sum-hash">Sum Hash: $HASH_VERSION:$ssum_hash (${smemos}個中${sdels}個削除)</p>
<p class="your-ip">■ ${sign_person}は $datetime にアクセスしていました。</p>
</div>
EOT
    } else {
      my $ok = 0;
      foreach my $l (@marked) {
	my $dt = $l->[0];
	my $txt = ($l->[1])? "${sign_person}IPアドレスの書き込みと思われます。"
	  : "不明のIPアドレスの書き込み。";
	$ok++ if $l->[1];
	print "$dt - $txt\n";
      }
      print "----\n";
      print "OK: メモには偽造がないと思われます。が、CSS や JavaScript、HTML 形式の偽装まではチェックしていませんのでご注意を。\n";
      if (@marked == $ok && $ok > 0) {
	print "先頭「●」の削除されていない書き込みはすべて${sign_person}のIPアドレスからと思われます。\n";
      } elsif ($ok == 0) {
	print "先頭「●」の削除されていない書き込みのうち${sign_person}のIPアドレスからと確認できたものはありません。\n";
      } else {
	print "先頭「●」の削除されていない書き込みのうちいくつかは${sign_person}のIPアドレスからと思われます。\n";
      }

      my $nickname = escape_html($sign_nickname);
      my $datetime = escape_html($sign_datetime);
      my $ip = escape_html($sign_ip);

      $r .= <<"EOT";
<div class="post-info">
<p class="signed-by">ログ署名者: ${nickname}</p>
<p class="sign-hash">Sign Hash: $ssign_hash</p>
<p class="sum-hash">Sum Hash: $HASH_VERSION:$ssum_hash (${smemos}個中${sdels}個削除)</p>
<p class="your-ip">■ ${sign_person}は $datetime に IPアドレス $ip からアクセスしていました。</p>
</div>
EOT
    }
    return $r;
  }
  return undef;
}

sub print_parse_html {
  my ($s, @opt) = @_;

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

  my $r = parse_html($s, @opt);

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

sub parse_get_datetime {
  my ($s) = @_;
  my @r;
  while ($s =~ /<pre( [^>]*)?>/s) {
    my $p = $`;
    $s = $';
    my $class = $1 || "";
    next if $class =~ /result/;
    if ($p =~ /<span\s+class=\"datetime\">\s*<a[^>]+>([^<]+)/s) {
      my $date = $1;
      $date =~ s/(\d\d)(\d\d)Z$/${1}:${2}Z/s;
      push(@r, $date);
    }
  }
  return @r;
}

sub check_slog_slog {
  my ($db, $date, @x) = @_;
  my @f = grep {
    my ($d, $y) = @{$_};
    parse_date($d) >= parse_date($db);
  } @x;
  if (@f) {
    my $a;
    foreach my $c (@f) {
      my ($d, $y) = @$c;
      $a = $y if defined $y;
    }
    if (defined $a) {
      $a = unescape_html($a);
      if ((! grep {((ref $_) eq 'Regexp')? ($a =~ $_) : ($a eq $_)}
	   @DENY_NICKNAME)
	  || (grep {((ref $_) eq 'Regexp')? ($a =~ $_) : ($a eq $_)}
	      @ALLOW_DENIED_NICKNAME)) {
	print escape_html("$date - 「$a」によりログ署名済み。\n");
      } else {
	print escape_html("$date - ※表示できない名前※によりログ署名済み。\n");
      }
    } else {
      print escape_html("$date - ログ署名済み。\n");
    }
    return 1;
  }
  return 0;
}

sub check_slog {
  my (%opt) = @_;
  my $file = $LOG;
  my @pickup = @{$opt{pickup}};
  @pickup = sort {
    my $ab = $a;
    my $bb = $b;
    my $ad = 1;
    my $bd = 1;
    $ad = $1 if $ab =~ s/\((\d+)\)$//s;
    $bd = $1 if $bb =~ s/\((\d+)\)$//s;
    my $atp = parse_date($ab);
    my $btp = parse_date($bb);
    my $c = $atp <=> $btp;
    if ($c == 0) {
      $ad <=> $bd;
    } else {
      $c;
    }
  } @pickup;

  sysopen(my $fh, $file, O_RDONLY | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_SH)
    or die "Cannot lock $file: $!";
  binmode($fh);
  my $s = decode('UTF-8', join("", <$fh>));
  flock($fh, LOCK_UN);
  close($fh);

  my %write;
  my %slog;
  while ($s =~ /^.*$/mg) {
    my $c = $&;
    if ($c !~ /^([^ ]+) (write|delete|slog) /) {
      die "$file: Parse Error.";
    }
    my $date = $1;
    my $cmd = $2;
    $c = $';
    if ($c =~ /^\s*\(([^\)]+)\)/) {
      $c = $';
	my $sid = $1;
      if ($cmd eq 'write') {
	$write{$date} = [] if ! exists $write{$date};
	push(@{$write{$date}}, $sid);
      } elsif ($cmd eq 'slog') {
	if ($c !~ /^\s*(c?)\"([^\"]+)\"/) {
	  die "$file: Parse Error.";
	}
	$slog{$sid} = [] if ! exists $slog{$sid};
	if (! defined $1 || $1 eq "") {
	  push(@{$slog{$sid}}, [$date, $2]);
	} else {
	  push(@{$slog{$sid}}, [$date, undef]);
	}
      }
    }
  }

  foreach my $date (@pickup) {
    my $db = $date;
    my $dd = 0;
    $dd = $1 if $db =~ s/\((\d+)\)$//;
    if (! exists $write{$db}) {
      print escape_html("$date - 記録にありません。おそらく古過ぎます。\n");
    } else {
      if ($dd == 0) {
	foreach my $x (@{$write{$db}}) {
	  my $done = 0;
	  if (exists $slog{$x}) {
	    $done = check_slog_slog($db, $date, @{$slog{$x}});
	  }
	  if (! $done) {
	    print escape_html("$date - ログ署名が取られていません。\n");
	  }
	}
      } elsif ($dd > @{$write{$db}}) {
	print escape_html("$date - 記録にありません。おそらく古過ぎます。\n");
      } else {
	my @l = @{$write{$db}};
	my $done = 0;
	if (exists $slog{$l[@l - $dd]}) {
	  $done = check_slog_slog($db, $date, @{$slog{$l[@l - $dd]}});
	}
	if (! $done) {
	  print escape_html("$date - ログ署名が取られていません。\n");
	}
      }
    }
  }
}

sub print_check_slog {
  my (@opt) = @_;
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

  check_slog(@opt);

  print <<"EOT";
</pre>
<p class="notice">※識別子の切り替え期間を過ぎても管理人はログ署名できます。その場合には告知します。</br>
※メモが古過ぎる場合、正規の販売がないか十分確認しましょう。</p>
</body>
</html>
EOT
}

sub print_page {
  my $recaptcha_script = "";
  $recaptcha_script = "<script type=\"text/javascript\" src=\"https://www.google.com/recaptcha/api.js?render=explicit\" async defer></script>"
    if $USE_RECAPTCHA;

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
<script type="text/javascript">
USE_RECAPTCHA=$USE_RECAPTCHA;
RECAPTCHA_SITE_KEY="$RECAPTCHA_SITE_KEY";
</script>
<script type="text/javascript" src="$JS"></script>
$recaptcha_script
</head>
<body>
<h1>log.html に偽造がないか調べます</h1>

<form id="parse_html-form" action="$PROGRAM" method="post" enctype="multipart/form-data" onSubmit="return checkSubmit('parse_html')">
<p>
<label>log.html: <input type="file" name="log-html" accept="text/html" />
</label>
</p>
<p>
<label>抽出する場合、抽出するメモの日時(改行区切り):
<textarea class="pickup" name="pickup" rows="8"></textarea>
</label>
</p>
<div id="parse_html-captcha" class="captcha parse_html-captcha"></div>
<input type="submit" value="送信" id="parse_html-submit"/>
<input type="hidden" name="cmd" value="parse_html">
</form>
EOT

  print <<"EOT" if $CHECK_SLOG;
<hr/>
<h1>ログ署名が取られてないか調べます</h1>

<form id="check_slog-form" action="$PROGRAM" method="post" enctype="multipart/form-data" onSubmit="return checkSubmit('check_slog')">
<p>
<label>調べるメモの日時(改行区切り):
<textarea class="pickup" name="pickup" rows="8"></textarea>
</label>
</p>
<p>または、
<label>log.html: <input type="file" name="log-html" accept="text/html" />
</label>
</p>
<div id="check_slog-captcha" class="captcha check_slog-captcha"></div>
<input type="submit" value="送信" id="check_slog-submit"/>
<input type="hidden" name="cmd" value="check_slog">
</form>
EOT

  print <<"EOT";
</body>
</html>
EOT
}

sub main {
  my $cmd = $CGI->param('cmd') || 'read';

  if ($cmd eq 'parse_html') {
    if ($USE_RECAPTCHA) {
      check_recaptcha() or die "reCAPTCHA failed.";
    }
    my $fh = $CGI->upload('log-html');
    if (! defined $fh) {
      my $err = $CGI->cgi_error;
      die "No file: $err";
    }
    binmode($fh);
    die "Th file is too large." if -s $fh > $LIMIT;
    my $s = join("", <$fh>);
    my @pickup = split(/[,\s]+/,
		       decode('UTF-8', $CGI->param('pickup') || ''));
    @pickup = grep {$_ ne ''} @pickup;
    print_parse_html(decode('UTF-8', $s), pickup => [@pickup]);
  } elsif ($CHECK_SLOG && $cmd eq 'check_slog') {
    if ($USE_RECAPTCHA) {
      check_recaptcha() or die "reCAPTCHA failed.";
    }
    my $fh = $CGI->upload('log-html');
    my @parsed;
    if (defined $fh) {
      binmode($fh);
      die "Th file is too large." if -s $fh > $LIMIT;
      my $s = join("", <$fh>);
      @parsed = parse_get_datetime(decode('UTF-8', $s));
    }
    my @pickup = split(/[,\s]+/,
		       decode('UTF-8', $CGI->param('pickup') || ''));
    @pickup = grep {$_ ne ''} @pickup;

    @pickup = uniq(@parsed, @pickup);
    if (@pickup) {
      print_check_slog(pickup => [@pickup]);
    } else {
      print_page();
    }
  } else {
    print_page();
  }
}

main();
exit(0);

#!/usr/bin/perl
our $VERSION = "0.0.8"; # Time-stamp: <2020-06-29T17:23:52Z>";

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
use Getopt::Long;

our $CONSOLE_ENCODING = 'UTF-8';
our $KEY_FILE = "shared_memo_key.xml";
our $LOG = "shared_memo.log";
our $UNESCAPE_HTML = 0;
our $DROP_LAST_NEWLINE = 0;
our $PARSE_HTML = 0;
our $DATETIME;
our $NICKNAME = "管理人";
our $BY_SIGNER = 0;
our $CLOSED = 1;
our $TITLE = "証明書";
our $CSS = "shared_memo.css";
our $HASH_VERSION = "0.0.8.3";
our $IP;
our $KEY;
our $NO_KEY = 0;
our $NO_LOG = 0;
our $OUTPUT;

@ARGV = map { decode($CONSOLE_ENCODING, $_) } @ARGV;
Getopt::Long::Configure("bundling", "auto_version");
GetOptions(
	   "k=s" => \$KEY_FILE,
	   "no-key|n" => \$NO_KEY,
	   "no-log" => \$NO_LOG,
	   "time|t=s" => \$DATETIME,
	   "ip|i=s" => \$IP,
	   "unescape-html|u" => \$UNESCAPE_HTML,
	   "parse-html|H" => \$PARSE_HTML,
	   "output-certificate|o=s" => \$OUTPUT,
	   "signer=s" => \$NICKNAME,
	   "by-signer" => \$BY_SIGNER,
	   "open" => sub {$CLOSED = 0;},
	   "drop-last-newline|d" => \$DROP_LAST_NEWLINE,
	   "help|h" => sub {usage(0);},
	  ) or usage(1);

sub usage {
  my ($i) = @_;

  print "Usage: calc_hash.pl --no-log -t DATETIME -i IPADDR TXT_FILE\n";
  print "   or: calc_hash.pl -H -i IPADDR PART_FILE_OF_LOG_HTML\n";
  exit($i);
}

if (! defined $DATETIME && ! $PARSE_HTML) {
  die "You need to specify -t DATETIME .\n";
}

if (defined $OUTPUT && $PARSE_HTML) {
  die "-o is not supported with -H.\n";
}

if (defined $OUTPUT && $NO_KEY) {
  die "-o is not supported with -n.\n";
}

usage(1) if @ARGV > 1;

sub datetime { # ISO 8601 extended format.
  my ($sec, $min, $hour, $mday, $mon, $year, $wday) = gmtime(time);
  $year += 1900;
  $mon ++;
  return sprintf("%d-%02d-%02dT%02d:%02d:%02dZ",
		 $year, $mon, $mday, $hour, $min, $sec);
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

sub parse_html {
  my ($s) = @_;

  $s =~ s/\x0d\x0a/\x0a/sg;

  read_key() if ! defined $KEY;
  my $hmac = Digest::HMAC_SHA1->new($KEY);

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
  my $sign_hash;
  my $sign_person;
  my $sign_datetime;
  my $sign_ip;
  my $sign_nickname;
  my $sign_error = 0;
  if ($s =~ /<p class=\"your-ip\"[^>]*>■ (署名者|あなた|作者)は ([^ ]+) に IPアドレス ([^ ]+) からアクセス/s) {
    $sign_person = $1;
    $sign_datetime = $2;
    $sign_ip = $3;
    $IP = $IP || $sign_ip;
  } elsif ($s =~ /<p class=\"your-ip\"[^>]*>■ (署名者|あなた|作者)は ([^ ]+) にアクセス/s) {
    $sign_person = $1;
    $sign_datetime = $2;
  }

  if ($s =~ /<p class=\"sign-hash\">Sign Hash: ([^<]+)/s) {
    $sign_hash = $1;
    if ($s =~ /<p class=\"signed-by\">[^:]+: ([^<]*)/s) {
      $sign_nickname = unescape_html($1);
    }
    $hmac2 = Digest::HMAC_SHA1->new($KEY);
  }

  my $memos = 0;
  my $dels = 0;
  while ($s =~ /<pre( [^>]*)?>([^<]*)/s) {
    $memos++;
    my $p = $`;
    $s = $';
    my $text = unescape_html($2);
    my $class = $1 || "";
    my $deleted = ($class =~ /deleted/);
    my $datetime = $DATETIME;
    if (! defined $DATETIME) {
      if ($p !~ /<span\s+class=\"datetime\">\s*<a[^>]+>([^<]+)/s) {
	die "You need to specify -t DATETIME .\n";
      }
      $datetime = $1;
    }
    my $hash = get_hash($datetime . $text, $datetime . ($IP || ""));
    my $ipmark = "○";
    if (defined $hmac2) {
      if ($p =~ /<span\s+class=\"ipmark([^\"]*)\">([^<]+)/s) {
	$ipmark = $2;
	my $delclass = $1;
	my $delmark = "";
	if ($delclass =~ /deleted-by-me/) {
	  $delmark = "●";
	} elsif ($delclass =~ /deleted-by-other/) {
	  $delmark = "○";
	}
	$hmac2->add(encode('UTF-8', $datetime . $ipmark . $delmark));
      }
    }
    if ($deleted) {
      $dels ++;
      my $h1a = substr($hash, 0, 2);
      my $h1b = substr($hash, 2, 4);
      my $h1c = substr($hash, 6);
      my $hash2 = "          ";
      if ($p =~ /<span\s+class=\"hash\">([^<]+)/s) {
	$hash2 = $1;
	$hmac->add($datetime . $1);
      }
      my $h2a = (length($hash2) >= 6)? substr($hash2, 0, 2) : "  ";
      my $h2b = "    ";
      my $h2c = (length($hash2) >= 4)? substr($hash2, -4) : "    ";
      my $n = "  ";
      my $ok = "   ";
      my $ip = "   ";
      # $n = " n" if $h1a ne $h2a;
      # $ok = " ok" if $h1b eq $h2b;
      $ip = " ip" if defined $IP && $h1c eq $h2c;
      print "$h2a    $h1c$n$ok$ip\n";
    } else {
      my $h1a = substr($hash, 0, 2);
      my $h1b = substr($hash, 2, 4);
      my $h1c = substr($hash, 6);
      my $hash2 = "          ";
      if ($p =~ /<span\s+class=\"hash\">([^<]+)/s) {
	$hash2 = $1;
	$hmac->add($datetime . encode('UTF-8', escape_html($text)) . $1);
      }
      my $h2a = (length($hash2) >= 2)? substr($hash2, 0, 2) : "  ";
      my $h2b = (length($hash2) >= 6)? substr($hash2, 2, 4) : "    ";
      my $h2c = (length($hash2) >= 10)? substr($hash2, 6) : "    ";
      my $n = "  ";
      my $ok = "   ";
      my $ip = "   ";
      $n = " n" if $h1a ne $h2a;
      $ok = " ok" if $h1b eq $h2b;
      $ip = " ip" if defined $IP && $h1c eq $h2c;
      print "$hash$n$ok$ip\n";
    }
  }

  if (defined $SUM_HASH && ! $NO_KEY) {
    my $sum_hash = substr($hmac->b64digest, 0, 16);
    if ($SUM_HASH eq $sum_hash && $memos == $N && $DELS == $dels) {
      print "Sum Hash is ok.\n";
    } else {
      print "Sum Hash is not ok.\n";
    }
    if (defined $hmac2) {
      if (defined $sign_ip) {
	$hmac2->add(encode('UTF-8',
			   "datetime: $sign_datetime"
			   . " person: $sign_person"
			   . " nickname: $sign_nickname"
			   . " ip: $sign_ip"
			   . " sum_hash: $sum_hash"));
      } else {
	$hmac2->add(encode('UTF-8',
			   "datetime: $sign_datetime"
			   . " person: $sign_person"
			   . " nickname: $sign_nickname"
			   . " sum_hash: $sum_hash"));
      }
      if ($sign_hash eq substr($hmac2->b64digest, 0, 20)) {
	print "Sign Hash is ok.\n";
      } else {
	print "Sign Hash is not ok.\n";
      }
    }
  }
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
  flock($fh, LOCK_UN);
  close($fh);
  close($fh);
}

sub check_log_write {
  my ($datetime) = @_;
  my $file = $LOG;
  my @r;

  sysopen(my $fh, $file, O_RDONLY | O_CREAT)
    or die "Cannot open $file: $!";
  flock($fh, LOCK_SH)
    or die "Cannot lock $file: $!";
  binmode($fh);
  my $s = decode('UTF-8', join("", <$fh>));
  flock($fh, LOCK_UN);
  close($fh);

  while ($s =~ /^.*$/mg) {
    my $c = $&;
    if ($c !~ /^([^ ]+) write /) {
      next;
    }
    next if $datetime ne $1;
    $c = $';
    my $sid;
    if ($c =~ s/^\s*\(([^\)]+)\)\s*//s) {
      $sid = $1;
    }
    if ($c =~ s/^\s*([^ ]+)\s+([^ ]+)//) {
      push(@r, [$2, $sid]);
    }
  }
  return @r;
}

sub calc_hash {
  my ($text) = @_;

  my $subdate = 0;
  $subdate = $1 if $DATETIME =~ s/\((\d+)\)$//s;

  $text = unescape_html($text) if $UNESCAPE_HTML;
  $text =~ s/\r?\n$//s if $DROP_LAST_NEWLINE;

  my $sid;
  if (! $NO_LOG) {
    my @write = check_log_write($DATETIME);
    if (! $subdate && @write > 1) {
      die "You must specify (1) or (2) ... after DATETIME.";
    }
    if ($subdate > @write) {
      die "($subdate) is too large.";
    }
    $subdate = 1 if $subdate == 0;
    if (@write) {
      my $x = $write[@write - $subdate];
      $IP = $x->[0] if ! defined $IP;
      $sid = $x->[1];
      if (defined $OUTPUT && ! defined $sid) {
	warn "No SESSION_ID on the log at $DATETIME.\n";
      }
    } elsif (defined $OUTPUT) {
      warn "No writing infomation on the log at $DATETIME.\n";
    }
  }
  my $ip = $IP || "unknown";
  my $hash = get_hash($DATETIME . $text, $DATETIME . $ip);

  my $signer = ($BY_SIGNER)? "署名者" : "作者";

  if (defined $OUTPUT) {
    my $hmac = Digest::HMAC_SHA1->new($KEY);
    my $hmac2 = Digest::HMAC_SHA1->new($KEY);
    $hmac->add($DATETIME . encode('UTF-8', escape_html($text)) . $hash);
    my $sum_hash = substr($hmac->b64digest, 0, 16);
    $hmac2->add($DATETIME . encode('UTF-8', "●"));
    $hmac2->add(encode('UTF-8',
		       "datetime: $DATETIME"
		       . " person: $signer"
		       . " nickname: $NICKNAME"
		       . " ip: $ip"
		       . " sum_hash: $sum_hash"));
    my $sign_hash = substr($hmac2->b64digest, 0, 20);
    my $nickname = escape_html($NICKNAME);

    open(my $fh, ">", $OUTPUT) or die "$OUTPUT: $!";
    binmode($fh, ":raw:utf8");
    print $fh <<"EOT";
<!DOCTYPE html>
<html lang="ja">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta http-equiv="Content-Language" content="ja">
<meta name="robots" content="noindex,nofollow" />
<meta name="viewport" content="width=device-width,initial-scale=1" />

<title>$TITLE</title>
<!-- calc_hash.pl version $VERSION .
     You can get it from https://github.com/JRF-2018/shared_memo . -->
<link rel="stylesheet" href="$CSS" type="text/css" />
</head>
<body>
<div class="container" id="log-container">
<h1>$TITLE</h1>

<div class="memo">
<form "delete-form" id="delete-form-1" action="#" method="get">
<div class="info">
<span class="ipmark">●</span>
<span class="datetime"><a href="#">$DATETIME</a></span>
<span class="hash">$hash</span>
</div>
</form>
<pre>$text</pre>
</div>

<div class="post-info">
<p class="signed-by">ログ署名者: ${nickname}</p>
<p class="sign-hash">Sign Hash: $sign_hash</p>
<p class="sum-hash">Sum Hash: $HASH_VERSION:$sum_hash (1個中0個削除)</p>
<p class="your-ip">■ ${signer}は $DATETIME に IPアドレス $ip からアクセスしていました。</p>
</div>
</div>
</body>
</html>
EOT
    close($fh);

    if (defined $sid && ! $NO_LOG) {
      my $now = datetime();
      my $closed = "";
      $closed = "c" if $CLOSED;
      log_append("$now slog ($sid) $closed\"$nickname\" $ip calc_hash.pl\n");
    }
  }
  $hash = substr($hash, 0, 6) if ! defined $IP;
  return $hash;
}

sub print_hash {
  my ($s) = @_;
  $s = decode('UTF-8', $s);
  if ($PARSE_HTML) {
    parse_html($s);
  } else {
    my $hash = calc_hash($s);
    print "$hash\n";
  }
}

sub main {
  $KEY = " " x 64 if $NO_KEY;

  if (! @ARGV) {
    binmode(STDIN);
    print_hash(join("", <STDIN>));
  } else {
    my $f = shift(@ARGV);
    open(my $fh, "<", $f) or die "Cannot open $f: $!";
    binmode($fh);
    print_hash(join("", <$fh>));
    close($fh);
  }
}

main();
exit(0);

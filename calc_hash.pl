#!/usr/bin/perl
our $VERSION = "0.0.6"; # Time-stamp: <2020-06-09T17:19:20Z>";

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

our $KEY_FILE = "shared_memo_key.xml";
our $UNESCAPE_HTML = 0;
our $DROP_LAST_NEWLINE = 0;
our $PARSE_HTML = 0;
our $DATETIME;
our $IP;
our $KEY;
our $NO_KEY = 0;

Getopt::Long::Configure("bundling", "auto_version");
GetOptions(
	   "k=s" => \$KEY_FILE,
	   "no-key|n" => \$NO_KEY,
	   "time|t=s" => \$DATETIME,
	   "ip|i=s" => \$IP,
	   "unescape-html|u" => \$UNESCAPE_HTML,
	   "parse-html|H" => \$PARSE_HTML,
	   "drop-last-newline|d" => \$DROP_LAST_NEWLINE,
	   "help|h" => sub {usage(0);},
	  ) or usage(1);

sub usage {
  my ($i) = @_;

  print "Usage: calc_hash.pl -t DATETIME -i IPADDR FILE\n";
  print "   or: calc_hash.pl -H -i IPADDR PART_FILE_OF_LOG_HTML\n";
  exit($i);
}

if (! defined $DATETIME && ! $PARSE_HTML) {
  die "You need to specify -t DATETIME .\n";
}

usage(1) if @ARGV > 1;

sub unescape_html {
  my ($s) = @_;
  $s =~ s/\&quot\;/\"/sg;
#  $s =~ s/\&apos\;/\'/sg;
  $s =~ s/\&gt\;/>/sg;
  $s =~ s/\&lt\;/</sg;
  $s =~ s/\&amp\;/\&/sg;
  return $s;
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

  while ($s =~ /<pre( [^>]*)?>([^<]*)/s) {
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
    if ($deleted) {
      my $h1a = substr($hash, 0, 2);
      my $h1b = substr($hash, 2, 4);
      my $h1c = substr($hash, 6);
      my $hash2 = "          ";
      if ($p =~ /<span\s+class=\"hash\">([^<]+)/s) {
	$hash2 = $1;
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
}

sub calc_hash {
  my ($text) = @_;

  $text = unescape_html($text) if $UNESCAPE_HTML;
  $text =~ s/\r?\n$//s if $DROP_LAST_NEWLINE;
  my $hash = get_hash($DATETIME . $text, $DATETIME . ($IP || ""));
  $hash = substr($hash, 0, 6) if ! defined $IP;
  return $hash;
}

sub print_hash {
  my ($s) = @_;
  $s = decode('UTF-8', $s);
  if ($PARSE_HTML) {
    parse_html($s);
  } else {
    print calc_hash($s) . "\n";
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

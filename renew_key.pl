#!/usr/bin/perl
our $VERSION = "0.2.0"; # Time-stamp: <2021-12-12T09:00:14Z>";

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
our $MEMO_XML = "shared_memo.xml";
our $KEY_PREFIX = "shared_memo_key-";
our $LOG = "shared_memo.log";
our $DATETIME = datetime();
our $NO_LOG = 0;
our $OUTPUT;

@ARGV = map { decode($CONSOLE_ENCODING, $_) } @ARGV;
Getopt::Long::Configure("bundling", "auto_version");
GetOptions(
	   "key|k=s" => \$KEY_FILE,
	   "key-prefix=s" => \$KEY_PREFIX,
	   "output=s" => \$OUTPUT,
	   "no-log" => \$NO_LOG,
	   "help|h" => sub {usage(0);},
	  ) or usage(1);

sub usage {
  my ($i) = @_;

  print "Usage: renew_key.pl [--no-log]\n";
  exit($i);
}

usage(1) if @ARGV > 0;

sub datetime { # ISO 8601 extended format.
  my ($sec, $min, $hour, $mday, $mon, $year, $wday) = gmtime(time);
  $year += 1900;
  $mon ++;
  return sprintf("%d-%02d-%02dT%02d:%02d:%02dZ",
		 $year, $mon, $mday, $hour, $min, $sec);
}

sub renew_key {
  my $mfile = $MEMO_XML;
  my $kfile = $KEY_FILE;
  my @x;
  for (my $i = 0; $i < 64; $i++) {
    push(@x, int(rand(256)))
  }
  my $key = pack("C*", @x);
  my $skey = unpack("H*", $key);
  sysopen(my $kfh, $kfile, O_RDWR | O_CREAT)
    or die "Cannot open $kfile: $!";
  flock($kfh, LOCK_EX)
    or die "Cannot lock $kfile: $!";
  sysopen(my $mfh, $mfile, O_WRONLY | O_CREAT)
    or die "Cannot open $mfile: $!";
  flock($mfh, LOCK_EX)
    or die "Cannot lock $mfile: $!";
  binmode($kfh);
  my $s = join("", <$kfh>);
  if ($s !~ /<generated>([^<]+)<\/generated>/s) {
    die "Key file is broken.";
  }
  my $prev = $1;
  $prev =~ s/[\-\:]//sg;
  if (! defined $OUTPUT) {
    $OUTPUT = $KEY_PREFIX . $prev . ".xml";
  }
  sysopen(my $ofh, $OUTPUT, O_WRONLY | O_EXCL | O_CREAT)
    or die "Cannot open $OUTPUT: $!";
  flock($ofh, LOCK_EX)
    or die "Cannot lock $OUTPUT: $!";
  binmode($ofh);
  print $ofh $s;
  flock($ofh, LOCK_UN);
  close($ofh);
  seek($kfh, 0, 0);
  binmode($kfh);
  print $kfh <<"EOT";
<keyinfo>
<key>$skey</key>
<generated>$DATETIME</generated>
</keyinfo>
EOT
  truncate($mfh, 0);
  flock($mfh, LOCK_UN);
  close($mfh);
  flock($kfh, LOCK_UN);
  close($kfh);
  chmod(0600, $kfile);
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

sub main {
  renew_key();
  log_append("$DATETIME renew_key\n") if ! $NO_LOG;
}

main();
exit(0);

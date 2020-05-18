#!/usr/bin/perl
our $VERSION = "0.0.1"; # Time-stamp: <2020-05-18T01:13:59Z>

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

## 参考: 《Perl で QRcode を作ってみる - amari3の日記》  
## https://amari3.hatenablog.com/entry/20100403/1270313835

use utf8; # Japanese
use strict;
use warnings;

use GD::Barcode::QRcode;
use Getopt::Long;

our $OUTPUT;
our $QR_VERSION = 3;
our $SIZE = 3;

Getopt::Long::Configure("bundling", "auto_version");
GetOptions(
	   "o=s" => \$OUTPUT,
	   "v=i" => \$QR_VERSION,
	   "s=i" => \$SIZE,
	   "help|h" => sub {usage(0);},
	  ) or usage(1);

sub usage {
  my ($i) = @_;
  print "Usage: gen_qr_code.pl -o OUT_PNG -s PIXEL_SIZE URL\n\n";
  print "If overflow error occurs, count up QR_VERSION .\n";
  exit($i);
}

if (@ARGV != 1) {
  usage(1);
}

our $url = shift(@ARGV);

our $png;

while ($QR_VERSION <= 40) {
  eval {
    my $qr  = GD::Barcode::QRcode->new
      ($url, {Ecc => 'M', Version => $QR_VERSION, ModuleSize => $SIZE})->plot;
    $png = $qr->png;
  };
  last if ! $@;
  $QR_VERSION++;
}

die $@ if $@;

if (defined $OUTPUT) {
  open my $fh, '>', $OUTPUT or die;
  print {$fh} $png;
  close $fh;
} else {
  binmode(STDOUT);
  print $png;
}

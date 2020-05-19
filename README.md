# グローバル共有メモ

<!-- Time-stamp: "2020-05-19T06:10:39Z" -->


## 概要

グローバルに共有して使うメモのウェブアプリです。


## ブログ等で使う場合

グローバル共有メモのウィジェットをブログ等で使う場合、ウィジェットを挿
入したい位置に次のようなコードを書きます。

```html
<script type="text/javascript">SHARED_MEMO_WIDGET_WIDTH="auto"; SHARED_MEMO_WIDGET_ROWS=8;</script>
<script type="text/javascript" src="http://jrockford.s1010.xrea.com/demo/shared_memo_widget.js"></script>
```

もし、ウィジェットの width を固定したい場合は、次のように書きます。
(200px で固定します。)

```html
<script type="text/javascript">SHARED_MEMO_WIDGET_WIDTH=200; SHARED_MEMO_WIDGET_ROWS=8;</script>
<script type="text/javascript" src="http://jrockford.s1010.xrea.com/demo/shared_memo_widget.js"></script>
```

TEXTAREA の rows を変更したい場合は、上の SHARED_MEMO_WIDGET_ROWS に代
入する値を変えましょう。

もし IE にも対応したいのならば、IE では height の自動調整が効きません
ので、IE 用に height を設定することになります。しかし、height を設定す
るとそのままでは自動調整は OFF になるので、IE 以外のブラウザで自動調整
を残したい場合は、さらに auto_height を 1 に設定する必要があります。
rows を変更するには結局、次のように設定することになります。

```html
<script type="text/javascript">
SHARED_MEMO_WIDGET_ROWS=20;
SHARED_MEMO_WIDGET_WIDTH=200;
SHARED_MEMO_WIDGET_AUTO_WIDTH=1;
SHARED_MEMO_WIDGET_HEIGHT=420;
SHARED_MEMO_WIDGET_AUTO_HEIGHT=1;
</script>
<script type="text/javascript" src="http://jrockford.s1010.xrea.com/demo/shared_memo_widget.js"></script>
```


## クローンサイトを生成する場合

このプログラムの GitHub レポジトリは
https://github.com/JRF-2018/shared_memo です。

https://github.com/JRF-2018/memo_cgi にあるものと違ってこれは、自分の
ブログサイト用に作ったウェブアプリで、そのソースを公開するために一応、
配布をしているという体裁です。

ただ、クローンサイトを作りたいというのであれば、それほど難しくありませ
ん。そのためにやることはいくつかあります。

やること 1 つ目、shared_memo_widget.js の CGI の変数をクローンサイト用
に書き換える。

やること 2 つ目、shared_memo.css で指定している textar-min.ttf フォン
トをクローンサイトの /fonts 以下に置く。フォントは ↓ にアーカイブがあ
ります。@font-face で指定するフォントには同一ドメイン制約があるので、
これが必要になります。

《Textar Font(temporary)》  
https://yamacraft.github.io/textar-font/

やること 3 つ目、shared_memo_log.png を自分用に生成する。
GD::Barcode::QRcode がインストールされている perl を用いれば、次のコマ
ンドで生成できます。(ちなみに XREA の perl にはインストールされてます。)

```sh
perl gen_qr_code.pl http://jrockford.s1010.xrea.com/demo/shared_memo.cgi\?cmd=log -o shared_memo_log.png
```

http://jrockford.s1010.xrea.com/demo/ の部分は自分のサイト用に書き換え
てください。または、QR コードを生成するサイトはいろいろありますので、
そこで http://jrockford.s1010.xrea.com/demo/shared_memo.cgi?cmd=log み
たいな URL の QR コードを生成し、shared_memo_log.png にすれば良いでしょ
う。

やること 4 つ目、.htaccess を設定する。直接ログ等が見られないようにす
べきです。.htaccess にたとえば次のように設定しましょう。

```
<Files ~ "\.(log|xml|pl|md)$">
  deny from all
</Files>
```

あとは、このアーカイブのファイルをディレクトリに置いて動かしてください。
上に書いたブログ等に挿入するウィジェットコードの shared_memo_widget.js
の位置を書き換えるのを忘れずに。また、cgi のパーミッションの設定も忘れ
ずに。


## 更新情報

更新情報は↓をご参照ください。

《グローバル共有メモ - JRF のソフトウェア Tips》  
http://jrf.cocolog-nifty.com/software/2020/05/post-dd6738.html


## License

The author is a Japanese.

I intended this program to be public-domain, but you can treat
this program under the (new) BSD-License or under the Artistic
License, if it is convenient for you.

Within three months after the release of this program, I
especially admit responsibility of efforts for rational requests
of correction to this program.

I often have bouts of schizophrenia, but I believe that my
intention is legitimately fulfilled.


----
(This document is mainly written in Japanese/UTF8.)

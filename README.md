# グローバル共有メモ

<!-- Time-stamp: "2020-06-03T14:29:30Z" -->


## 概要

グローバルに共有して使うメモのウェブアプリです。

↓に動いているサービスがあります。

《グローバル共有メモ》  
http://jrockford.s1010.xrea.com/demo/shared_memo.cgi


## メモを使うユーザーへのヒント

誰でも書け、誰でも消せます。街中の黒板のようなものです。

メモは 200 個を越えたところで 200個より前のものは消去されます。

「グローバル共有メモ: ログ」ページについて。

日時は世界標準時で、日時の右の灰色の不思議な文字列は偽造防止のための
「ハッシュ」です。

日時の左の先頭の丸は、自分が書いたか・削除したか否かを表します。●は自
分が書いたもの、○は他人が書いたもの、赤は他人が削除したもので、青緑は
自分が削除したものです。赤の●は、自分が書いて他人が削除したもので、注
意を要します。

自分かどうかの識別子は 10 日前後で、いっせいに更新されます。その日以降
の「自分」は別人とみなされます。


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

やること 5 つ目、もし、Google reCAPTCHA v2 checkbox が使いたい場合は、
Google で reCAPTCHA の設定をしたあと、shared_memo.cgi の $USE_RECAPTCHA
= 1にし、$RECAPTCHA_SECRET_KEY と $RECAPTCHA_SITE_KEY を設定してくださ
い。

あとは、このアーカイブのファイルをディレクトリに置いて動かしてください。
上に書いたブログ等に挿入するウィジェットコードの shared_memo_widget.js
の位置を書き換えるのを忘れずに。また、cgi のパーミッションの設定も忘れ
ずに。


## メモのハッシュの計算方法 その１

「メモのハッシュの計算方法」は専門的なトピックになります。普通の人は読
み飛ばしてください。

メモを書き換えすると、ログに ISO 8601 拡張形式の日時と削除ボタンの間に
何やら意味のなさそうなグレーの文字列が並んでいます。これが、「ハッシュ」
で、簡単にいうと偽造を防止するためにあります。

詳しく説明します。

このアプリはログを残します。メモの「ログ」こと「メッセージリスト」の他
に、書換・削除の際の日時や IP アドレスなどが残る「書込ログ」が取られて
います。

この両者のログには自動的に大きくなり過ぎるとカットする機能があります。
そのため、情報が残ることを嫌う攻撃者によって、大量ポストによる「消去」
が図られるおそれがあります。

このアプリではできるだけメモを完全消去し、大量ポストを無意味にしていま
す。

しかし、そうしていると、次に、文句を言うがためにスクリーンショットを取
る人が現れ、それが IP アドレス開示を迫ってきたときどうするかという問題
が出てきます。もし書込者に本当に問題があるなら、開示してもいっこうにか
まわないのですが、仮に逆にこの開示請求者が悪意を持っているとした場合、
問題となります。

そこで、「メッセージリスト」にハッシュを載せることにしました。これで悪
意のある開示請求者は相当排除できると考えています。しかし、こちらを強く
すると、問題は、「書込ログ」に残る IP アドレスを消したい者がまた現れ、
大量ポストする誘引ができることになります。

いっそのこと、IP アドレスも「メッセージリスト」に表示してしまうという
手もあったのですが、そうすると、事情をよく知らないプロバイダが悪意のあ
る開示請求者にだまされる誘引を作ることになりかねません。

そこで IP アドレスのハッシュも「メッセージリスト」に表示することにしま
した。「メッセージリスト」のハッシュはメモごとに一つに見えますが、実は
二つの部分、「メッセージハッシュ」と「IP ハッシュ」からなっています。
(削除をしたときは、削除者の IP ハッシュだけが残るようになっています。)

これにより「メッセージリスト」「書込ログ」の二つのログが実質的に消去さ
れても、開示請求者の側にメッセージリストが保存されており、怪しい IP ア
ドレスの心あたりがあれば、その IP アドレスからの書込・削除であったこと
を確認できるようになっています。

これにより大量ポスト攻撃の誘引も減るし、悪意のある開示請求者への誘引も
減ることと私は考えています。

実は「メッセージハッシュ」は「確認ハッシュ」と「検証ハッシュ」のさらに
二つの部分になります。よって「ハッシュ」全体は、「確認ハッシュ」と「検
証ハッシュ」と「IP ハッシュ」の三つの部分からなることになります。

「検証ハッシュ」と「IP ハッシュ」の値を得るためには、shared_memo.cgi
が生成したキーファイル shared_memo_key.xml が必要です。「確認ハッシュ」
にはそれが必要ありません。

ですから、弁護士などが、開示請求のための依頼を受けたとき、「確認ハッ
シュ」だけはチェックすることで、「ずさんな偽造」については
shared_memo.cgiの管理者などに問い合わせる前に排除することができるよう
になっています。

なお、確認ハッシュ、検証ハッシュは日時にメッセージを連結したものに対し
て取っています。IP ハッシュは日時に IP アドレスを連結したものに対して
取っています。

確認ハッシュ、検証ハッシュに日時を連結するのは、日時の偽装がなされない
ためです。

IP ハッシュに日時を連結するのは、少し考えてこうしました。日時を連結せ
ず IP アドレスそのものはわからないが同じ IP アドレスの投稿かはわかるよ
うにするという方向はありうると思います。しかし、IP アドレスというもの
はしばしば変わるもので、突然ハッシュが変わって別人が書いたことにされた
り、IP ハッシュの変化の傾向によって使っているプロバイダを予想できたり
したりしたら、あまり穏やかではありません。そこで、同じ IP アドレスかど
うかがユーザーからはわからないように日時連結をすることにしたのでした。

もちろん、こういうトラブルが実際に起こることを「想定している」というこ
とではありません。こういうトラブルにも容易に対処できることを示すことで、
攻撃者が現れにくくするということです。


## メモのハッシュの計算方法 その２ calc_hash.pl の使い方

ハッシュが「真正」なものかどうかの計算をサポートするための calc_hash.pl
がこのアーカイブには同梱されています。

まず、shared_memo_key.xml を持つ管理者に問う前に、弁護士などが「ずさん
な偽造」をチェックするためには、保存されたメッセージリストを log.html
として、次のように実行します。

```sh
$ perl calc_hash.pl -H -n log.html
```

このように perl を実行すると、偽造がされていなければ、ハッシュの値だけ
がメモの数だけ表示されます。ハッシュが10桁のものはメッセージの残ってい
るもの、ハッシュが4桁のものはメッセージが削除されているものです。しか
し、もし、「ずさんな偽造」がされていれば、残っているメッセージのハッシュ
の値の横に n が表示されます。

開示を求めるものにだけ n が表示されれば、「ずさんな偽造」が行われてい
ると考えてよさそうです。しかし、こういうシステムがあることをわかって、
そういうことをする者はいないでしょう。

ほとんどすべてに n が表示される場合、それは逆にメッセージリストの
log.html ファイルに何らかのミスがあると考えるべきかもしれません。改行
コード(lf)や文字コード(utf-8)を変えて試してみるべきでしょう。

開示請求の場所など関係なく、途中から n が付く場合は shared_memo.cgi の
バージョンの違いによりハッシュを取るためアルゴリズムが変わっているのか
もしれません。それについては、下の更新情報で確かめましょう。

さて、ここで「ずさんな偽造」がないとなったら、管理者の出番です。管理者
は n が出ない log.html を渡されたとしましょう。

怪しい IP アドレスを XXX.XXX.XXX.XXX とし、shared_memo.cgi が生成した
キーファイル shared_memo_key.xml がカレントディレクトリにあると
ころで、次のように実行します。

```sh
$ perl calc_hash.pl -H -i XXX.XXX.XXX.XXX log.html
```

そうすると、メモごとに計算されたハッシュとその横にメッセージハッシュが
あっていれば ok と、IP ハッシュがあっていれば ip と表示されます。原理
的に削除されているハッシュは ok と表示されることはなく ip のみ表示され
る可能性があります。

もし、削除されてないすべてのメッセージに ok が表示されていれば
log.html は真正であると考えてまず間違ありません。ok のところでさらに
ip が書かれていれば、その書込は「怪しい IP アドレス」からによるものと
言ってまず間違いがありません。(ただし、ハッシュを取るアルゴリズムやキー
ファイルに変更があった場合はこの限りではありません。)

削除されていないもので ok が出ていないのに ip が合っているというのには
注意を要します。それは本来ありえないからです。もしそうなっていれば、キー
が盗まれたことを脅迫的にほのめかされていると考えるべきなのかもしれませ
ん。


## メモのハッシュの計算方法 その３ log.html がないとき

管理者に届けられたとき log.html はないが画像のスクリーンショットがあり、
日時(2020-05-18T14:36:47Z とします)と怪しい IP アドレス
(XXX.XXX.XXX.XXX とします)がわかっているという場合、次のようにコマンド
を実行します。

```sh
$ echo "" | perl calc_hash.pl -t 2020-05-18T14:36:47Z -i XXX.XXX.XXX.XXX
XXYYYYZZZZ
```

このとき表示されるハッシュ XXYYYYZZZZ のうち、XXYYYY の部分はメッセー
ジハッシュで、今回は関係ありません。後ろ4文字の ZZZZ が IP ハッシュで、
ここがスクリーンショットのハッシュと一致していれば、その IP から書かれ
たものであることが確認できます。

しかし、スクリーンショットのメッセージの部分のみ不正に書き換えることは
できるので、そのメッセージそのものを書いたことは確認できないこと
には注意が必要です。

もちろん、スクリーンショットからメッセージを復元できればいいのですが、
スペースや細かな文字の違いでハッシュが合わなくなるため、あまりあてには
できません。が、復元したメッセージのハッシュも合うようなら、それはメッ
セージの確認も取れたことになります。

管理者に届ける前の弁護士の段階で、メッセージの復元だけ試みることもでき
ます。その場合、復元したメッセージのファイルが tmp.txt で日時が
2020-05-18T14:36:47Z とすると、

```sh
$ perl calc_hash.pl -n -t 2020-05-18T14:36:47Z tmp.txt
XXYYYY
```

と表示されたとき、XX がハッシュの先頭二文字と合っていれば、復元が成功
している可能性がかなり高いことになります。ただ、これはとても難しく、末
尾の改行の有無などにも注意が必要です。そこまでやるなら calc_hash.pl の
ソースをちゃんと読んでからトライすることをオススメします。


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

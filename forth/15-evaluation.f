: evaluate source-sector @ >r blk @ >r 0 source-sector ! 0 blk ! (evaluate) r> blk ! r> source-sector ! ;
: native-colon lit : ;
native-colon constant colon-xt
: : >in @ >r parse-name nip dup 0= swap 32 u< 0= or if r> drop fail then r> >in ! colon-xt execute ;
: type begin dup while over c@ emit swap 1+ swap 1- repeat 2drop ;
: cr 13 emit 10 emit ;
: space 32 emit ;
enter-next

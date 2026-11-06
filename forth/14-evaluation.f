: 4096* 256* 2* 2* 2* 2* ;
4096 4 + constant frame-base
variable blk
: frame-address eval-depth @ 4096* frame-base + ;
: (evaluate) dup 4094 u> if 2drop fail then eval-depth @ 4 u< 0= if 2drop fail then >in @ >r source-length @ >r 0 frame-address source-length @ 2 + move 1 eval-depth +! dup source-length ! 0 swap move 32 source-length @ c! 0 source-length @ 1+ c! 0 >in ! interpret -1 eval-depth +! frame-address 0 r@ 2 + move r> source-length ! r> >in ! ;
enter-next

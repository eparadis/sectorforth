4096 constant 4096
32768 constant 32768
: c@ @ ff and ;
: c! dup @ ff invert and rot ff and or swap ! ;
create dispatch 0 , 0 ,
: init-dispatch lit exit dispatch 2 + ! ;
init-dispatch
: jump rp@ ! ;
: execute dispatch ! dispatch jump ;
: boot-address lit boot ;
boot-address constant boot-xt
boot-xt 10 4 + + c@ boot-xt + 10 5 + + constant error-xt
variable eval-depth
: fail 0 eval-depth ! error-xt execute ;
0 0 8 load

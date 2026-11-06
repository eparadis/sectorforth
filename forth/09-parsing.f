: space? >in @ source-length @ u< if >in @ c@ 32 = else 0 then ;
: token? >in @ source-length @ u< if >in @ c@ 32 <> else 0 then ;
: parse-name begin space? while 1 >in +! repeat >in @ begin token? while 1 >in +! repeat >in @ over - ;
: same? >r begin r@ while over c@ over c@ <> if 2drop r> drop 0 exit then 1+ swap 1+ swap r> 1- >r repeat r> drop 2drop 0 invert ;
next-source

: cmove >r begin r@ while over c@ over c! 1+ swap 1+ swap r> 1- >r repeat r> drop 2drop ;
: cmove> dup if >r r@ 1- + swap r@ 1- + swap begin r@ while over c@ over c! 1- swap 1- swap r> 1- >r repeat r> drop else drop then 2drop ;
: move >r 2dup u< if r> cmove> else r> cmove then ;
: fill >r begin dup while over r@ swap c! swap 1+ swap 1- repeat 2drop r> drop ;
variable source-length
variable lookup-name
variable lookup-length
: source 0 source-length @ ;
next-source

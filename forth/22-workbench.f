: list block 16 >r begin r@ while dup 64 type cr 64 + r> 1- >r repeat r> drop drop ;
: load blk @ >r dup blk ! block 1024 (evaluate) r> blk ! ;
: thru >r >r begin r@ r2@ u> 0= while r@ load r> 1+ >r repeat r> drop r> drop ;
enter-next

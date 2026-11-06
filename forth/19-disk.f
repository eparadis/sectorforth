: sector-evaluate dup 0= if drop fail then source-sector @ >r blk @ >r dup source-sector ! 0 blk ! source-data read-sector if fail then source-data 511 (evaluate) r> blk ! r> source-sector ! ;
: r2@ rp@ 4 + @ ;
: sector-thru >r >r begin r@ r2@ u> 0= while r@ sector-evaluate r> 1+ >r repeat r> drop r> drop ;
enter-next

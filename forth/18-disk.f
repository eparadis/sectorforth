: next-source source-sector @ dup 0= if drop fail then 1+ sector-load ;
: 9* dup 2* 2* 2* + ;
: chs>sector dup 0= over 9 u> or if drop 2drop fail then >r dup 2 u< 0= if 2drop r> drop fail then over 40 u< 0= if 2drop r> drop fail then swap 2* + 9* r> 1- + ;
: load-chs chs>sector sector-load ;
enter-next

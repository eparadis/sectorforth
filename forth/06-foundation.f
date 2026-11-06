: u< 2dup xor 32768 and if swap 32768 and 0= swap drop else - 32768 and 0<> then ;
: < 32768 xor swap 32768 xor swap u< ;
: > swap < ;
: u> swap u< ;
: u/mod dup 0= if 2drop fail then 0 >r begin 2dup u< 0= while swap over - swap r> 1+ >r repeat drop r> ;
: 10* dup 2* 2* + 2* ;
7 10* 2 + 10* constant disk-sectors
: load-chs load ;
variable source-sector
: sector>chs 9 u/mod 2 u/mod swap rot 1+ ;
0 0 9 load

: (disk-io) io-mode ! over disk-sectors u< 0= if 2drop -1 exit then prepare-io swap sector>chs rot 256* + swap 256* boot-drive + swap rot boot-xt execute restore-io 256 u/mod nip ;
: read-sector 2 (disk-io) ;
: write-sector over 0= if 2drop -1 exit then 3 (disk-io) ;
frame-base 16384 + constant block-data
block-data 1024 + constant source-data
: sector-load dup 0= if drop fail then dup 0 read-sector if drop fail then source-sector ! 511 source-length ! 0 >in ! ;
enter-next

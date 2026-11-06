: sector-load dup 0= over disk-sectors u< 0= or if drop fail then dup source-sector ! sector>chs load-chs ;
: next-source source-sector @ 1+ sector-load ;
8 source-sector !
next-source

: match? dup 2 + c@ dup 64 and if 2drop 0 exit then 32 1- and lookup-length @ <> if drop 0 exit then 3 + lookup-name @ lookup-length @ same? ;
: find-name lookup-length ! lookup-name ! latest @ begin dup while dup match? if dup 2 + c@ 128 and swap 3 + lookup-length @ + swap exit then @ repeat 0 ;
variable number-value
variable number-sign
next-source

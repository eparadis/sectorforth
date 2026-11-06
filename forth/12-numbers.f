: number? 0 number-value ! 0 number-sign ! dup 0= if 2drop 0 exit then over c@ ascii-minus = if 1 number-sign ! swap 1+ swap 1- then dup 0= if 2drop 0 exit then begin dup while over c@ ascii-zero - dup 10 u< 0= if drop 2drop 0 exit then number-step 0= if 2drop 0 exit then swap 1+ swap 1- repeat 2drop number-sign @ if number-value @ 32768 u> if 0 exit then number-value @ negate else number-value @ then 0 invert ;
: compile-literal lit lit , , ;
next-source

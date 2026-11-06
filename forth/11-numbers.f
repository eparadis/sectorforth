4 10* 8 + constant ascii-zero
4 10* 5 + constant ascii-minus
6 10* 5 + 10* 5 + 10* 3 + constant digit-limit
: number-step number-value @ digit-limit u> if drop 0 exit then number-value @ digit-limit = over 5 u> and if drop 0 exit then number-value @ 10* + number-value ! 0 invert ;
next-source

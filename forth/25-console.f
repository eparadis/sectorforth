: recurse latest @ dup 2 + c@ 32 1- and + 3 + , ; immediate
: u. 10 u/mod dup if recurse else drop then .digit ;
: . dup 32768 and if 45 emit negate then u. space ;
: workbench cr begin 115 emit 102 emit 62 emit 32 emit 0 4094 accept cr 0 swap evaluate cr again ;
workbench

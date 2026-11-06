: literal compile-literal ; immediate
: interpret begin parse-name dup while find-name over if state @ if dup 0= if drop , else drop execute then else drop execute then else 2drop lookup-name @ lookup-length @ number? if state @ if compile-literal then else fail then then repeat 2drop ;
: enter-next next-source 512 1- source-length ! interpret ;
enter-next

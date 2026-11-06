: while lit ?branch , here @ 0 , ; immediate
: repeat swap lit branch , here @ - , dup here @ swap - swap ! ; immediate
: >rexit rp@ ! ;
: >r rp@ @ swap rp@ ! >rexit ;
: r> rp@ 2 + @ rp@ @ rp@ 2 + ! lit [ here @ 6 + , ] rp@ ! ;
: r@ rp@ 2 + @ ;
: rot >r swap r> swap ;
: -rot rot rot ;
: xor 2dup and invert -rot or and ;
: c! dup @ ff invert and rot ff and or swap ! ;
: c, here @ c! 1 here @ + here ! ;
: +! dup @ rot + swap ! ;
: allot here @ + here ! ;
0 0 6 load

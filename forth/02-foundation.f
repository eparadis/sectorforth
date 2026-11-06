: immediate latest @ 2 + dup @ 128 or swap ! ;
: [ 0 state ! ; immediate
: ] 1 state ! ;
: branch rp@ @ dup @ + rp@ ! ;
: ?branch 0= rp@ @ @ 2 - and rp@ @ + 2 + rp@ ! ;
: if lit ?branch , here @ 0 , ; immediate
: then dup here @ swap - swap ! ; immediate
: else lit branch , here @ 0 , swap dup here @ swap - swap ! ; immediate
: begin here @ ; immediate
: until lit ?branch , here @ - , ; immediate
: again lit branch , here @ - , ; immediate
0 0 5 load

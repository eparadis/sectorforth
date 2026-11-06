: reveal latest @ 2 + dup @ 64 invert and swap ! 0 state ! ;
: create : lit lit , here @ 4 + , lit exit , reveal ;
: variable create 0 , ;
: constant : lit lit , , lit exit , reveal ;
0 constant 0
1 constant 1
2 constant 2
3 constant 3
4 constant 4
5 constant 5
6 constant 6
7 constant 7
8 constant 8
9 constant 9
10 constant 10
ff constant ff
16 constant 16
18 constant 18
32 constant 32
64 constant 64
128 constant 128
256 constant 256
512 constant 512
1024 constant 1024
0 0 7 load

create boot-code 19 allot
boot-xt boot-code 19 move
boot-xt 9 + @ ff and constant boot-drive
variable io-mode
: prepare-io 36955 boot-xt ! 36953 boot-xt 5 + ! 144 boot-xt 7 + c! 36954 boot-xt 8 + ! 144 boot-xt 10 + c! 37008 boot-xt 13 + ! 36944 boot-xt 15 + ! 37008 boot-xt 17 + ! io-mode @ boot-xt 4 + c! ;
: restore-io boot-code boot-xt 19 move ;
enter-next

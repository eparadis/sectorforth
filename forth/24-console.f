: accept accept-limit ! accept-buffer ! 0 accept-count ! begin key dup 13 = if drop accept-count @ exit then dup 8 = if drop erase-key else dup 32 u< if drop else accept-count @ accept-limit @ u< if dup accept-buffer @ accept-count @ + c! emit 1 accept-count +! else drop then then then again ;
: edit-line block swap dup 16 u< 0= if 2drop fail then 2* 2* 2* 2* 2* 2* + dup 64 32 fill edit-prompt 64 accept drop update ;
: .digit 48 + emit ;
enter-next

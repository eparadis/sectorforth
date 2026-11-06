: key begin key ff and dup 0= while drop repeat ;
variable accept-buffer
variable accept-limit
variable accept-count
: erase-key accept-count @ if -1 accept-count +! 8 emit 32 emit 8 emit then ;
: edit-prompt cr 101 emit 100 emit 105 emit 116 emit 62 emit 32 emit ;
enter-next

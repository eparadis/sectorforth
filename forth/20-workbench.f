variable buffered-block
variable dirty
: block>sector dup 0= over 1408 u> or if drop fail then 1- 2* 64 + ;
: update -1 dirty ! ;
: save-buffers dirty @ if buffered-block @ block>sector dup block-data write-sector if drop fail then 1+ block-data 512 + write-sector if fail then 0 dirty ! then ;
: flush save-buffers 0 buffered-block ! ;
enter-next

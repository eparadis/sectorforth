: block dup buffered-block @ = if drop block-data exit then save-buffers dup block>sector 0 buffered-block ! dup block-data read-sector if 2drop fail then 1+ block-data 512 + read-sector if drop fail then buffered-block ! block-data ;
: buffer dup buffered-block @ <> if save-buffers dup block>sector drop buffered-block ! else drop then block-data ;
: blank-block block 1024 32 fill update ;
enter-next

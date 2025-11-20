#!/bin/sh

# replace the wallet addresses with your own

# to manually balance GPU resources between primary and secondary algorithms
# use `--dual-mode` parameter, e.g.
# `--dual-mode a12:r0.1` - minimum impact on the primary algorithm
# `--dual-mode a12:r128` - maximum impact on the primary algorithm

# octa + alph
./rigel -a ethash+alephium --coin [1]octa \
    -o [1]stratum+tcp://pool.vipor.net:5004             -u [1]YOUR_OCTA_WALLET \
    -o [2]stratum+tcp://de.alephium.herominers.com:1199 -u [2]YOUR_ALPH_WALLET \
    -w my_rig --log-file logs/miner.log

# octa + rxd
#./rigel -a ethash+sha512256d --coin [1]octa \
#    -o [1]stratum+tcp://pool.vipor.net:5004 -u [1]YOUR_OCTA_WALLET \
#    -o [2]stratum+tcp://pool.vipor.net:5066 -u [2]YOUR_RXD_WALLET \
#    -w my_rig --log-file logs/miner.log

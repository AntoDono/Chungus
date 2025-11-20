#!/bin/sh

# replace the wallet addresses with your own

# to manually balance GPU resources between primary and secondary algorithms
# use `--dual-mode` parameter, e.g.
# `--dual-mode a12:r0.1` - minimum impact on the primary algorithm
# `--dual-mode a12:r64` - maximum impact on the primary algorithm

# hyp + alph
./rigel -a ethashb3+alephium \
    -o [1]stratum+tcp://fr.vipor.net:5070                -u [1]YOUR_HYP_WALLET \
    -o [2]stratum+tcp://de.alephium.herominers.com:1199  -u [2]YOUR_ALPH_WALLET \
    -w my_rig --log-file logs/miner.log

# hyp + gram
#./rigel -a ethashb3+sha256ton \
#    -o [1]stratum+tcp://rth.eu.ekapool.com:18896 -u [1]YOUR_HYP_WALLET \
#    -o [2]stratum+tcp://ton.hashrate.to:4002     -u [2]YOUR_GRAM_WALLET \
#    -w my_rig --log-file logs/miner.log

# hyp + rxd
#./rigel -a ethashb3+sha512256d \
#    -o [1]stratum+tcp://rth.eu.ekapool.com:18896 -u [1]YOUR_HYP_WALLET \
#    -o [2]stratum+tcp://pool.vipor.net:5066      -u [2]YOUR_RXD_WALLET \
#    -w my_rig --log-file logs/miner.log

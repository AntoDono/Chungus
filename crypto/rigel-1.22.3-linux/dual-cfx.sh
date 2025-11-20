#!/bin/sh

# replace the wallet addresses with your own

# to manually balance GPU resources between primary and secondary algorithms
# use `--dual-mode` parameter, e.g.
# `--dual-mode a12:r0.1` - minimum impact on the primary algorithm
# `--dual-mode a12:r64` - maximum impact on the primary algorithm

# cfx + alph
./rigel -a octopus+alephium \
    -o [1]stratum+tcp://pool.woolypooly.com:3094         -u [1]YOUR_CFX_WALLET \
    -o [2]stratum+tcp://de.alephium.herominers.com:1199  -u [2]YOUR_ALPH_WALLET \
    -w my_rig --log-file logs/miner.log

# cfx + gram
#./rigel -a octopus+sha256ton \
#    -o [1]stratum+tcp://de.conflux.herominers.com:1170 -u [1]YOUR_CFX_WALLET \
#    -o [2]stratum+tcp://ton.hashrate.to:4002           -u [2]YOUR_GRAM_WALLET \
#    -w my_rig --log-file logs/miner.log

# cfx + rxd
#./rigel -a octopus+sha512256d \
#    -o [1]stratum+tcp://de.conflux.herominers.com:1170 -u [1]YOUR_CFX_WALLET \
#    -o [2]stratum+tcp://pool.vipor.net:5066            -u [2]YOUR_RXD_WALLET \
#    -w my_rig --log-file logs/miner.log

# cfx + xtm
#./rigel -a octopus+sha3x \
#    -o [1]stratum+tcp://de.conflux.herominers.com:1170 -u [1]YOUR_CFX_WALLET \
#    -o [2]stratum+tcp://tari.luckypool.io:6118         -u [2]YOUR_XTM_WALLET \
#    -w my_rig --log-file logs/miner.log

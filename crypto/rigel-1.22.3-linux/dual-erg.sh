#!/bin/sh

# replace the wallet addresses with your own

# to manually balance GPU resources between primary and secondary algorithms
# use `--dual-mode` parameter, e.g.
# `--dual-mode a12:r0.1` - minimum impact on the primary algorithm
# `--dual-mode a12:r128` - maximum impact on the primary algorithm

# erg + alph
./rigel -a autolykos2+alephium \
    -o [1]stratum+tcp://erg.kryptex.network:7777        -u [1]YOUR_ERG_WALLET  \
    -o [2]stratum+tcp://de.alephium.herominers.com:1199 -u [2]YOUR_ALPH_WALLET \
    -w my_rig --log-file logs/miner.log

# erg + gram
#./rigel -a autolykos2+sha256ton \
#    -o [1]stratum+tcp://erg.kryptex.network:7777 -u [1]YOUR_ERG_WALLET \
#    -o [2]stratum+tcp://ton.hashrate.to:4002     -u [2]YOUR_GRAM_WALLET \
#    -w my_rig --log-file logs/miner.log

# erg + rxd
#./rigel -a autolykos2+sha512256d \
#    -o [1]stratum+tcp://erg.kryptex.network:7777 -u [1]YOUR_ERG_WALLET \
#    -o [2]stratum+tcp://pool.vipor.net:5066      -u [2]YOUR_RXD_WALLET \
#    -w my_rig --log-file logs/miner.log

# erg + xtm
#./rigel -a autolykos2+sha3x \
#    -o [1]stratum+tcp://erg.kryptex.network:7777 -u [1]YOUR_ERG_WALLET \
#    -o [2]stratum+tcp://tari.luckypool.io:6118   -u [2]YOUR_XTM_WALLET \
#    -w my_rig --log-file logs/miner.log

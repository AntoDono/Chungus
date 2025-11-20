#!/bin/sh

# replace the wallet addresses with your own

# to manually balance GPU resources between primary and secondary algorithms
# use `--dual-mode` parameter, e.g.
# `--dual-mode a12:r0.1` - minimum impact on the primary algorithm
# `--dual-mode a12:r64` - maximum impact on the primary algorithm

# abel + alph
./rigel -a abelian+alephium \
   -o [1]stratum+ssl://pool-us.zkprovers.com:57778      -u [1]ABEL_POOL_USERNAME -p [1]ABEL_POOL_PASSWORD \
   -o [2]stratum+tcp://de.alephium.herominers.com:1199  -u [2]YOUR_ALPH_WALLET \
   -w my_rig --log-file logs/miner.log

# abel + gram
#./rigel -a abelian+sha256ton \
#   -o [1]stratum+ssl://global-service.abelpool.io:27778 -u [1]ABEL_POOL_USERNAME -p [1]ABEL_POOL_PASSWORD \
#   -o [2]stratum+tcp://ton.hashrate.to:4002             -u [2]YOUR_GRAM_WALLET \
#   -w my_rig --log-file logs/miner.log

# abel + rxd
#./rigel -a abelian+sha512256d \
#   -o [1]stratum+ssl://global-service.abelpool.io:27778 -u [1]ABEL_POOL_USERNAME -p [1]ABEL_POOL_PASSWORD \
#   -o [2]stratum+tcp://pool.vipor.net:5066              -u [2]YOUR_RXD_WALLET \
#   -w my_rig --log-file logs/miner.log

# abel + xtm
#./rigel -a abelian+sha3x \
#   -o [1]stratum+ssl://global-service.abelpool.io:27778 -u [1]ABEL_POOL_USERNAME -p [1]ABEL_POOL_PASSWORD \
#   -o [2]stratum+tcp://tari.luckypool.io:6118           -u [2]YOUR_XTM_WALLET \
#   -w my_rig --log-file logs/miner.log

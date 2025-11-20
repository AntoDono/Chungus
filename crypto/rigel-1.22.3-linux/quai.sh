#!/bin/sh

# replace the wallet addresses with your own

# mine to herominers
./rigel -a quai -o stratum+tcp://de.quai.herominers.com:1185 -u YOUR_QUAI_WALLET -w my_rig --log-file logs/miner.log

# mine to k1pool
#./rigel -a quai -o stratum+tcp://eu.quai.k1pool.com:3333 -u YOUR_K1POOL_WALLET -w my_rig --log-file logs/miner.log

# mine to kryptex
#./rigel -a quai -o stratum+tcp://quai.kryptex.network:7777 -u YOUR_QUAI_WALLET -w my_rig --log-file logs/miner.log

# mine to luckypool
#./rigel -a quai -o stratum+tcp://quai.luckypool.io:3333 -u YOUR_QUAI_WALLET -w my_rig --log-file logs/miner.log

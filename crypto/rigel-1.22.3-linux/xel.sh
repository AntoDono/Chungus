#!/bin/sh

# replace the wallet addresses with your own

# mine to vipor
./rigel -a xelishashv2 -o stratum+tcp://de.vipor.net:5077 -u YOUR_XEL_WALLET -w my_rig --log-file logs/miner.log

# mine to k1pool
#./rigel -a xelishashv2 -o stratum+tcp://eu.xel.k1pool.com:9351 -u YOUR_K1POOL_WALLET -w my_rig --log-file logs/miner.log

# mine to kryptex
#./rigel -a xelishashv2 -o stratum+tcp://xel.kryptex.network:7777 -u YOUR_XEL_WALLET -w my_rig --log-file logs/miner.log

# mine to herominers
#./rigel -a xelishashv2 -o stratum+tcp://de.xelis.herominers.com:1225 -u YOUR_XEL_WALLET -w my_rig --log-file logs/miner.log

# mine solo to a node
#./rigel -a xelishashv2 -o solo+tcp://127.0.0.1:8080 -u YOUR_XEL_WALLET -w my_rig --log-file logs/miner.log

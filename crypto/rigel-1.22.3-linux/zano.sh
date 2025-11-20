#!/bin/sh

# replace the wallet addresses with your own

# mine to luckypool
./rigel -a progpowz -o stratum+tcp://zano.luckypool.io:8888 -u YOUR_ZANO_WALLET -w my_rig --log-file logs/miner.log

# mine to woolypooly
#./rigel -a progpowz -o stratum+tcp://pool.woolypooly.com:3146 -u YOUR_ZANO_WALLET -w my_rig --log-file logs/miner.log

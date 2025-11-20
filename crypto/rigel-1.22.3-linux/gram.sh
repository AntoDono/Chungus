#!/bin/sh

# replace the wallet addresses with your own

# mine to icemining
./rigel -a sha256ton -o stratum+tcp://ton.hashrate.to:4002 -u YOUR_GRAM_WALLET -w my_rig --log-file logs/miner.log

# mine to hyperpool
#./rigel -a sha256ton -o stratum+tcp://stratum.hyperpool.pro:8040 -u YOUR_POOL_ID -w my_rig --log-file logs/miner.log

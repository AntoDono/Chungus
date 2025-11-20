#!/bin/sh

# replace the wallet addresses with your own

# mine to luckypool
./rigel -a sha3x -o stratum+tcp://tari.luckypool.io:6118 -u YOUR_XTM_WALLET -w my_rig --log-file logs/miner.log

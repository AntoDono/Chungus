#!/bin/sh

# replace the wallet addresses with your own

# mine to vipor
./rigel -a sha512256d -o stratum+tcp://pool.vipor.net:5066 -u YOUR_RXD_WALLET -w my_rig --log-file logs/miner.log

# mine to woolypooly
#./rigel -a sha512256d -o stratum+tcp://pool.woolypooly.com:3122 -u YOUR_RXD_WALLET -w my_rig --log-file logs/miner.log

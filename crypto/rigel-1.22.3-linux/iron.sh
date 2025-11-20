#!/bin/sh

# replace the wallet addresses with your own

# mine to herominers
./rigel -a fishhash -o stratum+tcp://de.ironfish.herominers.com:1145 -u YOUR_IRON_WALLET -w my_rig --log-file logs/miner.log

# mine to kryptex
#./rigel -a fishhash -o stratum+tcp://iron.kryptex.network:7777 -u YOUR_IRON_WALLET -w my_rig --log-file logs/miner.log

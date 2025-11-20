#!/bin/sh

# replace the wallet addresses with your own

# mine to 2miners
./rigel -a etchash -o stratum+ssl://etc.2miners.com:11010 -u 0xD9e815D700FCEFEa3D5777CDA381930a1588A0a9 -w yapper --log-file logs/miner.log

# mine to f2pool
#./rigel -a etchash -o stratum+tcp://etc.f2pool.com:8118 -u YOUR_ETC_WALLET -w my_rig --log-file logs/miner.log

#!/bin/sh

# replace the wallet addresses with your own

# mine to 2miners
./rigel -a kawpow --coin neox -o stratum+tcp://neox.2miners.com:4040 -u YOUR_NEOX_WALLET -w my_rig --log-file logs/miner.log

# mine to herominers
#./rigel -a kawpow --coin neox -o stratum+tcp://de.neoxa.herominers.com:1202 -u YOUR_NEOX_WALLET -w my_rig --log-file logs/miner.log

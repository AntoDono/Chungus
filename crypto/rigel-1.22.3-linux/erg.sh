#!/bin/sh

# replace the wallet addresses with your own

# mine to 2miners
./rigel -a autolykos2 -o stratum+tcp://erg.2miners.com:8888 -u YOUR_ERG_WALLET -w my_rig --log-file logs/miner.log

# mine to herominers
#./rigel -a autolykos2 -o stratum+tcp://de.ergo.herominers.com:1180 -u YOUR_ERG_WALLET -w my_rig --log-file logs/miner.log

# mine to kryptex
#./rigel -a autolykos2 -o stratum+tcp://erg.kryptex.network:7777 -u YOUR_ERG_WALLET -w my_rig --log-file logs/miner.log

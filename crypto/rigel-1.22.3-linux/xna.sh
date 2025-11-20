#!/bin/sh

# replace the wallet addresses with your own

# mine to vipor
./rigel -a kawpow --coin xna -o stratum+tcp://pool.vipor.net:5090 -u YOUR_XNA_WALLET -w my_rig --log-file logs/miner.log

# mine to rplant
#./rigel -a kawpow --coin xna -o stratum+tcp://stratum-eu.rplant.xyz:7029 -u YOUR_XNA_WALLET -w my_rig --log-file logs/miner.log

# mine to kryptex
#./rigel -a kawpow --coin xna -o stratum+tcp://xna.kryptex.network:7777 -u YOUR_XNA_WALLET -w my_rig --log-file logs/miner.log

# mine to 2miners
#./rigel -a kawpow --coin xna -o stratum+tcp://xna.2miners.com:6060 -u YOUR_XNA_WALLET -w my_rig --log-file logs/miner.log

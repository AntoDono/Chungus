#!/bin/sh

# replace the wallet addresses with your own

# mine to vipor
./rigel -a kawpow --coin clore -o stratum+tcp://pool.vipor.net:5030 -u YOUR_CLORE_WALLET -w my_rig --log-file logs/miner.log

# mine to rplant
#./rigel -a kawpow --coin clore -o stratum+tcp://stratum-eu.rplant.xyz:7083 -u YOUR_CLORE_WALLET -w my_rig --log-file logs/miner.log

# mine to kryptex
#./rigel -a kawpow --coin clore -o stratum+tcp://clore.kryptex.network:7777 -u YOUR_CLORE_WALLET -w my_rig --log-file logs/miner.log

# mine to 2miners
#./rigel -a kawpow --coin clore -o stratum+tcp://clore.2miners.com:2020 -u YOUR_CLORE_WALLET -w my_rig --log-file logs/miner.log

#!/bin/sh

# replace the wallet addresses with your own

# mine to vipor
./rigel -a alephium -o stratum+tcp://de.vipor.net:5050 -u YOUR_ALPH_WALLET -w my_rig --log-file logs/miner.log

# mine to herominers
#./rigel -a alephium -o stratum+tcp://de.alephium.herominers.com:1199 -u YOUR_ALPH_WALLET -w my_rig --log-file logs/miner.log

# mine to woolypooly
#./rigel -a alephium -o stratum+tcp://pool.woolypooly.com:3106 -u YOUR_ALPH_WALLET -w my_rig --log-file logs/miner.log

# mine to kryptex
#./rigel -a alephium -o stratum+tcp://alph.kryptex.network:7777 -u YOUR_ALPH_WALLET -w my_rig --log-file logs/miner.log

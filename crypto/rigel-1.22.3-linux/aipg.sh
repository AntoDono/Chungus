#!/bin/sh

# replace the wallet addresses with your own

# mine to rplant
./rigel -a kawpow --coin aipg -o stratum+tcp://stratum-eu.rplant.xyz:7105 -u YOUR_AIPG_WALLET -w my_rig --log-file logs/miner.log

# mine to mining4people
#./rigel -a kawpow --coin aipg -o stratum+tcp://de.mining4people.com:3328 -u YOUR_AIPG_WALLET -w my_rig --log-file logs/miner.log

# mine to ravenminer
#./rigel -a kawpow --coin aipg -o stratum+tcp://stratum.ravenminer.com:4010 -u YOUR_AIPG_WALLET -w my_rig --log-file logs/miner.log

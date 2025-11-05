# Download the deb package
wget https://download.foldingathome.org/releases/public/release/fahclient/debian-stable-64bit/v7.6/fahclient_7.6.21_amd64.deb

# Install
sudo dpkg -i fahclient_*.deb

# Install dependencies if needed
sudo apt-get install -f
# Download the tar package
wget https://download.foldingathome.org/releases/public/fah-client/debian-10-64bit/release/fah-client_8.4.9-64bit-release.tar.bz2

# Extract the tar.bz2 package
tar -xjf fah-*.tar.bz2
extracted_folder=$(tar -tjf fah-*.tar.bz2 | head -1 | cut -d'/' -f1)
echo "Extracted folder: $extracted_folder"

echo "Creating client link"

ln -s $extracted_folder/fah-client ./fah-client
rm fah-*.tar.bz2

echo "Setting up config.xml"
cat > config.xml << 'EOF'
<config>
     <user value="TeamName"/>
     <team value="TeamID"/>
     <account-token value="AccountToken"/>
</config>
EOF

echo "Setup completed successfully"
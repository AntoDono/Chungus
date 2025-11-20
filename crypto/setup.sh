wget https://github.com/rigelminer/rigel/releases/download/1.22.3/rigel-1.22.3-linux.tar.gz

tar -xzf rigel-*.tar.gz
extracted_folder=$(tar -tzf rigel-*.tar.gz | head -1 | cut -d'/' -f1)
echo "Extracted folder: $extracted_folder"

ln -s $extracted_folder/rigel ./rigel
rm rigel-*.tar.gz
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install -y ca-certificates curl make
sudo install -m 0755 -d /etc/apt/keyrings
# Add Docker's official GPG key:
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
# Add the repository to Apt sources:
echo   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" |   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl start docker


sudo groupadd redtics

sudo usermod -aG docker aseguel
sudo usermod -aG redtics aseguel

sudo adduser psilveira

sudo usermod -aG docker psilveira
sudo usermod -aG redtics psilveira
sudo usermod -aG sudo psilveira

sudo mkdir /opt/redtics
sudo chown psilveira:redtics /opt/redtics/


sudo adduser mpereyra
sudo usermod -aG docker mpereyra
sudo usermod -aG redtics mpereyra
sudo usermod -aG sudo mpereyra


sudo adduser ekristensen
sudo usermod -aG docker ekristensen
sudo usermod -aG redtics ekristensen
sudo usermod -aG sudo ekristensen

exit
sudo apt update
sudo apt-get install python3
sudo apt install python3-pip
alias pip='pip3'
sudo apt-get install git wget flex bison gperf python python-setuptools cmake ninja-build ccache libffi-dev libssl-dev dfu-util


#https://gist.github.com/elliotwoods/59e7dd58c53e1ee8f54cbb4437ec222f
sudo apt install curl
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python ./get-pip.py
pip install --updgrade pip
pip install -r esp-idf/requirements.txt
pip install esptool
source ~/esp-idf/export.sh


cd ~
git clone https://github.com/micropython/micropython.git
cd ~/micropython/
git submodule update --init --recursive
cd ~/micropython/mpy-cross/
make
или
pip install mpy-cross

cd ~/micropython/ports/esp32
make
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
The ESPIDF variable has not been set, please set it to the root of the esp-idf repository.
See README.md for installation instructions.
Supported git hash (v3.3): 9e70825d1e1cbf7988cf36981774300066580ea7
Supported git hash (v4.0) (experimental): 4c81978a3e2220674a432a588292a4c860eef27b
Makefile:74: *** ESPIDF not set.  Stop.

cd ~
git clone --recursive https://github.com/espressif/esp-idf.git
cd ~/esp-idf
git checkout 9e70825d1e1cbf7988cf36981774300066580ea7
#git checkout 4c81978a3e2220674a432a588292a4c860eef27b
git submodule update --init --recursive

./install.sh
. ./export.sh

cd ~/esp-idf/examples/get-started/hello_world/
/usr/bin/python -m pip install --user -r /home/pc/esp-idf/requirements.txt
idf.py build


cd ~/micropython/ports/esp32
Create a new file in the esp32 directory called makefile (or GNUmakefile) and add the following lines to that file:
ESPIDF = $(HOME)/esp-idf
BOARD ?= GENERIC
#PORT ?= /dev/ttyUSB0
#FLASH_MODE ?= qio
#FLASH_SIZE ?= 4MB
#CROSS_COMPILE ?= xtensa-esp32-elf-
include Makefile
EOF

sudo apt-get update -y
sudo apt-get install -y git-flow

cd ~/micropython/ports/esp32
sudo apt-get install python3-venv
python3 -m venv build-venv
source build-venv/bin/activate
pip install --upgrade pip
pip install -r ~/esp-idf/requirements.txt
make submodules
make


make USER_C_MODULES=../../../modules CFLAGS_EXTRA=-DMODULE_EXAMPLE_ENABLED=1 all
make USER_C_MODULES=../../../modules all
make USER_C_MODULES=cmodules all

******************************************************************************************
sudo apt-get install git wget flex bison gperf python3 python3-pip python3-setuptools cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0

~/micropython/ports/esp32/build-venv/bin/python3 -m pip install --upgrade pip
~/.espressif/python_env/idf4.3_py3.8_env/bin/python -m pip install --upgrade pip
~/.espressif/python_env/idf4.2_py3.8_env/bin/python -m pip install --upgrade pip

cd ~/esp-idf
git submodule update --init --recursive
./install.sh
source export.sh
. ./export.sh

cd ~/esp-idf/examples/get-started/hello_world/
idf.py clean
idf.py build

pip install sphinx
pip install sphinx_rtd_theme make html
cd ~/micropython/docs
clear && make html

cd ~/micropython/mpy-cross/
make clean && make
make clean
make
# OR INSTALL
pip install mpy-cross

cd ~/micropython/ports/esp32
make clean && make submodules && make
make clean
make submodules
make
clear && make 

clear && make USER_C_MODULES=../../../examples/usercmodule/micropython.cmake
clear && make USER_C_MODULES=../cmodules/micropython.cmake


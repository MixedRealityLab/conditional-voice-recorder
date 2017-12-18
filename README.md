<h1 align="center">
	Conditional Voice Recorder
</h1>

A system that listens for a hotword and begins audio capture. Configured to run on a Raspberry Pi 3, may work on other 
platforms. Makes use of the [Snowboy Hotword Detection system](https://snowboy.kitt.ai/).

## Setup
* Follow the steps to install the required pre-requisites from the 
  [GitHub repository](https://github.com/kitt-ai/snowboy#ubunturaspberry-pi)  
* You may need to install PIP at some point (not currently given in the setup instructions): 
  `curl https://bootstrap.pypa.io/get-pip.py | python` (need to run as SU if not already)
* Download a release of [Snowboy])(https://github.com/Kitt-AI/snowboy/releases)

### Build Instructions
* Install the following to compile the python library: `apt-get install python-dev`
* Install 'python-config': `pip install python-config` 
* The directory to build the Python library is 'swig/Python' (i.e. `cd` there now)
* Execute [this bash script to get SWIG](https://github.com/Kitt-AI/snowboy/issues/17#issuecomment-224766173) - you may 
  need to update the versions for SWIG and PCRE (check the directories manually), and then add the binary to the PATH
  - You could alternatively fix the 'Makefile' by changing the line `SWIG := swig` to `SWIG := swig3.0`, however at 
    time of writing, the Debian stable version of SWIG was not up-to-date enough
* Build the Python SWIG library by running `make` 

### Running an Snowboy Example
* Download/Generate a hotword model from the [Snowboy Website](https://snowboy.kitt.ai) (this requires Chrome or 
  Firefox), or find an existing file elsewhere on the Internet
* Move the '<name>.pdml' file in the 'examples/Python' directory and call `python demo.py <name>.pdml`
* Once you've confirmed the demo works, move onto the setup of the hotword detector

### Running the CVR
* Download the code from GitHub repository and `cd` into the directory
* Create symlinks to the compiled versions of 'smowboydetect.py' and '_snowboydetect.so', e.g.
  `ln -s /home/pi/snowboy-1.1.0/swig/Python/snowboydetect.py snowboydetect.py' and
  `ln -s /home/pi/snowboy-1.1.0/swig/Python/_snowboydetect.so _snowboydetect.so'
* Also use the default snowboy resources:
  `ln -s /home/pi/snowboy-1.1.0/resources resources'
* Copy your model to the directory
* Run the code `python detector.py <name>.pdml`

## Init Script
* This script starts, stops, and restarts the CVR automatically
* Edit the variable `DIR` in the file to the correct directory for the CVR
* Copy the file 'utils/cvr.sh' to '/etc/init.d/cvr', and make sure it is owned by root and has user execute permissions
* Optionally add `@reboot /etc/init.d/cvr start` to root's crontab to start the detector on boot
* Run `update-rc.d cvr defaults` after doing this
* Optionally, run `ln -s /etc/init.d/cvr /etc/rc0.d/K01cvr` to stop the system safely on shutdown

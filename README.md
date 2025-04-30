There is no way this will "just work" for you; there are paths and
other assumptions in the code. It is a toy, for fun. I have no plan
to maintain/fix/upgrade. If you find it useful, great!

![GUI for project showing three idling workers.](/Screenshot.png)

This is a driver for https://github.com/easydiffusion/easydiffusion which is a UI and
installer for stable diffusion. This project runs multiple instances, one
per machine. There are no GPUs on these machines; images are typically 10
minutes each so having a small farm of machines helps. This project does 
not use the easy diffusion GUI, though it may pop up in a web browser if 
ssh has X support. Just close those browsers if they show up. I wrote this
to experiment with SD without buying a GPU.

Within this project there are some useful bits:

main.py sets up queues for messages between the controller display and
all the worker tasks that each hold a machine. It creates and starts the
threads and creates and starts the controller (the tk window) and runs
the tk loop until shutdown.

controller.py builds a tk window. Lots of tk code, repetitive, and tied
to the REST API which is part of easy diffusion or stable diffusion (not
really sure where this API is defined; I teased it apart the hard way.)
The useful list of modifiers is scraped out of the easydiffusion json 
files. The "push" button's function queues a request to the workers. The
onAfter function gets queued messages from the workers and shows them in
the controller's GUI.

connector.py is a thread per machine that queues messages in both
directions. This is a Linux ssh subprocess multiple pipe solution and
usually pretty robust. Tearing down the connection usually doesn't 
leave an open port to prevent a restart. There is something flakey
with some machines and avahi (.local) support, using the ip address
solves that.

easydriver.py has a lot of statemachine logic empirically discovered.
It attempts to do what the ed-GUI does, at least enough to get this
going. PngInfo packs metadata into the png files.

The metadata is confusing and duplicated both in easydiffusion and this
project because there is a desire to save the prompt string which is
built from various GUI elements AND to save the values of the GUI 
elements for a subsequent relaunch. 

There might be a drag'n'drop python package for external files into a tk window, but
it looked like it might not be a good use of time. tk does d'n'd only within itself, I think. I recently saw a
web based interface that supports dragging existing files into the
html/js to populate parameters...seems quite nice. This might be my
one and only tk project.

see the dragon video project too...
[<img src="https://img.youtube.com/vi/3DK0RUCdaFU/maxresdefault.jpg" width="50%">](https://youtu.be/3DK0RUCdaFU)

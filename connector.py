"""
the connector is the thread-per-host and some easy diffusion logic
"""
import threading
import queue
import subprocess
import sys
import os
import signal
import time
from easydriver import EasyDriver

class ConnectionThread(threading.Thread):
    name = ""
    ip = ""
    request_id = "" # what this thread is working on
    # unclear which of these are just memory for the browser (easy diffusion restore) and which are needed by the worker
    # the active tags list is embedded into the prompt, and most likely is only needed to restore the browser, so left out.
    packet = {
        #"active_tags": ["Detailed and Intricate","CGI","Oil Paint","Linocut","Photoshoot","Beautiful Lighting","Melancholic","by Artgerm","Artstation","by wlop","Octane Render"],
        "block_nsfw": False,
        "clip_skip": False,
        "enable_vae_tiling": True,
        "guidance_scale": 7.5,
        "height": 256,
        "inactive_tags": [],
        "metadata_output_format": "none",
        "negative_prompt": "",
        "num_inference_steps": 10,
        "num_outputs": 3,
        "original_prompt": "score_9, score_8_up, score_7_up \ndog chasing a car up a hill toward a tree",
        "output_format": "png",
        "output_lossless": False,
        "output_quality": 75,
        "prompt": "dog chasing a car up a hill toward a tree, Detailed and Intricate, CGI, Oil Paint, Linocut, Photoshoot, Beautiful Lighting, Melancholic, by Artgerm, Artstation, by wlop, Octane Render",
        "sampler_name": "euler_a",
        "seed": 2173501355, # be sure to randomize this!
        "session_id": "1737852392408", # I think this is a value made up here that is echoed back with pictures later and can be left out
        "show_only_filtered_image": True, # unclear how the sequencing would work for progress images, etc
        "stream_image_progress": False,
        "stream_progress_updates": True,
        "use_stable_diffusion_model": "rinoPonyCheckpoint_v10",
        "use_vae_model": "", # need to reserarch this a bit
        "used_random_seed": False,
        "vram_usage_level": "balanced",
        "width": 384
        }
    
    def __init__(self, id, name, workq, talkq, pingq):
        threading.Thread.__init__(self)
        self.id = id # 0, 1, 2 ...
        self.name = name # both the thread's debugging name AND the remote machine name
        self.workQueue = workq
        self.talkQueue = talkq
        self.pingQueue = pingq
        self.exitflag = False
        self.easydriver = EasyDriver(name, workq, self)
        self.log("init complete, run begins")
        self.start()
        return
    
    def exit(self):
        self.exitflag = True
        self.log("exit flag set")
        return
    
    def run(self): 
        self.log(f"thread {self.name} is running, connecting")
        """
        the connection thread has three jobs

        o  stream output from easy diffusion to the logger
        o  read the html responses and update statemachine
        o  pull command from the workQueue when state is 'ready for command'

        

        statemachine

        o  UnknownState
        o  StoppedState
        o  RequestState
        o  PollingState

        """
        process = subprocess.Popen( # dual -t makes ^C work
                'ssh -t -t c@' + self.name + ' "/home/c/easy-diffusion/start.sh"', # https://stackoverflow.com/a/44354509
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        os.set_blocking(process.stdout.fileno(), False) # https://stackoverflow.com/a/59291466


        packet = None
        while packet is None and not self.exitflag:
            x="a" # prime loop. spew lines as long as available.
            while len(x):
                x = process.stdout.readline()
                if len(x)>1:
                    # if "]8" in x:
                    #     t = x[0:-1].replace("\x1b","ESC")
                    #     print(f"'{t}'")
                    self.log(x[0:-1]) # strip trail CR

            # spew finished. Operate html state machine.

            self.easydriver.cycle() # fsm
            time.sleep(1.0)

        #print(f"thread {self.name} finished {packet if packet else 'canceled'}")
        self.log( f"thread {self.name} finished {packet if packet else 'canceled'}")
        process.stdin.write("\x03") # ^C
        process.stdin.write("\x0d") # press any key to continue
        try:
            process.stdin.flush()
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()
        except BrokenPipeError:
            pass # never launched? the flush will fail
        return

    def log(self, message): # picked up by the controller for the scrolling displays
        self.talkQueue.put({"id":self.id, "message": message})

    def ping(self, message): # picked up by the controller for the scrolling displays
        self.pingQueue.put({"id":self.id, "message": message})

    def getPacket(self):
        packet = None
        if not self.workQueue.empty():
            try:
                packet = self.workQueue.get(timeout=1)  
            except queue.Empty as e:
                pass
        return packet



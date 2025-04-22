"""
the controller is the GUI window that sets parameters and makes requests
"""
import tkinter as tk  # sudo apt-get install python3-tk     might be needed
from tkinter import ttk
import re
import random
import json

# https://stackoverflow.com/questions/7141509/tkinter-wait-for-item-in-queue
# there are no perfect answers for queueing between threads and tkinter on main thread.
# I think I'll use the after poll

# this suggests how to prompt before closing
# https://stackoverflow.com/questions/111155/how-do-i-handle-the-window-close-event-in-tkinter
""" AI version...
import tkinter as tk
from tkinter import messagebox

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        root.destroy()

root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", on_closing)

# Add your Tkinter widgets here
label = tk.Label(root, text="Tkinter Window")
label.pack(pady=20)

root.mainloop()
"""

# this suggests that SDControl should derive from Tk rather than making an explicit instance:
# https://stackoverflow.com/questions/41245051/tkinter-protocol-wm-delete-window-not-working-on-extra-windows 
class SDControl:

    def __init__(self, machines, workq, talkq, pingq):
        self.root = tk.Tk()
        self.root.title("SD Control")
        self.machines = machines
        self.workQueue = workq
        self.talkQueue = talkq
        self.pingQueue = pingq
        #self.modelList=None
        #self.loraList=None
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        content = ttk.Frame(self.root, padding="3 3 12 12")
        content.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S)) # positions and sizes the content in the root
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        # leftFrame holds the N workers
        leftFrame = ttk.Frame(content) # borderwidth=5, relief="ridge", width=200, height=100
        leftFrame.grid(column=0, row=0, columnspan=1, rowspan=len(self.machines), sticky = 'nsew') # positions and size the leftFrame
        leftFrame.grid_columnconfigure(0, weight=1)

        self.statusTalk = []
        self.pingName = []
        self.waitName = []
        self.statName = []
        self.stepName = []
        for i in range(len(self.machines)):
            leftFrame.grid_rowconfigure(i, weight=1)
            # workerFrame holds one worker inside the leftFrame's i'th row
            workerFrame = ttk.Frame(leftFrame)
            workerFrame['padding'] = (0,5,0,0)
            workerFrame.grid(column=0, row=i, sticky = 'nsew')
            #workerFrame.grid_rowconfigure(0, weight=1)
            workerFrame.grid_columnconfigure(0, weight=0) # nn lbl
            workerFrame.grid_columnconfigure(1, weight=1) # talkframe
            nn=0
            pinglbl = ttk.Label(workerFrame, text="sleeping") # self.machines[i].name
            pinglbl.grid(column=0, row=nn, sticky = 'nsew')
            self.pingName.insert(0,pinglbl) # ping fills in as the machines wake up
            nn+=1
            waitlbl = ttk.Label(workerFrame, text="?")
            waitlbl.grid(column=0, row=nn, sticky = 'nsew')
            self.waitName.insert(0,waitlbl)
            nn+=1
            statlbl = ttk.Label(workerFrame, text="?")
            statlbl.grid(column=0, row=nn, sticky = 'nsew')
            self.statName.insert(0,statlbl)
            nn+=1
            steplbl = ttk.Label(workerFrame, text="?")
            steplbl.grid(column=0, row=nn, sticky = 'nsew')
            self.stepName.insert(0,steplbl)
            nn+=1
            workerFrame.grid_rowconfigure(nn, weight=1) # bottom dummy row expands
            nn+=1
            # talkFrame is on the right of the workerFrame and holds a text + Yscrollbar
            talkFrame = ttk.Frame(workerFrame)
            talkFrame.grid(column=1, row=0, rowspan=nn, sticky = 'nsew')
            talkFrame.grid_rowconfigure(0, weight=1)
            talkFrame.grid_columnconfigure(0, weight=1) # text
            talkFrame.grid_columnconfigure(1, weight=0) # scrollbar
            # text is on left of talkFrame
            t = tk.Text(talkFrame, state='disabled', width=100, height=8, wrap='none')
            t.grid(column=0, row=0, sticky = 'nsew')

            # scroll is on right
            ys = ttk.Scrollbar(talkFrame, orient = 'vertical', command = t.yview)
            ys.grid(column = 1, row = 0, sticky = 'nsw')
            t['yscrollcommand'] = ys.set # connects the scroll to the text
            self.statusTalk.insert(0, t) # remember the text for logging activity later
            
        rightFrame = ttk.Frame(content) # borderwidth=5, relief="ridge", width=200, height=100
        rightFrame.grid(column=1, row=0, columnspan=1, rowspan=len(self.machines)+1, sticky = 'ns') # taller by 1?
        rightFrame['padding'] = (15,5,5,5)

        leftright = 0

        self.saveitems = {}

        nn=0
        modellbl = ttk.Label(rightFrame, text="model")
        modellbl.grid(column=leftright+0, row=nn, columnspan=1, pady=(0, 10))
        self.modelWidget = ttk.Combobox(rightFrame)
        self.modelWidget.grid(column=leftright+1, row=nn, columnspan=1, pady=(0, 10))
        self.modelWidget.state(["readonly"]) ## = True # this is a function, how to clear? 
        self.modelWidget['values'] = ('nothing yet',)
        self.modelWidget.bind('<<ComboboxSelected>>', self.comboselectClearHilite) 
        self.saveitems["model"] = self.modelWidget
        if leftright: #every other 
            nn+=1 
        leftright = 2-leftright


        loralbl = ttk.Label(rightFrame, text="lora")
        loralbl.grid(column=leftright+0, row=nn, columnspan=1, pady=(0, 10))
        self.loraWidget = ttk.Combobox(rightFrame)
        self.loraWidget.grid(column=leftright+1, row=nn, columnspan=1, pady=(0, 10))
        self.loraWidget.state(["readonly"]) ## = True # this is a function, how to clear? 
        self.loraWidget['values'] = ('nothing yet',)
        self.loraWidget.bind('<<ComboboxSelected>>', self.comboselectClearHilite) 
        self.saveitems["lora"] = self.loraWidget
        if leftright: #every other 
            nn+=1 
        leftright = 2-leftright


        guidelbl = ttk.Label(rightFrame, text="guide 0..7..50")
        guidelbl.grid(column=leftright+0, row=nn, columnspan=1, pady=(0, 10))
        self.guideWidget = ttk.Entry(rightFrame)
        self.guideWidget.grid(column=leftright+1, row=nn, columnspan=1, pady=(0, 10))
        self.saveitems["guide"] = self.guideWidget
        if leftright: #every other 
            nn+=1 
        leftright = 2-leftright


        loraAlphalbl = ttk.Label(rightFrame, text="loraAlpha -1..1")
        loraAlphalbl.grid(column=leftright+0, row=nn, columnspan=1, pady=(0, 10))
        self.loraAlphaWidget = ttk.Entry(rightFrame)
        self.loraAlphaWidget.grid(column=leftright+1, row=nn, columnspan=1, pady=(0, 10))
        self.saveitems["loraalpha"] = self.loraAlphaWidget
        if leftright: #every other 
            nn+=1 
        leftright = 2-leftright


        stepslbl = ttk.Label(rightFrame, text="steps 2..10..30")
        stepslbl.grid(column=leftright+0, row=nn, columnspan=1, pady=(0, 10))
        self.stepsWidget = ttk.Entry(rightFrame)
        self.stepsWidget.grid(column=leftright+1, row=nn, columnspan=1, pady=(0, 10))
        self.saveitems["steps"] = self.stepsWidget
        if leftright: #every other 
            nn+=1 
        leftright = 2-leftright


        vsizelbl = ttk.Label(rightFrame, text="vsize 256..4096")
        vsizelbl.grid(column=leftright+0, row=nn, columnspan=1, pady=(0, 10))
        self.vsizeWidget = ttk.Entry(rightFrame)
        self.vsizeWidget.grid(column=leftright+1, row=nn, columnspan=1, pady=(0, 10))
        self.saveitems["vsize"] = self.vsizeWidget
        if leftright: #every other 
            nn+=1 
        leftright = 2-leftright


        noutlbl = ttk.Label(rightFrame, text="num out 1..10")
        noutlbl.grid(column=leftright+0, row=nn, columnspan=1, pady=(0, 10))
        self.noutWidget = ttk.Entry(rightFrame)
        self.noutWidget.grid(column=leftright+1, row=nn, columnspan=1, pady=(0, 10))
        self.saveitems["nout"] = self.noutWidget        
        if leftright: #every other 
            nn+=1 
        leftright = 2-leftright


        hsizelbl = ttk.Label(rightFrame, text="hsize 256..4096")
        hsizelbl.grid(column=leftright+0, row=nn, columnspan=1, pady=(0, 10))
        self.hsizeWidget = ttk.Entry(rightFrame)
        self.hsizeWidget.grid(column=leftright+1, row=nn, columnspan=1, pady=(0, 10))
        self.saveitems["hsize"] = self.hsizeWidget
        if leftright: #every other 
            nn+=1 
        leftright = 2-leftright


        # checkboxes /home/c/easy-diffusion/ui/modifiers.json
        # [
        #   {
        #     "category": "Drawing Style",
        #     "modifiers": [
        #       {
        #         "modifier": "Cel Shading",
        #         "previews": [
        #           {
        #             "name": "portrait",
        #             "path": "drawing_style/cel_shading/portrait-0.jpg"
        #           },
        #           {
        #             "name": "landscape",
        #             "path": "drawing_style/cel_shading/landscape-0.jpg"
        #           }
        #         ]
        #       },
        #       {
        #         "modifier": "Children's Drawing",
        # ...  {
        #     "category": "Visual Style",
        #     ...

        leftright = 0 # add the 1-3 text box, make sure the step is even
        promptlbl = ttk.Label(rightFrame, text="prompt")
        promptlbl.grid(column=leftright+0, row=nn, columnspan=1, pady=(0, 10))
        self.promptWidget = tk.Text(rightFrame, height=6)
        self.promptWidget.grid(column=leftright+1, row=nn, columnspan=3, pady=(0, 10))
        self.saveitems["prompt"] = self.promptWidget
        nn+=1 

        self.allcats = []
        with open("/home/c/easy-diffusion/ui/modifiers.json", "r") as f:
            cats = json.load(f)
            for cat in cats:
                catname = cat["category"]
                catlabel = ttk.Label(rightFrame,text=catname)
                catlabel.grid(column=leftright+0,row=nn,pady=(0,10))
                catFrame = ttk.Frame(rightFrame)
                catFrame.grid(column=leftright+1,row=nn,pady=(0,10))
                catListBox = tk.Listbox(catFrame, height=6, selectmode='extended', exportselection=False) # https://stackoverflow.com/questions/10048609/how-to-keep-selections-highlighted-in-a-tkinter-listbox
                catListBox.grid(column=0,row=0)
                catListBoxScroll = ttk.Scrollbar(catFrame, orient=tk.VERTICAL, command=catListBox.yview)
                catListBoxScroll.grid(column=1, row=0, sticky=(tk.N, tk.S))
                catListBox['yscrollcommand'] = catListBoxScroll.set
                self.saveitems["cat_"+catname] = catListBox
                if leftright: #every other 
                    nn+=1 
                leftright = 2-leftright
                self.allcats.append(catListBox)
                # the listbox+scroll is constructed, now fill it in                
                mods = cat["modifiers"]
                for mod in mods:
                    modname = mod["modifier"]
                    #print(f"{catname} {modname}")
                    catListBox.insert(0,modname)


        # spacing at bottom
        rightFrame.grid_rowconfigure(nn, weight=1)
        nn += 1
        # output-only read-only fields
        queueSizelbl = ttk.Label(rightFrame, text="queueSize")
        queueSizelbl.grid(column=0, row=nn, columnspan=1, pady=(0, 10))
        self.queueSizeWidget = ttk.Label(rightFrame)
        self.queueSizeWidget.grid(column=1, row=nn, columnspan=1, pady=(0, 10))

        exit = ttk.Button(rightFrame, text="Exit", command=self.exit)
        push = ttk.Button(rightFrame, text="Push", command=self.push)
        exit.grid(column=2, row=nn)
        push.grid(column=3, row=nn)

        self.aftertime = 100
        self.root.after(self.aftertime, self.onAfter) # begin polling for messages in talkQueue

        with open("/home/c/Desktop/sd_driver_settings.json", "r") as f:
            settings = json.load(f)
            for key in self.saveitems.keys():
                try:
                    try:
                        self.saveitems[key].selection_clear(0, tk.END) # listbox, others dont have selection_clear
                        for idx in settings[key]:
                            self.saveitems[key].selection_set(idx) # 10 list boxes
                    except TypeError:
                        self.saveitems[key].set(settings[key]) # combo - model, lora, entry and text dont have set

                except AttributeError:
                    try:
                        self.saveitems[key].delete(0, tk.END) # Entry - guide, loraalpha, steps, ... hsize
                        self.saveitems[key].insert(0, settings[key])
                    except tk.TclError:
                        self.saveitems[key].delete("1.0", tk.END) # Text - prompt - unlike Entry needs multiline "1.0"
                        self.saveitems[key].insert(tk.END, settings[key])

    def comboselectClearHilite(self,x):
        # https://stackoverflow.com/questions/5235998/how-to-control-the-tkinter-combobox-selection-highlighting
        self.modelWidget.selection_clear()
        self.loraWidget.selection_clear()

    def exit(self):
        for i in range(len(self.machines)):
            self.machines[i].exit()
        #self.root.after(5000,self.root.quit)

    def push(self):

        # save settings
        settings = {}
        for key in self.saveitems.keys():
            try:
                settings[key] = self.saveitems[key].get() # Entry
            except TypeError:
                try:
                    settings[key] = self.saveitems[key].curselection() # ListBox
                except AttributeError:
                    settings[key] = self.saveitems[key].get("1.0", "end-1c") # Text
        #print(settings)
        with open("/home/c/Desktop/sd_driver_settings.json", "w") as f:
            json.dump(settings, f)

# render_request
#         {'prompt': 'dog chasing a car up a hill toward a tree, Detailed and Intricate, CGI, Oil Paint, Li...rtgerm, Artstation, by wlop, Octane Render', 
#          'negative_prompt': '', 
#          'seed': 1206883517, 
#          'width': 768, 
#          'height': 512, 
#          'num_outputs': 1, 
#          'num_inference_steps': 4, 
#          'guidance_scale': 3.0, 
#          'control_alpha': None, 
#          'prompt_strength': 0.8, 
#          'preserve_init_image_color_profile': False, 
#          'strict_mask_border': False, 
#          'sampler_name': 'euler_a', 
#          'hypernetwork_strength': 0, 
#          'lora_alpha': 0, 
#          'tiling': None
#          }
# task_data
# {'request_id': 139978875598736, 
#  'session_id': '1737852392408', 
#  'vram_usage_level': 'balanced', 
#  'use_face_correction': None, 
#  'use_upscale': None, 
#  'upscale_amount': 4, 
#  'latent_upscaler_steps': 10, 
#  'use_stable_diffusion_model': 'AnythingXL_inkBase', 
#  'use_vae_model': '', 
#  'use_hypernetwork_model': None, 
#  'use_lora_model': None, 
#  'use_controlnet_model': None, 
#  'use_embeddings_model': None, 
#  'filters': [], 
#  'filter_params': {}, 
#  'control_filter_to_apply': None, 
#  'enable_vae_tiling': True, 
#  'show_only_filtered_image': True, 
#  'block_nsfw': False, 
#  'stream_image_progress': False, 
#  'stream_image_progress_interval': 5, 
#  'clip_skip': False, 
#  'codeformer_upscale_faces': False, 
#  'codeformer_fidelity': 0.5, 
#  'output_format': 'png', 
#  'output_quality': 75, 
#  'output_lossless': False, 
#  'save_to_disk_path': None, 
#  'metadata_output_format': 'txt'
#  }

# the saved json file
# {
#   "prompt": "gazing pool in a dark forest, Detailed and Intricate, CGI, Oil Paint, Linocut, Photoshoot, Beautiful Lighting, Melancholic, by Artgerm, Artstation, by Greg Rutkowski, by wlop, Octane Render",
#   "seed": 2173501355,
#   "used_random_seed": false,
#   "negative_prompt": "",
#   "num_outputs": 1,
#   "num_inference_steps": 10,
#   "guidance_scale": 7.5,
#   "width": 3072,
#   "height": 2048,
#   "vram_usage_level": "balanced",
#   "sampler_name": "euler_a",
#   "use_stable_diffusion_model": "msPonyreal_v3",
#   "clip_skip": false,
#   "use_vae_model": "",
#   "stream_progress_updates": true,
#   "stream_image_progress": false,
#   "show_only_filtered_image": true,
#   "block_nsfw": false,
#   "output_format": "png",
#   "output_quality": 75,
#   "output_lossless": false,
#   "metadata_output_format": "none",
#   "inactive_tags": [],
#   "enable_vae_tiling": true
# }

        prompt = self.promptWidget.get("1.0", "end-1c")
        for cat in self.allcats: # the listboxes with multiple selections
            idxs = cat.curselection()
            for idx in idxs:
                prompt += ", " + cat.get(idx)

        workpacket = {
#            "block_nsfw": False,
#            "clip_skip": False,
#            "enable_vae_tiling": True,
            "guidance_scale": self.guideWidget.get(),
            "height": self.vsizeWidget.get(),
#            "metadata_output_format": "none",
            "negative_prompt": "nsfw",
            "num_inference_steps": self.stepsWidget.get(),
            "num_outputs": self.noutWidget.get(),
            "output_format": "png",
#            "output_lossless": False,
#            "output_quality": 75,
            "prompt": prompt,
            "sampler_name": "euler_a",
            "seed": random.randint(1000000000,2000000000),
            "session_id": "1737852392408",
#            "show_only_filtered_image": True,
#            "stream_image_progress": False,
#            "stream_progress_updates": True,
            "use_stable_diffusion_model": self.modelWidget.get(),
            "use_lora_model": self.loraWidget.get(),
            'lora_alpha': self.loraAlphaWidget.get(),
#            "use_vae_model": "",
#            "used_random_seed": False,
            "vram_usage_level": "balanced",
            "width": self.hsizeWidget.get(),
            "settings": settings,
        }
        self.workQueue.put(workpacket)
        return

    def onAfter(self): # polling dispatcher for talkQueue, pingQueue
        if not self.talkQueue.empty():
            try:
                m = self.talkQueue.get(False) # must succeed because the queue is not empty
            except:
                assert False # this can't happen because this is polling from the main thread - there is no race
            self.log(m['id'], m['message'])
        
        if not self.pingQueue.empty():
            try:
                m = self.pingQueue.get(False) # must succeed because the queue is not empty
            except:
                assert False # this can't happen because this is polling from the main thread - there is no race
            id = m['id'] # 1
           # print(m['message']) # {'type': 'status', 'value': 'LoadingModel'}, {'type': 'name', 'value': 'thinkc.local'}
            type = m['message']['type'] # status, name
            value = m['message']['value'] # LoadingModel, thinkc.local
            if type=='name':
                self.pingName[id].config(text = value)
            elif type=='wait':
                self.waitName[id].config(text = value)
            elif type=='stat':
                self.statName[id].config(text = value)
            elif type=='step':
                self.stepName[id].config(text = value)
            elif type=="loras":
                self.log(id,"new loras="+str(value))
                if self.loraWidget['values'] == ('nothing yet',):
                    self.loraWidget['values'] = value
                else:
                    self.loraWidget['values'] = list(set(self.loraWidget['values']) & set(value))
            elif type=="models":
                self.log(id,"models="+str(value))
                if self.modelWidget['values'] == ('nothing yet',):
                    self.modelWidget['values'] = value
                else:
                    self.modelWidget['values'] = list(set(self.modelWidget['values']) & set(value))
            else:
                print(m)
        self.queueSizeWidget.config(text = str(self.workQueue.qsize()))
        self.root.after(self.aftertime, self.onAfter) # poll again, after aftertime

    def log(self, id, text):
        self.statusTalk[id]['state'] = 'normal'
        self.statusTalk[id].delete('1.0', 'end -1000 lines') # elsewhere the height is 8, keep 1000 for scrolling
        self.statusTalk[id].insert(tk.END,re.sub(r'\x1b\[[0-9;]*[mG]', '', text)+"\n")
        self.statusTalk[id].see(tk.END)
        self.statusTalk[id]['state'] = 'disabled'

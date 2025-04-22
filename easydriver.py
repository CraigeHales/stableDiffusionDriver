"""
easydriver is the statemachine logic and url calls to work with easy diffusion


"""

import requests
import json
import base64
from io import BytesIO
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import re
import time

waiter = ["|","/","-","\\",]

class EasyDriver:
    def __init__(self,name,workQueue,con):
        self.state = "unknown"
        self.name = name
        self.workQueue = workQueue
        self.con = con
        self.con.ping({"type":"name", "value":name})
        self.iwaiter = 0
        self.packet = "no packet yet"
        return

    def cycle(self):
        match self.state:
            case "unknown": # try a ping
                try:
                    # fetch models
                    r = requests.get("http://" + self.name + ":9000/get/models?scan_for_malicious=true")
                    r = r.json()
                    # r['options'].keys() ->
                    # dict_keys(['stable-diffusion', 'vae', 'hypernetwork', 'lora', 'codeformer', 'embeddings', 'controlnet', 'gfpgan'])
                    # r['options']['stable-diffusion'] ->
                    # ['absolutereality_v181', 'anima008XxmixTurbo_v10', 'AnythingXL_inkBase', 'binchModePonyXL_v15', 'c4pacitor_dV2', 'cerberoturboAllInOne_10', 'copaxTimelessxlSDXL1_v11Lightning', 'cyberrealistic_v33', 'dreamshaper_8', 'dreamshaperXL_alpha2Xl10', 'epicphotogasm_ultimateFidelity', 'epicrealism_naturalSinRC1VAE', 'Epicrealismxl_Hades', 'fluentlyXL_v3Lightning4S', 'ghostmix_v20Bakedvae', 'jibMixRealisticXL_v10Lightning46Step', 'majicmixRealistic_v7', 'msPonyreal_v3', 'onlyfornsfw118_v10TurboLCM', 'paintersCheckpointOilPaint_v11', 'phoenixByArteiaman_v10SDXLTURBO', 'ponyDiffusionV6XL_v6StartWithThisOne', 'purerealismMixXL_v10', 'realDream_sdxlLightning1LowCFG', 'realDream_sdxlPony13', 'realgoodFastpass_beta01', 'realisticVisionV60B1_v51HyperVAE', 'reallybiglust_v095Realism', 'realmixpony_rev08V5', 'realvisxlV40_v30TurboBakedvae', 'rinoPonyCheckpoint_v10', 'sd-v1-5', 'sdXL_v10VAEFix', 'sdxl_vae.pony', 'stellaratormix_v20', 'switchMix_realism', 'toonyou_beta6', 'turboxl_Ambdreamffxl400', 'ultrarealFineTune_v20', 'ultrarealFineTune_v3Experimental', 'unstableIllusionSDXL_sdxlLightningVAE']
                    self.models = r['options']['stable-diffusion']
                    self.loras = r['options']['lora']
                    self.con.ping({"type":"models", "value":self.models})
                    self.con.ping({"type":"loras", "value":self.loras})
                    r = requests.get("http://" + self.name + ":9000/ping")
                    r = r.json()
                    self.con.ping({"type":"stat", "value":r["status"]})
                    self.state = "pinging"
                except Exception as e:
                    self.con.log(repr(e))
                    self.state = "unknown"
                pass
            case "pinging": # try receive
                try:
                    r = requests.get("http://" + self.name + ":9000/ping")
                    r = r.json()
                    self.con.ping({"type":"stat", "value":r["status"]})
                    match r["status"]:
                        case "LoadingModel":
                            self.state = "pinging"
                        case "Online":
                            self.state = "idle"
                        case "Rendering":
                            self.state = "busy"
                        case _:
                            print(r["status"])
                            self.state = "unknown"        
                except Exception as e:
                    self.con.log(repr(e))
                    self.state = "unknown"

                pass
            case "idle": # try get a command from commandQueue
                self.packet = self.con.getPacket()
                if self.packet:
                    self.con.ping({"type":"step", "value":f"starting!"})
                    try:
                        headers = { "Content-Type": "application/json" }
                        r = requests.post("http://" + self.name + ":9000/render", json=self.packet, headers=headers)
                        r = r.json()
                        # {'detail': [{'loc': ['body'], 'msg': 'value is not a valid dict', 'type': 'type_error.dict'}]}
                        # {'detail': [{'type': 'json_invalid', 'loc': ['body', 0], 'msg': 'JSON decode error', 'input': {}, 'ctx': {'error': 'Expecting value'}}]}
                        # {'status': 'Online', 'queue': 1, 'stream': '/image/stream/140463533482576', 'task': 140463533482576}
                        # {'status': 'Rendering', 'queue': 1, 'stream': '/image/stream/140464610964048', 'task': 140464610964048}
                        # {'status': 'Rendering', 'queue': 19, 'stream': '/image/stream/140239618177920', 'task': 140239618177920}
                        self.con.ping({"type":"stat", "value":r["status"]})
                        match r["status"]:
                            case "LoadingModel":
                                self.state = "pinging"
                            case "Online":
                                self.stream = r["stream"]
                                self.task = r["task"]
                                self.state = "busy"
                                self.startTime = time.time()
                            case _:
                                print(r["status"])
                                self.state = "unknown"        
                    except Exception as e:
                        self.con.log(repr(e))
                        self.state = "unknown"
                else: # waiting for a workQueue item, pinging state looks active then feeds back here
                    self.con.ping({"type":"step", "value":f"idling!"})
                    self.state = "pinging"

            case "busy":
                try:
                    r = requests.get("http://" + self.name + ":9000" + self.stream)
                    if len(r.content):
                        #print(r.content)
                        #r = r.json() somtimes these are packed without separators instead of just one
                        r = b"[" + r.content.replace(b"}{", b"}, {") + b"]" # https://stackoverflow.com/a/64051111
                        ra = json.loads(r)
                        #print(len(ra))
                        for r in ra:
                            if 'step' in r:
                                self.con.ping({"type":"step", "value":f"{r['step']}/{r['total_steps']}"})
                                self.state = "busy"
                            elif 'status' in r:
                                self.con.ping({"type":"stat", "value":r["status"]})
                                match r["status"]:
                                    case "succeeded":
                                        self.stopTime = time.time()
                                        self.con.ping({"type":"step", "value":f"done"})
                                        render_request = r['render_request'] 
                                        # (['prompt', 'negative_prompt', 'seed', 'width', 'height', 'num_outputs', 
                                        # 'num_inference_steps', 'guidance_scale', 'control_alpha', 'prompt_strength', 
                                        # 'preserve_init_image_color_profile', 'strict_mask_border', 'sampler_name', 
                                        # 'hypernetwork_strength', 'lora_alpha', 'tiling'])
                                        task_data = r['task_data']
                                        # (['request_id', 'session_id', 'vram_usage_level', 'use_face_correction', 
                                        # 'use_upscale', 'upscale_amount', 'latent_upscaler_steps', 'use_stable_diffusion_model', 
                                        # 'use_vae_model', 'use_hypernetwork_model', 'use_lora_model', 'use_controlnet_model', 
                                        # 'use_embeddings_model', 'filters', 'filter_params', 'control_filter_to_apply', 
                                        # 'enable_vae_tiling', 'show_only_filtered_image', 'block_nsfw', 'stream_image_progress', 
                                        # 'stream_image_progress_interval', 'clip_skip', 'codeformer_upscale_faces', 'codeformer_fidelity', 
                                        # 'output_format', 'output_quality', 'output_lossless', 'save_to_disk_path', 'metadata_output_format'])
                                        outputs = r['output']
                                        # list: [{'data': 'data:image/png;base64,iVBORhE...2mCC', 'seed': 2173501355, 'path_abs': None}]

                                        for output in outputs:
                                            seed = output['seed']
                                            data = output['data'].split(',') # "data:image/png;base64,iVBORw0KGg..."
                                            extension = data[0].split(';')[0].split('/')[1] # "data:image/png;base64"
                                            data = base64.b64decode(data[1])
                                            prompt = re.sub(r'[\s\W]', '', str(render_request["prompt"]).title())
                                            if len(prompt) > 60:
                                                prompt = prompt[:35] + "..." + prompt[-15:]
                                            filename = ("/home/c/Desktop/images/" 
                                                        + "_M-" + str(task_data["use_stable_diffusion_model"])
                                                        + "_P-" + prompt
                                                        + "_S-" + str(seed) 
                                                        + "_I-" + str(render_request["num_inference_steps"])
                                                        + "_G-" + str(render_request["guidance_scale"])
                                                        + "_L-" + str(task_data["use_lora_model"]) 
                                                        + "_A-" + str(render_request["lora_alpha"])
                                                        + "_V-" + str(task_data["use_vae_model"])
                                                        + "." + extension)
                                            # embed meta data
                                            image_file = BytesIO(data)
                                            image = Image.open(image_file)
                                            metadata = PngInfo() # pngmeta --xrdf --quiet 1366114905.png  is one way to extract this. https://superuser.com/questions/275502/how-to-get-information-about-an-image-picture-from-the-linux-command-line
                                            metadata.add_text("runtime", str(self.stopTime - self.startTime)+"/"+str(render_request["num_outputs"]))
                                            metadata.add_text("settings", json.dumps(self.packet)) # added 11mar2025 13:00 pm
                                            #print(str(render_request))
                                            for key in render_request:
                                                metadata.add_text(key, str(render_request[key]))
                                            #print(str(task_data))
                                            for key in task_data:
                                                metadata.add_text(key, str(task_data[key]))
                                            image.save(filename, pnginfo=metadata)
                                            targetImage = Image.open(filename)
                                            #print(targetImage.text)

                                        self.state = "pinging"
                                    case _:
                                        self.con.ping({"type":"step", "value":f"error"})
                                        print(str(r),str(self.packet))
                                        self.state = "unknown"  
                            else:
                                self.con.log(repr(r))
                    else:
                        self.iwaiter += 1 
                        if self.iwaiter >= len(waiter):
                            self.iwaiter = 0
                        self.con.ping({"type":"wait", "value":waiter[self.iwaiter]})
                except Exception as e:
                    self.con.log(repr(e))
                    self.state = "unknown"

            case _:
                assert False

        return
    

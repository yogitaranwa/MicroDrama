"""Run on an idle free GPU host before selective official model downloads.
No weights or packages are downloaded by this diagnostic.
"""
import json, shutil, platform, importlib.util
from pathlib import Path
import torch
from huggingface_hub import HfApi
api=HfApi()
REPOS=['Wan-AI/Wan2.1-VACE-1.3B','Wan-AI/Wan2.1-I2V-14B-480P',
       'MeiGen-AI/MeiGen-MultiTalk','MeiGen-AI/InfiniteTalk',
       'TencentGameMate/chinese-wav2vec2-base','guozinan/PuLID']
report={'python':platform.python_version(),'torch':torch.__version__,
 'cuda':torch.cuda.is_available(),
 'gpus':[{'name':torch.cuda.get_device_properties(i).name,
          'memory_gib':torch.cuda.get_device_properties(i).total_memory/2**30}
         for i in range(torch.cuda.device_count())],
 'disks':{p:{'free_gib':shutil.disk_usage(p).free/2**30,
             'total_gib':shutil.disk_usage(p).total/2**30}
          for p in ['/','/kaggle/working','/tmp']},
 'modules':{m:importlib.util.find_spec(m) is not None
            for m in ['flash_attn','xfuser','insightface','diffusers','transformers']},
 'official_repo_files':{}}
for repo in REPOS:
 info=api.model_info(repo,files_metadata=True)
 report['official_repo_files'][repo]=[{'file':f.rfilename,'bytes':f.size}
                                    for f in info.siblings]
Path('/kaggle/working/model_setup_preflight.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))

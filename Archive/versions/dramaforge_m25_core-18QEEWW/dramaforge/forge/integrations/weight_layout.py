"""Read-only, no-download checkpoint layout checks from pinned loader contracts.

Presence is not authenticity. These checks catch incomplete/miswired folders;
model execution must still validate tensors, dependencies and hardware.
"""
import json
from pathlib import Path
from .registry import IntegrationError


def check_weight_layout(backend, ckpt_dir, *, wav2vec_dir=None,
                        infinitetalk_ckpt=None):
    root=Path(ckpt_dir)
    required=['config.json','models_t5_umt5-xxl-enc-bf16.pth','Wan2.1_VAE.pth',
              'google/umt5-xxl/spiece.model']
    errors=[]
    if backend in ('multitalk','infinitetalk'):
        required += ['models_clip_open-clip-xlm-roberta-large-vit-huge-14.pth']
        if backend == 'multitalk':
            index=root/'diffusion_pytorch_model.safetensors.index.json'
            try:
                data=json.loads(index.read_text())
                shards=set(data['weight_map'].values())
                if not shards or 'multitalk.safetensors' not in shards:
                    errors.append('MultiTalk merged index must include multitalk.safetensors')
                for shard in shards:
                    candidate=(root/shard).resolve()
                    if not candidate.is_relative_to(root.resolve()):
                        errors.append('checkpoint index escapes checkpoint directory')
                    elif not candidate.is_file() or candidate.stat().st_size == 0:
                        errors.append(f'checkpoint shard missing or empty: {shard}')
            except (OSError, ValueError, KeyError, TypeError):
                errors.append('valid MultiTalk merged weight index required')
        else:
            required += [f'diffusion_pytorch_model-{i:05d}-of-00007.safetensors' for i in range(1,8)]
            if not infinitetalk_ckpt or not Path(infinitetalk_ckpt).is_file() or Path(infinitetalk_ckpt).stat().st_size == 0:
                errors.append('explicit non-empty InfiniteTalk checkpoint file required')
        if not wav2vec_dir:
            errors.append('wav2vec directory required')
        else:
            w=Path(wav2vec_dir)
            for name in ('config.json','preprocessor_config.json'):
                if not (w/name).is_file(): errors.append(f'wav2vec file missing: {name}')
            if not any((w/n).is_file() and (w/n).stat().st_size for n in ('model.safetensors','pytorch_model.bin')):
                errors.append('wav2vec model weights missing')
    elif backend == 'vace':
        required += ['diffusion_pytorch_model.safetensors']
    else:
        raise IntegrationError('unsupported checkpoint layout')
    for name in required:
        p=root/name
        if not p.is_file() or p.stat().st_size == 0:
            errors.append(f'checkpoint file missing or empty: {name}')
    return {'backend':backend,'layout_ok':not errors,'errors':errors,
            'verification':'presence_only_not_authenticity_or_inference'}
